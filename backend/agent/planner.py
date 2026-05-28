"""Deterministic planner skeleton for early integration tests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.agent.memory import AgentSession
from backend.agent.tools import get_tool

URL_PATTERN = re.compile(r"https?://[^\s)\]}>'\"]+")


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Structured tool call emitted by the planner."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PlannerDecision:
    """Planner output for one integration step."""

    tool_call: ToolCall | None
    termination_reason: str | None = None

    @property
    def should_stop(self) -> bool:
        return self.tool_call is None and self.termination_reason is not None


class PlannerSkeleton:
    """Small deterministic planner used before the Claude planner loop exists."""

    def plan_next(self, session: AgentSession) -> PlannerDecision:
        """Choose the next tool call from the current session state."""
        if session.steps_taken == 0:
            return self._plan_navigation(session)
        if session.steps_taken == 1:
            return self._plan_extraction()
        if session.steps_taken == 2:
            return self._plan_credibility(session)
        return PlannerDecision(tool_call=None, termination_reason="sufficient_coverage")

    def _plan_navigation(self, session: AgentSession) -> PlannerDecision:
        next_url = self._first_unvisited_url(session)
        if next_url is None:
            return PlannerDecision(tool_call=None, termination_reason="no_new_sources")

        tool = get_tool("navigate_to_url")
        return PlannerDecision(
            tool_call=ToolCall(
                name=tool["name"],
                arguments={"url": next_url},
            )
        )

    def _plan_extraction(self) -> PlannerDecision:
        tool = get_tool("extract_structured_data")
        return PlannerDecision(
            tool_call=ToolCall(
                name=tool["name"],
                arguments={"selector": "body", "extraction_goal": "extract main page text"},
            )
        )

    def _plan_credibility(self, session: AgentSession) -> PlannerDecision:
        if not session.sources_visited or session.session_summary is None:
            return PlannerDecision(tool_call=None, termination_reason="sufficient_coverage")

        tool = get_tool("assess_credibility")
        return PlannerDecision(
            tool_call=ToolCall(
                name=tool["name"],
                arguments={
                    "url": sorted(session.sources_visited)[-1],
                    "content_snippet": session.session_summary,
                },
            )
        )

    def _first_unvisited_url(self, session: AgentSession) -> str | None:
        for match in URL_PATTERN.finditer(session.research_goal):
            url = match.group(0).rstrip(".,;")
            if url not in session.sources_visited:
                return url
        return None
