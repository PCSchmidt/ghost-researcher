"""Report synthesizer skeleton with source-trace validation."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from backend.agent.memory import AgentSession, EvidenceRecord
from backend.agent.openrouter import OpenRouterChatClient
from backend.config import Settings
from backend.synthesizer.schema import (
    Reference,
    ReportClaim,
    ReportParagraph,
    ReportSection,
    ReportValidationError,
    ResearchReport,
    validate_report_sources,
)

SynthesisTransport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

logger = logging.getLogger("ghostresearcher.synthesis")


class SynthesisError(RuntimeError):
    """Raised when synthesis cannot produce a valid report."""


class ReportSynthesizer:
    """Create source-grounded research reports from session evidence."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: SynthesisTransport | None = None,
        model: str | None = None,
    ) -> None:
        self._settings = settings
        self._model = model or settings.default_synthesizer_model
        self._transport = transport

    async def synthesize(self, session: AgentSession) -> ResearchReport:
        """Generate and validate a report for the current session.

        Model synthesis is best-effort. If the model budget is already spent (the
        research loop can exhaust the shared token budget before synthesis runs) or a
        model pass fails, we degrade to a token-free deterministic build from the
        gathered evidence — a run that gathered evidence must never return an empty
        report.
        """
        if not session.evidence_records:
            raise SynthesisError("no_evidence_records")

        has_transport = self._transport is not None or bool(self._settings.openrouter_api_key)
        if has_transport and not self._over_budget(session):
            try:
                transport = self._transport or OpenRouterChatClient(self._settings).complete
                if self._settings.longform_enabled:
                    report = await self._synthesize_long_form(session, transport)
                else:
                    report = await self._synthesize_flat(session, transport)
            except SynthesisError as exc:
                logger.warning(
                    "model synthesis failed (%s); using deterministic build (goal=%r, tokens=%d)",
                    exc,
                    session.research_goal,
                    session.running_tokens,
                )
                report = self._deterministic_report_for(session)
        else:
            report = self._deterministic_report_for(session)

        validate_report_sources(report, session.evidence_records)
        return report

    def _deterministic_report_for(self, session: AgentSession) -> ResearchReport:
        if self._settings.longform_enabled:
            return _deterministic_long_form_report(session, self._settings.longform_max_sections)
        return _deterministic_report(session)

    def _over_budget(self, session: AgentSession) -> bool:
        return (
            session.running_tokens >= self._settings.max_tokens_per_job
            or session.running_cost_usd >= self._settings.max_model_cost_per_job_usd
        )

    def _guard_cost(self, session: AgentSession) -> None:
        if self._over_budget(session):
            raise SynthesisError("cost_limit")

    async def _synthesize_flat(self, session: AgentSession, transport: SynthesisTransport) -> ResearchReport:
        response = await transport(_request_payload(self._model, session))
        _record_usage(session, response)
        self._guard_cost(session)
        return _report_from_response(response)

    async def _call_json(
        self,
        transport: SynthesisTransport,
        model: str,
        request: dict[str, Any],
        session: AgentSession,
    ) -> dict[str, Any]:
        request = {**request, "model": model}
        response = await transport(request)
        _record_usage(session, response)
        self._guard_cost(session)
        return _json_content(response)

    async def _synthesize_long_form(self, session: AgentSession, transport: SynthesisTransport) -> ResearchReport:
        """Outline -> per-section drafting -> abstract/conclusion framing.

        Cheap tier (default_synthesizer_model) drafts sections; premium tier
        (fallback_synthesizer_model) handles the outline and framing where coherence
        matters most. Any pass failure degrades to a deterministic long-form build
        from the same evidence rather than returning nothing.
        """
        evidence = _evidence_for_synthesis(session)
        outline_model = self._settings.fallback_synthesizer_model
        section_model = self._settings.default_synthesizer_model
        try:
            outline = await self._call_json(transport, outline_model, _outline_request(session, evidence), session)
            planned = _parse_outline_sections(outline, evidence, self._settings.longform_max_sections)
            self._guard_cost(session)
            # Sections are independent, so draft them concurrently — this keeps total
            # synthesis time close to a single section call rather than their sum, which
            # matters because synthesis runs after the research loop under the job's
            # hard wall-clock timeout.
            section_jsons = await asyncio.gather(
                *(
                    self._call_json(transport, section_model, _section_request(session, heading, assigned), session)
                    for heading, assigned in planned
                )
            )
            drafted: list[ReportSection] = []
            for (heading, _assigned), section_json in zip(planned, section_jsons):
                paragraphs = _parse_section_paragraphs(section_json, evidence)
                if paragraphs:
                    drafted.append(ReportSection(heading=heading, paragraphs=paragraphs))
            if not drafted:
                raise SynthesisError("no_sections_drafted")
            self._guard_cost(session)
            framing = await self._call_json(
                transport, outline_model, _framing_request(session, outline, drafted), session
            )
            return _assemble_long_form(session, evidence, outline, drafted, framing)
        except SynthesisError:
            # Surfaces to synthesize(), which logs the reason and degrades to the
            # deterministic long-form build. Centralizing the fallback there keeps it
            # observable instead of silently swallowed here.
            raise
        except Exception as exc:  # noqa: BLE001 - report as SynthesisError so the caller degrades + logs
            raise SynthesisError(f"long_form_failed:{type(exc).__name__}") from exc


