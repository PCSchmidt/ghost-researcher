"""Session state contracts for planner and executor coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class EvidenceRecord:
    """Normalized extracted evidence that can support report claims."""

    url: str
    title: str
    claims: list[str]
    credibility_score: float
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class DetectionEvent:
    """Record a site detection or blocking event during browsing."""

    url: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class AgentSession:
    """Mutable session state for a single research job."""

    research_goal: str
    steps_taken: int = 0
    planner_turns: int = 0
    running_tokens: int = 0
    running_cost_usd: float = 0.0
    sources_visited: set[str] = field(default_factory=set)
    search_queries: list[str] = field(default_factory=list)
    evidence_records: list[EvidenceRecord] = field(default_factory=list)
    detection_events: list[DetectionEvent] = field(default_factory=list)
    termination_state: str = "active"
    termination_reason: str | None = None
    session_summary: str | None = None

    def increment_step(self, *, tokens: int = 0, cost_usd: float = 0.0) -> None:
        """Advance the session counters after a planner or tool step."""
        self.steps_taken += 1
        self.planner_turns += 1
        self.running_tokens += tokens
        self.running_cost_usd += cost_usd

    def register_source(self, url: str) -> bool:
        """Return True only when a source is first seen in this session."""
        if url in self.sources_visited:
            return False
        self.sources_visited.add(url)
        return True

    def record_search_query(self, query: str) -> None:
        """Track unique planner search attempts in order."""
        self.search_queries.append(query)

    def add_evidence(self, *, url: str, title: str, claims: list[str], credibility_score: float) -> None:
        """Append extracted evidence to the session record."""
        self.evidence_records.append(
            EvidenceRecord(
                url=url,
                title=title,
                claims=claims,
                credibility_score=credibility_score,
            )
        )

    def add_detection_event(self, *, url: str, reason: str) -> None:
        """Record that a source blocked or challenged automation."""
        self.detection_events.append(DetectionEvent(url=url, reason=reason))

    def should_summarize(self, threshold: int = 10) -> bool:
        """Signal when the session should compact old tool outputs."""
        return self.steps_taken > 0 and self.steps_taken % threshold == 0

    def can_continue(self, *, max_steps: int, max_tokens: int) -> bool:
        """Check hard research limits before issuing another planner step."""
        return self.steps_taken < max_steps and self.running_tokens < max_tokens and self.termination_state == "active"

    def finalize(self, reason: str) -> None:
        """Mark the session as finalized with a concrete termination reason."""
        self.termination_state = "finalized"
        self.termination_reason = reason
