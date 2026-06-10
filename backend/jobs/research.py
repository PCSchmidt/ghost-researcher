"""Planner-to-runner orchestration skeleton."""

from __future__ import annotations

import inspect
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

from backend.agent.memory import AgentSession
from backend.agent.openrouter import OpenRouterPlanner
from backend.agent.planner import PlannerDecision, PlannerSkeleton, ToolCall
from backend.config import Settings
from backend.jobs.runner import ResearchRunner
from backend.synthesizer.report import ReportSynthesizer, SynthesisError
from backend.synthesizer.schema import ResearchReport

logger = logging.getLogger("ghostresearcher.research")


class PlannerLike(Protocol):
    def plan_next(
        self,
        session: AgentSession,
        *,
        last_tool_result: dict[str, Any] | None = None,
    ) -> PlannerDecision | Any: ...


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
    synthesis: ResearchReport | None = None


class ResearchOrchestrator:
    """Minimal planner integration path without synthesis."""

    def __init__(
        self,
        settings: Settings,
        *,
        planner: PlannerLike | None = None,
        runner: ResearchRunner | None = None,
        synthesizer: Any | None = None,
    ) -> None:
        self._settings = settings
        self._planner = planner or _default_planner(settings)
        self._runner = runner or ResearchRunner(settings)
        self._synthesizer = synthesizer or ReportSynthesizer(settings)

    async def _plan_next(
        self,
        session: AgentSession,
        *,
        last_tool_result: dict[str, Any] | None = None,
    ) -> PlannerDecision:
        planned = self._planner.plan_next(session, last_tool_result=last_tool_result)
        if inspect.isawaitable(planned):
            planned = await planned
        return planned

    async def run_one_step(self, research_goal: str) -> PlannerRunResult:
        """Plan one tool call, dispatch it if available, and return the session state."""
        session = AgentSession(research_goal=research_goal)
        decision = await self._plan_next(session)
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

    async def run_sequence(self, research_goal: str, *, max_steps: int = 15, min_sources: int = 4) -> PlannerSequenceResult:
        """Run a deterministic tool sequence without synthesis or persistence."""
        session = AgentSession(research_goal=research_goal)
        if isinstance(self._planner, PlannerSkeleton):
            self._planner = PlannerSkeleton(min_sources=min_sources)
        decisions: list[PlannerDecision] = []
        tool_results: list[dict[str, Any]] = []
        last_tool_result: dict[str, Any] | None = None
        started_at = time.monotonic()
        time_budget = self._settings.job_time_budget_seconds

        # The whole planner loop is wrapped so an unexpected mid-run failure
        # (a flaky CDP/browser call, an OpenRouter hiccup) does not 500 the request
        # and discard every source already gathered. On error we finalize and fall
        # through to synthesis on whatever evidence exists — the same graceful
        # degradation the wall-clock budget already provides.
        try:
            for step in range(max_steps):
                # Wall-clock guard: heavy goals can hit many slow sources and exceed the
                # HTTP request timeout. When the budget is spent, stop planning and let
                # synthesis run on whatever evidence exists so the job returns a report
                # instead of failing.
                if time_budget > 0 and time.monotonic() - started_at > time_budget:
                    if session.termination_state == "active":
                        session.finalize("time_budget")
                    break
                decision = await self._plan_next(session, last_tool_result=last_tool_result)
                decision = self._guard_premature_finalize(session, decision, min_sources=min_sources)
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
                last_tool_result = tool_result
                if decision.tool_call.name == "navigate_to_url":
                    session.session_summary = None
                    # Create baseline evidence from the navigate result itself.
                    # Extraction may fail on JS-heavy/paywalled sites, but navigate
                    # always captures the page title and a text excerpt from full HTML.
                    if not tool_result.get("detection_blocked"):
                        title = tool_result.get("title", "") or tool_result.get("final_url", "")
                        excerpt = tool_result.get("content_excerpt", "")
                        if excerpt or title:
                            session.add_evidence(
                                url=tool_result.get("final_url", tool_result.get("url", "")),
                                title=title,
                                claims=[excerpt] if excerpt else [title],
                                credibility_score=0.5,
                                evidence_type="navigation_fallback",
                            )
                if decision.tool_call.name == "extract_structured_data":
                    session.session_summary = str(tool_result.get("text_excerpt", ""))
                if decision.tool_call.name == "finalize_report":
                    break
                if decision.tool_call.name == "web_search" and tool_result.get("new_result_count", 0) == 0:
                    session.finalize("no_new_sources")
                    break

                # Deterministic fallback: after 2+ consecutive searches with zero navigations,
                # force navigate+extract on top source candidates.
                recent = decisions[-3:]
                recent_searches = sum(1 for d in recent if d.tool_call and d.tool_call.name == "web_search")
                recent_navs = sum(1 for d in recent if d.tool_call and d.tool_call.name == "navigate_to_url")
                if recent_searches >= 2 and recent_navs == 0 and session.source_candidates:
                    for candidate_url in session.source_candidates:
                        if candidate_url in session.sources_visited or not candidate_url.startswith("http"):
                            continue
                        nav_result = await self._runner.execute_tool_call(
                            name="navigate_to_url",
                            arguments={"url": candidate_url},
                            session=session,
                        )
                        tool_results.append(nav_result)
                        last_tool_result = nav_result
                        if not nav_result.get("detection_blocked"):
                            ext_result = await self._runner.execute_tool_call(
                                name="extract_structured_data",
                                arguments={"selector": "body", "extraction_goal": "Extract key facts and data"},
                                session=session,
                            )
                            tool_results.append(ext_result)
                            last_tool_result = ext_result
                        break  # one forced navigate+extract per fallback trigger
            else:
                # Exhausted max_steps without explicit finalize_report or stop signal.
                # termination_state defaults to the truthy "active", so `not state` never
                # fired and finished jobs were left "active". Guard on "active" explicitly
                # (matching the time-budget guard above) so they finalize as "max_steps".
                if session.termination_state == "active":
                    session.finalize("max_steps")
        except Exception:  # noqa: BLE001 - degrade to a partial report, never 500 away gathered evidence
            logger.exception(
                "research loop failed; finalizing on gathered evidence (goal=%r, sources=%d)",
                research_goal,
                len(session.sources_visited),
            )
            if session.termination_state == "active":
                session.finalize("error")

        synthesis = await self._synthesize_if_ready(session)
        return PlannerSequenceResult(session=session, decisions=decisions, tool_results=tool_results, synthesis=synthesis)

    def _guard_premature_finalize(
        self,
        session: AgentSession,
        decision: PlannerDecision,
        *,
        min_sources: int,
    ) -> PlannerDecision:
        if decision.tool_call is None or decision.tool_call.name != "finalize_report":
            return decision
        if decision.tool_call.arguments.get("termination_reason") != "sufficient_coverage":
            return decision
        if len(session.evidence_records_by_type("assessed")) >= min_sources:
            return decision

        current_url = session.current_source_url
        if current_url and current_url in session.sources_visited:
            assessed_urls = session.evidence_urls_by_type("assessed")
            extracted_urls = session.evidence_urls_by_type("extracted").union(assessed_urls)
            if current_url not in extracted_urls:
                return PlannerDecision(
                    tool_call=ToolCall(
                        name="extract_structured_data",
                        arguments={"selector": "body", "extraction_goal": "extract main page text"},
                    )
                )
            if session.session_summary is not None and current_url not in assessed_urls:
                return PlannerDecision(
                    tool_call=ToolCall(
                        name="assess_credibility",
                        arguments={"url": current_url, "content_snippet": session.session_summary},
                    )
                )

        candidate = session.next_source_candidate()
        if candidate is not None:
            return PlannerDecision(tool_call=ToolCall(name="navigate_to_url", arguments={"url": candidate}))
        return decision

    async def _synthesize_if_ready(self, session: AgentSession) -> ResearchReport | None:
        if not session.evidence_records:
            return None
        try:
            return await self._synthesizer.synthesize(session)
        except SynthesisError:
            return None
        except Exception:  # noqa: BLE001 - a synthesis transport failure must not 500 the run
            logger.exception("synthesis failed; returning job without a report (goal=%r)", session.research_goal)
            return None


def _default_planner(settings: Settings) -> PlannerLike:
    if settings.openrouter_api_key:
        return OpenRouterPlanner(settings)
    return PlannerSkeleton()
