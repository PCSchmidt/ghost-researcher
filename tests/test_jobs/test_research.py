"""Regression tests for the planner-to-runner orchestration skeleton."""

from __future__ import annotations

import unittest

from backend.config import Settings
from backend.executor.credibility import CredibilityResult
from backend.executor.extract import ExtractionResult
from backend.executor.navigate import NavigationResult
from backend.executor.search import SearchResultItem, SearchResults
from backend.jobs.research import ResearchOrchestrator
from backend.jobs.runner import ResearchRunner
from backend.synthesizer.schema import ResearchReport, ReportClaim


class FakeSynthesizer:
    async def synthesize(self, session) -> ResearchReport:
        return ResearchReport(
            title="Synthesized report",
            summary="Latest FAA BVLOS guidance",
            key_findings=[
                ReportClaim(text="Latest FAA BVLOS guidance", source_urls=["https://example.com/report"])
            ],
            sources_used=["https://example.com/report"],
            confidence=0.81,
        )


class ResearchOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrator_accepts_async_planner(self) -> None:
        class AsyncPlanner:
            async def plan_next(
                self,
                session,
                *,
                last_tool_result=None,
            ):
                from backend.agent.planner import PlannerDecision, ToolCall

                return PlannerDecision(
                    tool_call=ToolCall(
                        name="web_search",
                        arguments={"query": session.research_goal, "num_results": 1},
                    )
                )

        async def fake_search(settings: Settings, **kwargs: object) -> SearchResults:
            return SearchResults(query=str(kwargs["query"]), results=[], new_result_count=0)

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            planner=AsyncPlanner(),
            runner=ResearchRunner(settings, search=fake_search),
        )

        result = await orchestrator.run_one_step("Find recent FAA BVLOS guidance")

        self.assertEqual("web_search", result.decision.tool_call.name)
        self.assertEqual("Find recent FAA BVLOS guidance", result.tool_result["query"])

    async def test_orchestrator_dispatches_planned_navigation(self) -> None:
        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url=str(kwargs["url"]),
                title="Example Report",
                status_code=200,
                content_excerpt="Example report content",
                links=[],
                detection_blocked=False,
                blocked_reason=None,
                screenshot_path=None,
                timing_ms=7,
            )

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            runner=ResearchRunner(settings, navigate=fake_navigate),
        )

        result = await orchestrator.run_one_step("Review https://example.com/report")

        self.assertEqual("navigate_to_url", result.decision.tool_call.name)
        self.assertEqual("https://example.com/report", result.tool_result["final_url"])
        self.assertEqual(1, result.session.steps_taken)
        self.assertIn("https://example.com/report", result.session.sources_visited)

    async def test_orchestrator_searches_when_goal_has_no_url(self) -> None:
        orchestrator = ResearchOrchestrator(Settings.from_env({}))

        result = await orchestrator.run_one_step("Find recent FAA BVLOS guidance")

        self.assertEqual("web_search", result.decision.tool_call.name)
        self.assertEqual(5, result.tool_result["new_result_count"])
        self.assertEqual(["Find recent FAA BVLOS guidance"], result.session.search_queries)
        self.assertEqual(5, len(result.session.source_candidates))

    async def test_orchestrator_runs_navigation_extraction_and_credibility_sequence(self) -> None:
        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url=str(kwargs["url"]),
                title="FAA Report",
                status_code=200,
                content_excerpt="FAA report content",
                links=[],
                detection_blocked=False,
                blocked_reason=None,
                screenshot_path=None,
                timing_ms=7,
            )

        async def fake_extract(settings: Settings, **kwargs: object) -> ExtractionResult:
            return ExtractionResult(
                selector=str(kwargs["selector"]),
                extraction_goal=str(kwargs["extraction_goal"]),
                records=[{"text": "Latest FAA guidance from 2026", "index": 0}],
                text_excerpt="Latest FAA guidance from 2026",
                record_count=1,
                schema_valid=True,
            )

        async def fake_assess(settings: Settings, **kwargs: object) -> CredibilityResult:
            return CredibilityResult(
                url=str(kwargs["url"]),
                score=0.81,
                domain_authority=0.6,
                freshness=0.85,
                corroboration=0.5,
                detection_penalty=0.0,
                rationale="test rationale",
            )

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            runner=ResearchRunner(settings, navigate=fake_navigate, extract=fake_extract, assess=fake_assess),
            synthesizer=FakeSynthesizer(),
        )

        result = await orchestrator.run_sequence("Review https://example.com/report", min_sources=1)

        self.assertEqual(
            ["navigate_to_url", "extract_structured_data", "assess_credibility", "finalize_report"],
            [decision.tool_call.name for decision in result.decisions if decision.tool_call is not None],
        )
        self.assertEqual(4, result.session.steps_taken)
        self.assertEqual(1, len(result.session.evidence_records_by_type("extracted")))
        self.assertEqual(1, len(result.session.evidence_records_by_type("assessed")))
        self.assertEqual("finalized", result.session.termination_state)
        self.assertEqual("sufficient_coverage", result.session.termination_reason)
        self.assertIsNotNone(result.synthesis)

    async def test_orchestrator_guards_premature_finalize_after_navigation_evidence(self) -> None:
        from backend.agent.planner import PlannerDecision, ToolCall

        class PrematurePlanner:
            def __init__(self) -> None:
                self.calls = 0

            def plan_next(self, session, *, last_tool_result=None):
                self.calls += 1
                if self.calls == 1:
                    return PlannerDecision(
                        tool_call=ToolCall(
                            name="navigate_to_url",
                            arguments={"url": "https://example.com/report"},
                        )
                    )
                return PlannerDecision(
                    tool_call=ToolCall(
                        name="finalize_report",
                        arguments={
                            "confidence": 0.5,
                            "sources_used": ["https://example.com/report"],
                            "termination_reason": "sufficient_coverage",
                        },
                    )
                )

        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url=str(kwargs["url"]),
                title="Example Report",
                status_code=200,
                content_excerpt="Example report content",
                links=[],
                detection_blocked=False,
                blocked_reason=None,
                screenshot_path=None,
                timing_ms=7,
            )

        async def fake_extract(settings: Settings, **kwargs: object) -> ExtractionResult:
            return ExtractionResult(
                selector=str(kwargs["selector"]),
                extraction_goal=str(kwargs["extraction_goal"]),
                records=[{"text": "Latest report content from 2026", "index": 0}],
                text_excerpt="Latest report content from 2026",
                record_count=1,
                schema_valid=True,
            )

        async def fake_assess(settings: Settings, **kwargs: object) -> CredibilityResult:
            return CredibilityResult(
                url=str(kwargs["url"]),
                score=0.81,
                domain_authority=0.6,
                freshness=0.85,
                corroboration=0.5,
                detection_penalty=0.0,
                rationale="test rationale",
            )

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            planner=PrematurePlanner(),
            runner=ResearchRunner(settings, navigate=fake_navigate, extract=fake_extract, assess=fake_assess),
            synthesizer=FakeSynthesizer(),
        )

        result = await orchestrator.run_sequence("Review https://example.com/report", min_sources=1)

        self.assertEqual(
            ["navigate_to_url", "extract_structured_data", "assess_credibility", "finalize_report"],
            [decision.tool_call.name for decision in result.decisions if decision.tool_call is not None],
        )
        self.assertEqual(1, len(result.session.evidence_records_by_type("extracted")))
        self.assertEqual(1, len(result.session.evidence_records_by_type("assessed")))

    async def test_orchestrator_runs_search_first_for_url_free_goal(self) -> None:
        async def fake_search(settings: Settings, **kwargs: object) -> SearchResults:
            return SearchResults(
                query=str(kwargs["query"]),
                results=[
                    SearchResultItem(
                        title="FAA guidance",
                        url="https://faa.gov/bvlos-guidance",
                        snippet="FAA BVLOS guidance",
                        source_type="gov",
                    )
                ],
                new_result_count=1,
            )

        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url=str(kwargs["url"]),
                title="FAA Guidance",
                status_code=200,
                content_excerpt="FAA guidance content",
                links=[],
                detection_blocked=False,
                blocked_reason=None,
                screenshot_path=None,
                timing_ms=7,
            )

        async def fake_extract(settings: Settings, **kwargs: object) -> ExtractionResult:
            return ExtractionResult(
                selector=str(kwargs["selector"]),
                extraction_goal=str(kwargs["extraction_goal"]),
                records=[{"text": "Latest FAA BVLOS guidance", "index": 0}],
                text_excerpt="Latest FAA BVLOS guidance",
                record_count=1,
                schema_valid=True,
            )

        async def fake_assess(settings: Settings, **kwargs: object) -> CredibilityResult:
            return CredibilityResult(
                url=str(kwargs["url"]),
                score=0.9,
                domain_authority=0.95,
                freshness=0.85,
                corroboration=0.5,
                detection_penalty=0.0,
                rationale="test rationale",
            )

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            runner=ResearchRunner(
                settings,
                search=fake_search,
                navigate=fake_navigate,
                extract=fake_extract,
                assess=fake_assess,
            ),
            synthesizer=FakeSynthesizer(),
        )

        result = await orchestrator.run_sequence("Find recent FAA BVLOS guidance", min_sources=1)

        self.assertEqual(
            ["web_search", "navigate_to_url", "extract_structured_data", "assess_credibility", "finalize_report"],
            [decision.tool_call.name for decision in result.decisions if decision.tool_call is not None],
        )
        self.assertEqual(["Find recent FAA BVLOS guidance"], result.session.search_queries)
        self.assertEqual(["https://faa.gov/bvlos-guidance"], result.session.source_candidates)
        self.assertIn("https://faa.gov/bvlos-guidance", result.session.sources_visited)
        self.assertEqual(1, len(result.session.evidence_records_by_type("extracted")))
        self.assertEqual(1, len(result.session.evidence_records_by_type("assessed")))
        self.assertEqual("sufficient_coverage", result.session.termination_reason)

    async def test_orchestrator_runs_multi_source_sequence_when_requested(self) -> None:
        async def fake_search(settings: Settings, **kwargs: object) -> SearchResults:
            return SearchResults(
                query=str(kwargs["query"]),
                results=[
                    SearchResultItem(title="FAA", url="https://faa.gov/one", snippet="FAA", source_type="gov"),
                    SearchResultItem(
                        title="Federal Register",
                        url="https://federalregister.gov/two",
                        snippet="Federal Register",
                        source_type="gov",
                    ),
                ],
                new_result_count=2,
            )

        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url=str(kwargs["url"]),
                title="Source",
                status_code=200,
                content_excerpt="Source content",
                links=[],
                detection_blocked=False,
                blocked_reason=None,
                screenshot_path=None,
                timing_ms=7,
            )

        async def fake_extract(settings: Settings, **kwargs: object) -> ExtractionResult:
            return ExtractionResult(
                selector=str(kwargs["selector"]),
                extraction_goal=str(kwargs["extraction_goal"]),
                records=[{"text": "Latest FAA guidance", "index": 0}],
                text_excerpt="Latest FAA guidance",
                record_count=1,
                schema_valid=True,
            )

        async def fake_assess(settings: Settings, **kwargs: object) -> CredibilityResult:
            return CredibilityResult(
                url=str(kwargs["url"]),
                score=0.9,
                domain_authority=0.95,
                freshness=0.85,
                corroboration=0.5,
                detection_penalty=0.0,
                rationale="test rationale",
            )

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            runner=ResearchRunner(settings, search=fake_search, navigate=fake_navigate, extract=fake_extract, assess=fake_assess),
        )

        result = await orchestrator.run_sequence("Find FAA guidance", max_steps=8, min_sources=2)

        self.assertEqual(2, len(result.session.evidence_records_by_type("extracted")))
        self.assertEqual(2, len(result.session.evidence_records_by_type("assessed")))
        self.assertEqual("sufficient_coverage", result.session.termination_reason)
        self.assertEqual("finalize_report", result.decisions[-1].tool_call.name)
        self.assertEqual(2, len(result.synthesis.sources_used))

    async def test_orchestrator_leaves_synthesis_empty_when_not_finalized_with_coverage(self) -> None:
        orchestrator = ResearchOrchestrator(Settings.from_env({}))

        result = await orchestrator.run_sequence("Find FAA BVLOS guidance", max_steps=1)

        self.assertIsNone(result.synthesis)

    async def test_run_sequence_stops_and_synthesizes_on_time_budget(self) -> None:
        # A heavy goal must not run forever: when the wall-clock budget is spent the
        # loop stops planning, finalizes as time_budget, and still returns a report.
        import asyncio

        from backend.agent.planner import PlannerDecision, ToolCall

        class NeverStopsPlanner:
            async def plan_next(self, session, *, last_tool_result=None):
                return PlannerDecision(
                    tool_call=ToolCall(name="navigate_to_url", arguments={"url": "https://example.com/a"})
                )

        class SlowRunner:
            async def execute_tool_call(self, *, name, arguments, session):
                await asyncio.sleep(0.02)
                session.increment_step()
                return {
                    "title": "Source",
                    "content_excerpt": "useful evidence text from the page",
                    "final_url": arguments.get("url"),
                    "detection_blocked": False,
                }

        settings = Settings.from_env({"JOB_TIME_BUDGET_SECONDS": "0.01"})
        orchestrator = ResearchOrchestrator(
            settings,
            planner=NeverStopsPlanner(),
            runner=SlowRunner(),
            synthesizer=FakeSynthesizer(),
        )

        result = await orchestrator.run_sequence("Research a demanding topic", max_steps=50, min_sources=3)

        self.assertEqual("time_budget", result.session.termination_reason)
        self.assertLess(len(result.decisions), 50)
        self.assertIsNotNone(result.synthesis)

    async def test_run_sequence_finalizes_as_max_steps_when_loop_exhausted(self) -> None:
        # A run that never calls finalize_report must still end "finalized" with reason
        # "max_steps" (not left "active"), since termination_state defaults to "active".
        from backend.agent.planner import PlannerDecision, ToolCall

        class AlwaysNavigatePlanner:
            def __init__(self) -> None:
                self.calls = 0

            async def plan_next(self, session, *, last_tool_result=None):
                self.calls += 1
                return PlannerDecision(
                    tool_call=ToolCall(
                        name="navigate_to_url",
                        arguments={"url": f"https://example.com/{self.calls}"},
                    )
                )

        class OkRunner:
            async def execute_tool_call(self, *, name, arguments, session):
                session.increment_step()
                return {
                    "title": "Source",
                    "content_excerpt": "useful evidence text from the page",
                    "final_url": arguments.get("url"),
                    "detection_blocked": False,
                }

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            planner=AlwaysNavigatePlanner(),
            runner=OkRunner(),
            synthesizer=FakeSynthesizer(),
        )

        result = await orchestrator.run_sequence("Research a broad topic", max_steps=3, min_sources=3)

        self.assertEqual("finalized", result.session.termination_state)
        self.assertEqual("max_steps", result.session.termination_reason)

    async def test_run_sequence_degrades_to_partial_report_on_mid_loop_error(self) -> None:
        # A flaky tool call mid-run (e.g. a CDP/browser failure) must not propagate
        # and 500 the request, discarding everything already gathered. The loop should
        # finalize as "error" and still synthesize from the evidence collected so far.
        from backend.agent.planner import PlannerDecision, ToolCall

        class FlakyRunner:
            def __init__(self) -> None:
                self.calls = 0

            async def execute_tool_call(self, *, name, arguments, session):
                self.calls += 1
                if self.calls == 1:
                    session.increment_step()
                    return {
                        "title": "First Source",
                        "content_excerpt": "useful evidence from the first page",
                        "final_url": arguments.get("url"),
                        "detection_blocked": False,
                    }
                raise RuntimeError("connect_over_cdp: simulated browser failure")

        class AlwaysNavigatePlanner:
            def __init__(self) -> None:
                self.calls = 0

            async def plan_next(self, session, *, last_tool_result=None):
                self.calls += 1
                return PlannerDecision(
                    tool_call=ToolCall(
                        name="navigate_to_url",
                        arguments={"url": f"https://example.com/{self.calls}"},
                    )
                )

        settings = Settings.from_env({})
        orchestrator = ResearchOrchestrator(
            settings,
            planner=AlwaysNavigatePlanner(),
            runner=FlakyRunner(),
            synthesizer=FakeSynthesizer(),
        )

        # Must not raise: the mid-loop RuntimeError is caught and degraded.
        result = await orchestrator.run_sequence("Research a demanding topic", max_steps=10, min_sources=3)

        self.assertEqual("error", result.session.termination_reason)
        self.assertEqual("finalized", result.session.termination_state)
        self.assertIsNotNone(result.synthesis)
        self.assertGreaterEqual(len(result.session.evidence_records), 1)


if __name__ == "__main__":
    unittest.main()