def _deterministic_report(session: AgentSession) -> ResearchReport:
    evidence = _evidence_for_synthesis(session)
    sources_used = [record.url for record in evidence]
    claims = [
        ReportClaim(text=claim, source_urls=[record.url])
        for record in evidence
        for claim in record.claims
        if claim.strip()
    ]
    if not claims:
        raise SynthesisError("no_claims")
    average_confidence = sum(record.credibility_score for record in evidence) / len(evidence)
    return ResearchReport(
        title=f"Research Report: {session.research_goal}",
        summary=" ".join(claim.text for claim in claims)[:800],
        key_findings=claims,
        sources_used=sources_used,
        confidence=round(average_confidence, 3),
        limitations=["Deterministic synthesis skeleton; no live model synthesis was used."],
    )


# --------------------------------------------------------------------------- #
# Long-form (v1.5.0) multi-pass synthesis
# --------------------------------------------------------------------------- #

_LONGFORM_MIN_PARAGRAPH_CHARS = 40


def _evidence_brief(record: EvidenceRecord) -> dict[str, Any]:
    return {
        "url": record.url,
        "title": record.title,
        "credibility_score": round(record.credibility_score, 3),
        "claims": [claim for claim in record.claims if claim.strip()][:6],
    }


def _outline_request(session: AgentSession, evidence: list[EvidenceRecord]) -> dict[str, Any]:
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are GhostResearcher planning the outline of a research paper. "
                    "Group the evidence into coherent themed sections. Return ONLY JSON. "
                    "Each section's source_urls must be chosen from the provided evidence URLs."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "research_goal": session.research_goal,
                        "evidence": [_evidence_brief(record) for record in evidence],
                        "instructions": (
                            "Produce a paper title and 2-6 themed sections. Sections should follow a logical "
                            "narrative (context -> mechanisms/themes -> implications). Do not invent sources."
                        ),
                        "schema": {
                            "title": "string",
                            "sections": [{"heading": "string", "source_urls": ["string"]}],
                        },
                    },
                    sort_keys=True,
                ),
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }


def _section_request(session: AgentSession, heading: str, assigned: list[EvidenceRecord]) -> dict[str, Any]:
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are GhostResearcher drafting ONE section of a research paper. Write 1-4 evidence-grounded "
                    "paragraphs. Every paragraph must list the source URLs it draws from in 'citations', chosen "
                    "only from the provided evidence. Do not fabricate facts or sources. Return ONLY JSON."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "research_goal": session.research_goal,
                        "section_heading": heading,
                        "evidence": [_evidence_brief(record) for record in assigned],
                        "schema": {"paragraphs": [{"text": "string", "citations": ["string"]}]},
                    },
                    sort_keys=True,
                ),
            },
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }


def _framing_request(session: AgentSession, outline: dict[str, Any], sections: list[ReportSection]) -> dict[str, Any]:
    section_digest = [
        {"heading": section.heading, "paragraph_texts": [paragraph.text for paragraph in section.paragraphs]}
        for section in sections
    ]
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are GhostResearcher writing the abstract, conclusion, and key findings for a research "
                    "paper given its drafted sections. The abstract is one paragraph; the conclusion synthesizes "
                    "the implications. key_findings must cite source_urls drawn only from the evidence already used "
                    "in the sections. Return ONLY JSON."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "research_goal": session.research_goal,
                        "title": str(outline.get("title") or session.research_goal),
                        "sections": section_digest,
                        "schema": {
                            "abstract": "string",
                            "conclusion": "string",
                            "key_findings": [{"text": "string", "source_urls": ["string"]}],
                        },
                    },
                    sort_keys=True,
                ),
            },
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }


