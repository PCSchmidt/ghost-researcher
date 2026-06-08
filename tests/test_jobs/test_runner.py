"""Regression tests for the thin research runner."""

from __future__ import annotations

import unittest

from backend.agent.memory import AgentSession
from backend.config import Settings
from backend.executor.credibility import CredibilityResult
from backend.executor.extract import ExtractionResult
from backend.executor.navigate import NavigationResult
from backend.executor.search import SearchResultItem, SearchResults
from backend.jobs.runner import ResearchRunner


class ResearchRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_executes_navigation_and_updates_session(self) -> None:
        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url="https://example.com/final",
                title="Example",
                status_code=200,
                content_excerpt="Example content",
                links=["https://example.com/about"],
                detection_blocked=False,
                blocked_reason=None,
                screenshot_path=None,
                timing_ms=15,
            )

        runner = ResearchRunner(Settings.from_env({}), navigate=fake_navigate)
        session = AgentSession(research_goal="Test navigation")

        payload = await runner.execute_tool_call(
            name="navigate_to_url",
            arguments={"url": "https://example.com/start", "wait_for": "#content"},
            session=session,
        )

        self.assertEqual("https://example.com/final", payload["final_url"])
        self.assertEqual(1, session.steps_taken)
        self.assertIn("https://example.com/final", session.sources_visited)

    async def test_runner_records_detection_events(self) -> None:
        async def fake_navigate(settings: Settings, **kwargs: object) -> NavigationResult:
            return NavigationResult(
                url=str(kwargs["url"]),
                final_url="https://example.com/challenge",
                title="Challenge",
                status_code=403,
                content_excerpt="verify you are human",
                links=[],
                detection_blocked=True,
                blocked_reason="bot_challenge",
                screenshot_path=None,
                timing_ms=10,
            )

        runner = ResearchRunner(Settings.from_env({}), navigate=fake_navigate)
        session = AgentSession(research_goal="Test challenge")

        await runner.execute_tool_call(
            name="navigate_to_url",
            arguments={"url": "https://example.com/challenge"},
            session=session,
        )

        self.assertEqual(1, len(session.detection_events))
        self.assertEqual("bot_challenge", session.detection_events[0].reason)

    async def test_runner_executes_search_and_records_candidates(self) -> None:
        async def fake_search(settings: Settings, **kwargs: object) -> SearchResults:
            return SearchResults(
                query=str(kwargs["query"]),
                results=[
                    SearchResultItem(
                        title="FAA guidance",
                        url="https://faa.gov/guidance",
                        snippet="FAA BVLOS guidance",
                        source_type="gov",
                    )
                ],
                new_result_count=1,
            )

        runner = ResearchRunner(Settings.from_env({}), search=fake_search)
        session = AgentSession(research_goal="Find FAA guidance")

        payload = await runner.execute_tool_call(
            name="web_search",
            arguments={"query": "Find FAA guidance"},
            session=session,
        )

        self.assertEqual(1, payload["new_result_count"])
        self.assertEqual(["Find FAA guidance"], session.search_queries)
        self.assertEqual(["https://faa.gov/guidance"], session.source_candidates)

    async def test_runner_rejects_unsupported_tools(self) -> None:
        runner = ResearchRunner(Settings.from_env({}))
        session = AgentSession(research_goal="Unsupported tool test")

        with self.assertRaisesRegex(NotImplementedError, "unsupported_tool"):
            await runner.execute_tool_call(
                name="take_screenshot",
                arguments={},
                session=session,
            )

    async def test_runner_executes_extraction(self) -> None:
        async def fake_extract(settings: Settings, **kwargs: object) -> ExtractionResult:
            return ExtractionResult(
                selector=str(kwargs["selector"]),
                extraction_goal=str(kwargs["extraction_goal"]),
                records=[{"text": "Example extracted text", "index": 0}],
                text_excerpt="Example extracted text",
                record_count=1,
                schema_valid=True,
            )

        runner = ResearchRunner(Settings.from_env({}), extract=fake_extract)
        session = AgentSession(research_goal="Extract page content")

        payload = await runner.execute_tool_call(
            name="extract_structured_data",
            arguments={"selector": "article", "extraction_goal": "collect article text"},
            session=session,
        )

        self.assertEqual(1, payload["record_count"])
        self.assertEqual(1, session.steps_taken)

    async def test_runner_executes_credibility_assessment(self) -> None:
        seen_kwargs: dict[str, object] = {}

        async def fake_assess(settings: Settings, **kwargs: object) -> CredibilityResult:
            seen_kwargs.update(kwargs)
            return CredibilityResult(
                url=str(kwargs["url"]),
                score=0.82,
                domain_authority=0.9,
                freshness=0.8,
                corroboration=0.5,
                detection_penalty=0.0,
                rationale="test rationale",
            )

        runner = ResearchRunner(Settings.from_env({}), assess=fake_assess)
        session = AgentSession(research_goal="Assess source credibility")
        session.add_evidence(
            url="https://faa.gov/other",
            title="Other FAA source",
            claims=["Other claim"],
            credibility_score=0.9,
        )

        payload = await runner.execute_tool_call(
            name="assess_credibility",
            arguments={"url": "https://faa.gov/example", "content_snippet": "Latest FAA guidance"},
            session=session,
        )

        self.assertEqual(0.82, payload["score"])
        self.assertEqual(["https://faa.gov/other"], seen_kwargs["corroborating_sources"])
        self.assertEqual(1, session.steps_taken)
        self.assertEqual(2, len(session.evidence_records))

    async def test_runner_executes_finalize_report(self) -> None:
        runner = ResearchRunner(Settings.from_env({}))
        session = AgentSession(research_goal="Finalize research")
        session.add_evidence(
            url="https://faa.gov/example",
            title="FAA Example",
            claims=["Example claim"],
            credibility_score=0.82,
        )

        payload = await runner.execute_tool_call(
            name="finalize_report",
            arguments={
                "confidence": 0.82,
                "sources_used": ["https://faa.gov/example"],
                "termination_reason": "sufficient_coverage",
            },
            session=session,
        )

        self.assertTrue(payload["accepted"])
        self.assertTrue(payload["queued_for_synthesis"])
        self.assertEqual("finalized", session.termination_state)
        self.assertEqual("sufficient_coverage", session.termination_reason)


if __name__ == "__main__":
    unittest.main()
