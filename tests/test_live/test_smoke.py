"""Skipped-by-default live integration smoke tests.

These tests intentionally require GHOSTRESEARCHER_RUN_LIVE_TESTS=1 plus the
provider-specific environment variables. The default regression suite must stay
network-free and secret-free.
"""

from __future__ import annotations

import os
import unittest

from backend.agent.memory import AgentSession
from backend.agent.openrouter import OpenRouterPlanner
from backend.config import Settings
from backend.executor.browser import CloakBrowserClient
from backend.executor.navigate import navigate_to_url
from backend.executor.search import SearchProviderError, web_search
from backend.synthesizer.report import ReportSynthesizer

RUN_LIVE_TESTS = os.environ.get("GHOSTRESEARCHER_RUN_LIVE_TESTS") == "1"


def _live_skip_reason(required: list[str]) -> str:
    missing = [name for name in required if not os.environ.get(name)]
    if not RUN_LIVE_TESTS:
        return "set GHOSTRESEARCHER_RUN_LIVE_TESTS=1 to run live smoke tests"
    if missing:
        return "missing live smoke env vars: " + ", ".join(missing)
    return ""


def _skip_unless_live(*required: str) -> None:
    reason = _live_skip_reason(list(required))
    if reason:
        raise unittest.SkipTest(reason)


class LiveSearchSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_brave_search_returns_normalized_candidates(self) -> None:
        _skip_unless_live("SEARCH_API_KEY")
        settings = Settings.from_env(os.environ)
        if settings.search_provider.strip().lower() != "brave":
            self.skipTest("set SEARCH_PROVIDER=brave to run Brave Search smoke test")
        try:
            results = await web_search(settings, query="FAA UAS rulemaking", num_results=3)
        except SearchProviderError as exc:
            self.skipTest(f"Brave Search is unreachable from this environment: {exc}")

        self.assertGreater(results.new_result_count, 0)
        self.assertLessEqual(len(results.results), 3)
        self.assertTrue(all(item.url.startswith(("http://", "https://")) for item in results.results))
        self.assertTrue(all(item.title for item in results.results))


class LiveOpenRouterSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_openrouter_planner_returns_valid_tool_call(self) -> None:
        _skip_unless_live("OPENROUTER_API_KEY")
        settings = Settings.from_env(os.environ)
        planner = OpenRouterPlanner(settings)

        decision = await planner.plan_next(AgentSession(research_goal="Find recent FAA UAS rulemaking updates"))

        self.assertIsNotNone(decision.tool_call)
        self.assertIn(
            decision.tool_call.name,
            {"web_search", "navigate_to_url", "extract_structured_data", "assess_credibility", "finalize_report"},
        )

    async def test_openrouter_synthesizer_returns_source_grounded_report(self) -> None:
        _skip_unless_live("OPENROUTER_API_KEY")
        settings = Settings.from_env(os.environ)
        session = AgentSession(research_goal="Summarize FAA UAS rulemaking smoke-test evidence")
        session.add_evidence(
            url="https://www.faa.gov/uas/advanced_operations",
            title="FAA Advanced UAS Operations",
            claims=["The FAA publishes guidance and updates for advanced UAS operations."],
            credibility_score=0.9,
        )
        synthesizer = ReportSynthesizer(settings)

        report = await synthesizer.synthesize(session)

        self.assertIn("https://www.faa.gov/uas/advanced_operations", report.sources_used)
        self.assertTrue(report.key_findings)
        self.assertTrue(
            all(
                source_url in {"https://www.faa.gov/uas/advanced_operations"}
                for finding in report.key_findings
                for source_url in finding.source_urls
            )
        )


class LiveCloakBrowserSmokeTests(unittest.IsolatedAsyncioTestCase):
    def test_cloakbrowser_healthcheck_returns_ok(self) -> None:
        _skip_unless_live("CLOAK_CDP_URL")
        settings = Settings.from_env(os.environ)
        health = CloakBrowserClient(settings).healthcheck(timeout=5.0)
        if health.status != "ok":
            self.skipTest(f"CloakBrowser is unreachable from this environment: {health.detail}")

        self.assertEqual("ok", health.status, health.to_dict())
        self.assertTrue(health.websocket_debugger_url)

    async def test_cloakbrowser_can_navigate_to_example_dot_com(self) -> None:
        _skip_unless_live("CLOAK_CDP_URL")
        settings = Settings.from_env(os.environ)
        health = CloakBrowserClient(settings).healthcheck(timeout=5.0)
        if health.status != "ok":
            self.skipTest(f"CloakBrowser is unreachable from this environment: {health.detail}")

        result = await navigate_to_url(settings, url="https://example.com", timeout_seconds=15.0)

        self.assertEqual("https://example.com", result.url)
        self.assertIn("Example", result.title)
        self.assertGreaterEqual(result.status_code, 200)
        self.assertLess(result.status_code, 400)
        self.assertFalse(result.detection_blocked, result.blocked_reason)


if __name__ == "__main__":
    unittest.main()
