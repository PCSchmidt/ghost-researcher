"""Structured report schema and source-trace validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agent.memory import EvidenceRecord


class ReportValidationError(ValueError):
    """Raised when a report cannot be traced to session evidence."""


@dataclass(frozen=True, slots=True)
class ReportClaim:
    """One claim in the final report with explicit source traceability."""

    text: str
    source_urls: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "source_urls": self.source_urls}


@dataclass(frozen=True, slots=True)
class ReportParagraph:
    """One paragraph of a themed section with in-text source citations.

    ``citations`` holds source URLs (not numbers) so the source-trace invariant is
    preserved end-to-end; the renderer/exporter maps each URL to a reference number.
    """

    text: str
    citations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "citations": self.citations}


@dataclass(frozen=True, slots=True)
class ReportSection:
    """A themed section of the long-form report."""

    heading: str
    paragraphs: list[ReportParagraph]

    def to_dict(self) -> dict[str, Any]:
        return {"heading": self.heading, "paragraphs": [paragraph.to_dict() for paragraph in self.paragraphs]}


@dataclass(frozen=True, slots=True)
class Reference:
    """One numbered entry in the report bibliography."""

    url: str
    title: str
    credibility_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"url": self.url, "title": self.title, "credibility_score": self.credibility_score}


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """Structured report emitted by the synthesizer.

    Long-form fields (``abstract``, ``sections``, ``conclusion``, ``references``) are
    additive and default empty, so a flat skeleton report stays valid. When
    ``sections`` is populated the report renders as a research paper; ``summary`` and
    ``key_findings`` are retained as a quick-view layer and for backward compatibility.
    """

    title: str
    summary: str
    key_findings: list[ReportClaim]
    sources_used: list[str]
    confidence: float
    limitations: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: list[ReportSection] = field(default_factory=list)
    conclusion: str = ""
    references: list[Reference] = field(default_factory=list)

    @property
    def is_long_form(self) -> bool:
        return bool(self.sections)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "key_findings": [claim.to_dict() for claim in self.key_findings],
            "sources_used": self.sources_used,
            "confidence": self.confidence,
            "limitations": self.limitations,
            "abstract": self.abstract,
            "sections": [section.to_dict() for section in self.sections],
            "conclusion": self.conclusion,
            "references": [reference.to_dict() for reference in self.references],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchReport":
        claims = payload.get("key_findings", [])
        if not isinstance(claims, list):
            raise ReportValidationError("invalid_key_findings")
        sections = payload.get("sections", [])
        if not isinstance(sections, list):
            raise ReportValidationError("invalid_sections")
        references = payload.get("references", [])
        if not isinstance(references, list):
            raise ReportValidationError("invalid_references")
        return cls(
            title=_required_string(payload, "title"),
            summary=_required_string(payload, "summary"),
            key_findings=[_claim_from_dict(claim) for claim in claims],
            sources_used=_required_string_list(payload, "sources_used"),
            confidence=_required_confidence(payload),
            limitations=_optional_string_list(payload, "limitations"),
            abstract=_optional_string(payload, "abstract"),
            sections=[_section_from_dict(section) for section in sections],
            conclusion=_optional_string(payload, "conclusion"),
            references=[_reference_from_dict(reference) for reference in references],
        )


def validate_report_sources(report: ResearchReport, evidence_records: list[EvidenceRecord]) -> None:
    """Ensure every cited source exists in the session evidence record.

    Holds the source-trace invariant across the flat quick-view layer (key_findings)
    and the long-form layer (section paragraph citations + references): no claim,
    in-text citation, or reference may point at a URL the agent never gathered.
    """
    evidence_urls = {record.url for record in evidence_records}
    if not report.sources_used:
        raise ReportValidationError("no_sources_used")
    for source_url in report.sources_used:
        if source_url not in evidence_urls:
            raise ReportValidationError(f"unsupported_source:{source_url}")
    for claim in report.key_findings:
        if not claim.text.strip():
            raise ReportValidationError("empty_claim")
        if not claim.source_urls:
            raise ReportValidationError("claim_without_source")
        for source_url in claim.source_urls:
            if source_url not in evidence_urls:
                raise ReportValidationError(f"unsupported_claim_source:{source_url}")

    for section in report.sections:
        if not section.heading.strip():
            raise ReportValidationError("empty_section_heading")
        if not section.paragraphs:
            raise ReportValidationError("empty_section")
        for paragraph in section.paragraphs:
            if not paragraph.text.strip():
                raise ReportValidationError("empty_paragraph")
            for source_url in paragraph.citations:
                if source_url not in evidence_urls:
                    raise ReportValidationError(f"unsupported_citation:{source_url}")

    for reference in report.references:
        if reference.url not in evidence_urls:
            raise ReportValidationError(f"unsupported_reference:{reference.url}")


def _claim_from_dict(payload: Any) -> ReportClaim:
    if not isinstance(payload, dict):
        raise ReportValidationError("invalid_claim")
    return ReportClaim(
        text=_required_string(payload, "text"),
        source_urls=_required_string_list(payload, "source_urls"),
    )


def _paragraph_from_dict(payload: Any) -> ReportParagraph:
    if not isinstance(payload, dict):
        raise ReportValidationError("invalid_paragraph")
    return ReportParagraph(
        text=_required_string(payload, "text"),
        citations=_optional_string_list(payload, "citations"),
    )


def _section_from_dict(payload: Any) -> ReportSection:
    if not isinstance(payload, dict):
        raise ReportValidationError("invalid_section")
    paragraphs = payload.get("paragraphs", [])
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ReportValidationError("invalid_section_paragraphs")
    return ReportSection(
        heading=_required_string(payload, "heading"),
        paragraphs=[_paragraph_from_dict(paragraph) for paragraph in paragraphs],
    )


def _reference_from_dict(payload: Any) -> Reference:
    if not isinstance(payload, dict):
        raise ReportValidationError("invalid_reference")
    credibility = payload.get("credibility_score", 0.0)
    if isinstance(credibility, bool) or not isinstance(credibility, (int, float)):
        credibility = 0.0
    return Reference(
        url=_required_string(payload, "url"),
        title=_optional_string(payload, "title") or _required_string(payload, "url"),
        credibility_score=float(credibility),
    )


def _required_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ReportValidationError(f"invalid_{name}")
    return value.strip()


def _required_string_list(payload: dict[str, Any], name: str) -> list[str]:
    value = payload.get(name)
    if not isinstance(value, list) or not value:
        raise ReportValidationError(f"invalid_{name}")
    normalized = [str(item).strip() for item in value if str(item).strip()]
    if len(normalized) != len(value):
        raise ReportValidationError(f"invalid_{name}")
    return normalized


def _optional_string_list(payload: dict[str, Any], name: str) -> list[str]:
    value = payload.get(name, [])
    if not isinstance(value, list):
        raise ReportValidationError(f"invalid_{name}")
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ReportValidationError(f"invalid_{name}")
    return value.strip()


def _required_confidence(payload: dict[str, Any]) -> float:
    value = payload.get("confidence")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ReportValidationError("invalid_confidence")
    confidence = float(value)
    if confidence < 0 or confidence > 1:
        raise ReportValidationError("invalid_confidence")
    return confidence
