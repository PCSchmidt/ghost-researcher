"""Credibility scoring skeleton for source assessment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from backend.config import Settings

STOPWORDS = {
    "about",
    "according",
    "after",
    "also",
    "and",
    "are",
    "for",
    "from",
    "has",
    "have",
    "into",
    "its",
    "latest",
    "new",
    "not",
    "of",
    "on",
    "or",
    "source",
    "that",
    "the",
    "this",
    "to",
    "with",
}


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


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]{4,}", value.lower())
        if token not in STOPWORDS
    }


def _claim_overlap(content_snippet: str, corroborating_claims: list[str] | None) -> float:
    snippet_tokens = _meaningful_tokens(content_snippet)
    if not snippet_tokens:
        return 0.0
    best_overlap = 0.0
    for claim in corroborating_claims or []:
        claim_tokens = _meaningful_tokens(claim)
        if not claim_tokens:
            continue
        overlap = len(snippet_tokens.intersection(claim_tokens)) / max(1, min(len(snippet_tokens), len(claim_tokens)))
        best_overlap = max(best_overlap, overlap)
    return _clamp(best_overlap)


def _corroboration(
    content_snippet: str,
    corroborating_sources: list[str] | None,
    corroborating_claims: list[str] | None,
) -> float:
    source_count = len(set(corroborating_sources or []))
    distinct_domains = {
        hostname
        for source in (corroborating_sources or [])
        if (hostname := urlparse(source).hostname)
    }
    snippet = content_snippet.lower()
    evidence_markers = len(
        {
            marker
            for marker in (
                "according to",
                "cited",
                "reported",
                "data",
                "study",
                "regulation",
                "rulemaking",
                "federal register",
                "guidance",
            )
            if marker in snippet
        }
    )
    claim_overlap = _claim_overlap(content_snippet, corroborating_claims)
    score = (
        0.35
        + min(0.25, source_count * 0.08)
        + min(0.15, len(distinct_domains) * 0.06)
        + min(0.1, evidence_markers * 0.025)
        + min(0.15, claim_overlap * 0.15)
    )
    return _clamp(score)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


async def assess_credibility(
    settings: Settings,
    *,
    url: str,
    content_snippet: str,
    corroborating_sources: list[str] | None = None,
    corroborating_claims: list[str] | None = None,
) -> CredibilityResult:
    """Score source credibility with a transparent hand-tuned baseline."""
    del settings
    if not content_snippet.strip():
        raise ValueError("insufficient_content")

    domain_authority = _domain_authority(url)
    freshness = _freshness(content_snippet)
    corroboration = _corroboration(content_snippet, corroborating_sources, corroborating_claims)
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
