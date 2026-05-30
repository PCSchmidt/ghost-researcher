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
class ResearchReport:
    """Structured report emitted by the synthesizer."""

    title: str
    summary: str
    key_findings: list[ReportClaim]
    sources_used: list[str]
    confidence: float
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "key_findings": [claim.to_dict() for claim in self.key_findings],
            "sources_used": self.sources_used,
            "confidence": self.confidence,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchReport":
        claims = payload.get("key_findings", [])
        if not isinstance(claims, list):
            raise ReportValidationError("invalid_key_findings")
        return cls(
            title=_required_string(payload, "title"),
            summary=_required_string(payload, "summary"),
            key_findings=[_claim_from_dict(claim) for claim in claims],
            sources_used=_required_string_list(payload, "sources_used"),
            confidence=_required_confidence(payload),
            limitations=_optional_string_list(payload, "limitations"),
        )


def validate_report_sources(report: ResearchReport, evidence_records: list[EvidenceRecord]) -> None:
    """Ensure every cited source exists in the session evidence record."""
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


def _claim_from_dict(payload: Any) -> ReportClaim:
    if not isinstance(payload, dict):
        raise ReportValidationError("invalid_claim")
    return ReportClaim(
        text=_required_string(payload, "text"),
        source_urls=_required_string_list(payload, "source_urls"),
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


def _required_confidence(payload: dict[str, Any]) -> float:
    value = payload.get("confidence")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ReportValidationError("invalid_confidence")
    confidence = float(value)
    if confidence < 0 or confidence > 1:
        raise ReportValidationError("invalid_confidence")
    return confidence
