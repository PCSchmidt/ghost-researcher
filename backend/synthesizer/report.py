"""Report synthesizer skeleton with source-trace validation."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from backend.agent.memory import AgentSession, EvidenceRecord
from backend.agent.openrouter import OpenRouterChatClient
from backend.config import Settings
from backend.synthesizer.schema import ResearchReport, ReportClaim, ReportValidationError, validate_report_sources

SynthesisTransport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


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
        """Generate and validate a report for the current session."""
        if not session.evidence_records:
            raise SynthesisError("no_evidence_records")
        if session.running_tokens >= self._settings.max_tokens_per_job:
            raise SynthesisError("cost_limit")
        if session.running_cost_usd >= self._settings.max_model_cost_per_job_usd:
            raise SynthesisError("cost_limit")

        if self._transport is None and not self._settings.openrouter_api_key:
            report = _deterministic_report(session)
        else:
            transport = self._transport or OpenRouterChatClient(self._settings).complete
            response = await transport(_request_payload(self._model, session))
            _record_usage(session, response)
            if session.running_tokens >= self._settings.max_tokens_per_job:
                raise SynthesisError("cost_limit")
            if session.running_cost_usd >= self._settings.max_model_cost_per_job_usd:
                raise SynthesisError("cost_limit")
            report = _report_from_response(response)

        validate_report_sources(report, session.evidence_records)
        return report


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


def _report_from_response(response: dict[str, Any]) -> ResearchReport:
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
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise SynthesisError("invalid_report_json") from exc
    try:
        return ResearchReport.from_dict(payload)
    except ReportValidationError as exc:
        raise SynthesisError(str(exc)) from exc


__all__ = ["ReportSynthesizer", "SynthesisError"]
