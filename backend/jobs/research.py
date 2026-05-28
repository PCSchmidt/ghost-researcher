"""Planner-to-runner orchestration skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, PlannerSkeleton
from backend.config import Settings
from backend.jobs.runner import ResearchRunner


@dataclass(frozen=True, slots=True)
class PlannerRunResult:
    """Result from one planner integration pass."""

    session: AgentSession
    decision: PlannerDecision
    tool_result: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class PlannerSequenceResult:
    """Result from a deterministic multi-step planner sequence."""

    session: AgentSession
    decisions: list[PlannerDecision]
    tool_results: list[dict[str, Any]]


class ResearchOrchestrator:
    """Minimal planner integration path without synthesis."""

    def __init__(
        self,
        settings: Settings,
        *,
        planner: PlannerSkeleton | None = None,
        runner: ResearchRunner | None = None,
    ) -> None:
        self._planner = planner or PlannerSkeleton()
        self._runner = runner or ResearchRunner(settings)

    async def run_one_step(self, research_goal: str) -> PlannerRunResult:
        """Plan one tool call, dispatch it if available, and return the session state."""
        session = AgentSession(research_goal=research_goal)
        decision = self._planner.plan_next(session)
        if decision.should_stop:
            session.finalize(decision.termination_reason or "no_new_sources")
            return PlannerRunResult(session=session, decision=decision, tool_result=None)

        if decision.tool_call is None:
            session.finalize("no_new_sources")
            return PlannerRunResult(session=session, decision=decision, tool_result=None)

        tool_result = await self._runner.execute_tool_call(
            name=decision.tool_call.name,
            arguments=decision.tool_call.arguments,
            session=session,
        )
        return PlannerRunResult(session=session, decision=decision, tool_result=tool_result)

    async def run_sequence(self, research_goal: str, *, max_steps: int = 3) -> PlannerSequenceResult:
        """Run a deterministic tool sequence without synthesis or persistence."""
        session = AgentSession(research_goal=research_goal)
        decisions: list[PlannerDecision] = []
        tool_results: list[dict[str, Any]] = []

        for _ in range(max_steps):
            decision = self._planner.plan_next(session)
            decisions.append(decision)
            if decision.should_stop or decision.tool_call is None:
                session.finalize(decision.termination_reason or "no_new_sources")
                break

            tool_result = await self._runner.execute_tool_call(
                name=decision.tool_call.name,
                arguments=decision.tool_call.arguments,
                session=session,
            )
            tool_results.append(tool_result)
            if decision.tool_call.name == "extract_structured_data":
                session.session_summary = str(tool_result.get("text_excerpt", ""))
            if decision.tool_call.name == "assess_credibility":
                session.finalize("sufficient_coverage")
                break

        return PlannerSequenceResult(session=session, decisions=decisions, tool_results=tool_results)
