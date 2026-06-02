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

        result = await orchestrator.run_sequence("Review https://example.com/report")

        self.assertEqual(
            ["navigate_to_url", "extract_structured_data", "assess_credibility", "finalize_report"],
            [decision.tool_call.name for decision in result.decisions],
        )
        self.assertEqual(4, result.session.steps_taken)
        self.assertEqual("finalized", result.session.termination_state)
        self.assertEqual("sufficient_coverage", result.session.termination_reason)
        self.assertEqual("Latest FAA guidance from 2026", result.session.session_summary)
        self.assertEqual(0.81, result.tool_results[-2]["score"])
        self.assertEqual("Synthesized report", result.synthesis.title)

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

        result = await orchestrator.run_sequence("Find recent FAA BVLOS guidance")

        self.assertEqual(
            ["web_search", "navigate_to_url", "extract_structured_data", "assess_credibility", "finalize_report"],
            [decision.tool_call.name for decision in result.decisions],
        )
        self.assertEqual(["Find recent FAA BVLOS guidance"], result.session.search_queries)
        self.assertEqual(["https://faa.gov/bvlos-guidance"], result.session.source_candidates)
        self.assertIn("https://faa.gov/bvlos-guidance", result.session.sources_visited)
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

        self.assertEqual(2, len(result.session.evidence_records))
        self.assertEqual("sufficient_coverage", result.session.termination_reason)
        self.assertEqual("finalize_report", result.decisions[-1].tool_call.name)
        self.assertEqual(2, len(result.synthesis.sources_used))

    async def test_orchestrator_leaves_synthesis_empty_when_not_finalized_with_coverage(self) -> None:
        orchestrator = ResearchOrchestrator(Settings.from_env({}))

        result = await orchestrator.run_sequence("Find FAA BVLOS guidance", max_steps=1)

        self.assertIsNone(result.synthesis)


if __name__ == "__main__":
    unittest.main()