def _parse_outline_sections(
    outline: dict[str, Any],
    evidence: list[EvidenceRecord],
    max_sections: int,
) -> list[tuple[str, list[EvidenceRecord]]]:
    by_url = {record.url: record for record in evidence}
    raw_sections = outline.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise SynthesisError("invalid_outline_sections")
    planned: list[tuple[str, list[EvidenceRecord]]] = []
    for raw in raw_sections[:max_sections]:
        if not isinstance(raw, dict):
            continue
        heading = str(raw.get("heading") or "").strip()
        if not heading:
            continue
        urls = raw.get("source_urls") if isinstance(raw.get("source_urls"), list) else []
        assigned = [by_url[str(url)] for url in urls if str(url) in by_url]
        if not assigned:
            assigned = list(evidence)  # ungrounded outline: hand the section all evidence
        planned.append((heading, assigned))
    if not planned:
        raise SynthesisError("no_planned_sections")
    return planned


def _parse_section_paragraphs(section_json: dict[str, Any], evidence: list[EvidenceRecord]) -> list[ReportParagraph]:
    evidence_urls = {record.url for record in evidence}
    raw_paragraphs = section_json.get("paragraphs")
    if not isinstance(raw_paragraphs, list):
        return []
    paragraphs: list[ReportParagraph] = []
    for raw in raw_paragraphs:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        if len(text) < _LONGFORM_MIN_PARAGRAPH_CHARS:
            continue
        raw_citations = raw.get("citations") if isinstance(raw.get("citations"), list) else []
        citations = [str(url) for url in raw_citations if str(url) in evidence_urls]
        paragraphs.append(ReportParagraph(text=text, citations=citations))
    return paragraphs


def _assemble_long_form(
    session: AgentSession,
    evidence: list[EvidenceRecord],
    outline: dict[str, Any],
    sections: list[ReportSection],
    framing: dict[str, Any],
) -> ResearchReport:
    evidence_urls = {record.url for record in evidence}
    title = str(outline.get("title") or "").strip() or f"Research Report: {session.research_goal}"

    abstract = str(framing.get("abstract") or "").strip()
    conclusion = str(framing.get("conclusion") or "").strip()

    key_findings: list[ReportClaim] = []
    for raw in framing.get("key_findings") or []:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        raw_sources = raw.get("source_urls") if isinstance(raw.get("source_urls"), list) else []
        sources = [str(url) for url in raw_sources if str(url) in evidence_urls]
        if text and sources:
            key_findings.append(ReportClaim(text=text, source_urls=sources))
    if not key_findings:
        key_findings = _key_findings_from_sections(sections, evidence)

    cited = _ordered_cited_urls(sections, key_findings)
    sources_used = cited or [record.url for record in evidence]
    references = _references_from_evidence(evidence)
    summary = abstract or " ".join(p.text for section in sections for p in section.paragraphs)[:800] or title
    confidence = _long_form_confidence(evidence, set(sources_used))

    return ResearchReport(
        title=title,
        summary=summary,
        key_findings=key_findings,
        sources_used=sources_used,
        confidence=confidence,
        abstract=abstract,
        sections=sections,
        conclusion=conclusion,
        references=references,
    )


