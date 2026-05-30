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


class ResearchOrchestratorTests(unittest.IsolatedAsyncioTestCase):
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
        )

        result = await orchestrator.run_sequence("Review https://example.com/report")

        self.assertEqual(
            ["navigate_to_url", "extract_structured_data", "assess_credibility"],
            [decision.tool_call.name for decision in result.decisions],
        )
        self.assertEqual(3, result.session.steps_taken)
        self.assertEqual("finalized", result.session.termination_state)
        self.assertEqual("sufficient_coverage", result.session.termination_reason)
        self.assertEqual("Latest FAA guidance from 2026", result.session.session_summary)
        self.assertEqual(0.81, result.tool_results[-1]["score"])

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
        )

        result = await orchestrator.run_sequence("Find recent FAA BVLOS guidance")

        self.assertEqual(
            ["web_search", "navigate_to_url", "extract_structured_data", "assess_credibility"],
            [decision.tool_call.name for decision in result.decisions],
        )
        self.assertEqual(["Find recent FAA BVLOS guidance"], result.session.search_queries)
        self.assertEqual(["https://faa.gov/bvlos-guidance"], result.session.source_candidates)
        self.assertIn("https://faa.gov/bvlos-guidance", result.session.sources_visited)
        self.assertEqual("sufficient_coverage", result.session.termination_reason)


if __name__ == "__main__":
    unittest.main()
