"""Credibility scoring skeleton for source assessment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from backend.config import Settings


@dataclass(frozen=True, slots=True)
class CredibilityResult:
    """Normalized output for assess_credibility."""

    url: str
    score: float
    domain_authority: float
    freshness: float
    corroboration: float
    detection_penalty: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "score": self.score,
            "domain_authority": self.domain_authority,
            "freshness": self.freshness,
            "corroboration": self.corroboration,
            "detection_penalty": self.detection_penalty,
            "rationale": self.rationale,
        }


def _domain_authority(url: str) -> float:
    hostname = urlparse(url).hostname or ""
    if hostname.endswith(".gov") or hostname.endswith(".mil"):
        return 0.95
    if hostname.endswith(".edu"):
        return 0.9
    if hostname.endswith(".org"):
        return 0.75
    if hostname.endswith(".com"):
        return 0.6
    return 0.45


def _freshness(content_snippet: str) -> float:
    snippet = content_snippet.lower()
    if re.search(r"\b2026\b|latest|recent|today|this week|this month", snippet):
        return 0.85
    if re.search(r"\b2025\b|last year", snippet):
        return 0.65
    return 0.5


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


async def assess_credibility(
    settings: Settings,
    *,
    url: str,
    content_snippet: str,
) -> CredibilityResult:
    """Score source credibility with a transparent hand-tuned baseline."""
    del settings
    if not content_snippet.strip():
        raise ValueError("insufficient_content")

    domain_authority = _domain_authority(url)
    freshness = _freshness(content_snippet)
    corroboration = 0.5
    detection_penalty = 0.0
    score = _clamp((domain_authority * 0.45) + (freshness * 0.3) + (corroboration * 0.25) - detection_penalty)
    rationale = (
        f"domain_authority={domain_authority:.2f}; freshness={freshness:.2f}; "
        f"corroboration={corroboration:.2f}; detection_penalty={detection_penalty:.2f}"
    )
    return CredibilityResult(
        url=url,
        score=score,
        domain_authority=domain_authority,
        freshness=freshness,
        corroboration=corroboration,
        detection_penalty=detection_penalty,
        rationale=rationale,
    )