def _deterministic_long_form_report(session: AgentSession, max_sections: int) -> ResearchReport:
    """Structured paper built directly from evidence (no model), for offline/fallback."""
    evidence = _evidence_for_synthesis(session)
    if not evidence:
        raise SynthesisError("no_evidence_records")
    chunk_size = max(1, -(-len(evidence) // max(1, max_sections)))  # ceil division
    sections: list[ReportSection] = []
    for index in range(0, len(evidence), chunk_size):
        chunk = evidence[index : index + chunk_size]
        paragraphs = [
            ReportParagraph(text=" ".join(c for c in record.claims if c.strip()) or record.title, citations=[record.url])
            for record in chunk
            if any(c.strip() for c in record.claims) or record.title
        ]
        if paragraphs:
            sections.append(ReportSection(heading=f"Findings {len(sections) + 1}", paragraphs=paragraphs))
    if not sections:
        raise SynthesisError("no_claims")
    key_findings = _key_findings_from_sections(sections, evidence)
    sources_used = _ordered_cited_urls(sections, key_findings) or [record.url for record in evidence]
    abstract = " ".join(p.text for section in sections for p in section.paragraphs)[:600]
    return ResearchReport(
        title=f"Research Report: {session.research_goal}",
        summary=abstract or session.research_goal,
        key_findings=key_findings,
        sources_used=sources_used,
        confidence=_long_form_confidence(evidence, set(sources_used)),
        limitations=["Deterministic long-form build; no live model synthesis was used."],
        abstract=abstract,
        sections=sections,
        conclusion="Synthesis assembled deterministically from gathered evidence.",
        references=_references_from_evidence(evidence),
    )


def _key_findings_from_sections(sections: list[ReportSection], evidence: list[EvidenceRecord]) -> list[ReportClaim]:
    evidence_urls = {record.url for record in evidence}
    findings: list[ReportClaim] = []
    for section in sections:
        for paragraph in section.paragraphs:
            sources = [url for url in paragraph.citations if url in evidence_urls]
            if sources:
                findings.append(ReportClaim(text=paragraph.text, source_urls=sources))
            if len(findings) >= 8:
                return findings
    if not findings:
        # Last resort: synthesize a finding per evidence record so the quick-view layer is non-empty.
        for record in evidence:
            claim = next((c for c in record.claims if c.strip()), record.title)
            if claim:
                findings.append(ReportClaim(text=claim, source_urls=[record.url]))
    return findings


def _ordered_cited_urls(sections: list[ReportSection], key_findings: list[ReportClaim]) -> list[str]:
    seen: dict[str, None] = {}
    for section in sections:
        for paragraph in section.paragraphs:
            for url in paragraph.citations:
                seen.setdefault(url, None)
    for claim in key_findings:
        for url in claim.source_urls:
            seen.setdefault(url, None)
    return list(seen.keys())


def _references_from_evidence(evidence: list[EvidenceRecord]) -> list[Reference]:
    ordered = sorted(evidence, key=lambda record: record.credibility_score, reverse=True)
    return [
        Reference(url=record.url, title=record.title or record.url, credibility_score=round(record.credibility_score, 3))
        for record in ordered
    ]


def _long_form_confidence(evidence: list[EvidenceRecord], sources_used: set[str]) -> float:
    cited = [record for record in evidence if record.url in sources_used] or evidence
    if not cited:
        return 0.0
    return round(sum(record.credibility_score for record in cited) / len(cited), 3)


def _json_content(response: dict[str, Any]) -> dict[str, Any]:
    payload = _message_content(response)
    if not isinstance(payload, dict):
        raise SynthesisError("invalid_pass_json")
    return payload


def _request_payload(model: str, session: AgentSession) -> dict[str, Any]:
    evidence = _evidence_for_synthesis(session)
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the GhostResearcher synthesizer. Return only JSON matching the requested schema. "
                    "Every key finding must cite source_urls from the provided evidence only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "research_goal": session.research_goal,
                        "evidence_records": [_evidence_to_dict(record) for record in evidence],
                        "schema": {
                            "title": "string",
                            "summary": "string",
                            "key_findings": [{"text": "string", "source_urls": ["string"]}],
                            "sources_used": ["string"],
                            "confidence": "number 0..1",
                            "limitations": ["string"],
                        },
                    },
                    sort_keys=True,
                ),
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }


def _evidence_to_dict(record: EvidenceRecord) -> dict[str, Any]:
    return {
        "url": record.url,
        "title": record.title,
        "claims": record.claims,
        "credibility_score": record.credibility_score,
        "evidence_type": record.evidence_type,
        "extracted_at": record.extracted_at.isoformat(),
    }


def _evidence_for_synthesis(session: AgentSession) -> list[EvidenceRecord]:
    """Prefer assessed evidence and keep only one synthesis record per source."""
    preferred_types = ("assessed", "extracted", "navigation_fallback")
    selected: dict[str, EvidenceRecord] = {}
    for evidence_type in preferred_types:
        for record in session.evidence_records_by_type(evidence_type):
            selected.setdefault(record.url, record)
    return list(selected.values())


def _record_usage(session: AgentSession, response: dict[str, Any]) -> None:
    usage = response.get("usage") or {}
    cost_value = usage.get("cost") or usage.get("total_cost") or response.get("cost") or 0.0
    session.record_model_usage(
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        cost_usd=float(cost_value),
    )


def _message_content(response: dict[str, Any]) -> Any:
    """Extract and JSON-decode the assistant message content from a chat response."""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SynthesisError("missing_choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise SynthesisError("missing_message")
    content = message.get("content")
    if not isinstance(content, str):
        raise SynthesisError("missing_content")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise SynthesisError("invalid_report_json") from exc


def _report_from_response(response: dict[str, Any]) -> ResearchReport:
    payload = _message_content(response)
    if not isinstance(payload, dict):
        raise SynthesisError("invalid_report_json")
    try:
        return ResearchReport.from_dict(payload)
    except ReportValidationError as exc:
        raise SynthesisError(str(exc)) from exc


__all__ = ["ReportSynthesizer", "SynthesisError"]
