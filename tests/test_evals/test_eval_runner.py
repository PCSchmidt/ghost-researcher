"""Tests for the GhostResearcher eval harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.agent.memory import AgentSession
from backend.config import Settings
from backend.executor.browser import BrowserHealth
from backend.jobs.research import PlannerSequenceResult
from backend.synthesizer.schema import ResearchReport, ReportClaim
from evals.eval_runner import (
    BenchmarkPrompt,
    _breadth_score,
    load_benchmark_prompts,
    run_eval_suite,
    score_prompt,
    validate_live_environment,
    write_eval_results,
)


class EvalRunnerTests(unittest.IsolatedAsyncioTestCase):
    def test_load_benchmark_prompts_reads_seed_file(self) -> None:
        prompts = load_benchmark_prompts()

        self.assertEqual(10, len(prompts))
        self.assertEqual("bp_001", prompts[0].id)
        self.assertGreaterEqual(prompts[0].min_sources, 1)

    def test_score_prompt_rewards_source_traceability(self) -> None:
        prompt = _prompt()
        session = AgentSession(research_goal=prompt.prompt)
        session.add_evidence(
            url="https://faa.gov/ghostresearcher-eval/test",
            title="FAA source",
            claims=["Evidence includes deadline and affected operations with recent 2026 context."],
            credibility_score=0.9,
        )
        session.register_source("https://faa.gov/ghostresearcher-eval/test")
        session.finalize("sufficient_coverage")
        result = PlannerSequenceResult(
            session=session,
            decisions=[],
            tool_results=[],
            synthesis=ResearchReport(
                title="FAA report",
                summary="Evidence includes deadline and affected operations with recent 2026 context.",
                key_findings=[
                    ReportClaim(
                        text="Evidence includes deadline and affected operations with recent 2026 context.",
                        source_urls=["https://faa.gov/ghostresearcher-eval/test"],
                    )
                ],
                sources_used=["https://faa.gov/ghostresearcher-eval/test"],
                confidence=0.9,
            ),
        )

        scored = score_prompt(prompt, result)

        self.assertEqual(1.0, scored["metrics"]["source_trace_score"])
        self.assertEqual(["faa.gov"], scored["metrics"]["expected_source_matches"])
        self.assertGreater(scored["score"], 0.7)

    async def test_run_eval_suite_produces_cases_and_average(self) -> None:
        payload = await run_eval_suite(prompts=[_prompt()])

        self.assertEqual(1, payload["benchmark_count"])
        self.assertEqual("offline", payload["mode"])
        self.assertEqual("deterministic", payload["search_provider"])
        self.assertEqual("test", payload["cases"][0]["id"])
        self.assertEqual(2, payload["cases"][0]["metrics"]["source_count"])
        tool_sequence = payload["cases"][0]["metrics"]["tool_sequence"]
        self.assertIn("extract_structured_data", tool_sequence)
        self.assertIn("assess_credibility", tool_sequence)
        self.assertEqual("finalize_report", tool_sequence[-1])
        self.assertNotIn("source_count_below_benchmark_minimum", payload["cases"][0]["limitations"])

    async def test_offline_suite_is_a_regression_harness_not_a_quality_score(self) -> None:
        # Offline is labeled a regression harness: a healthy deterministic run keeps
        # integrity at 1.0 (the pipeline works), but the quality score must stay
        # below 1.0 — meeting the benchmark floor is adequate, not excellent. This is
        # the property that the old flat-1.0 scorer lacked.
        payload = await run_eval_suite(prompts=[_prompt()])

        self.assertEqual("regression", payload["harness_kind"])
        self.assertEqual(1.0, payload["average_integrity_score"])
        self.assertLess(payload["average_quality_score"], 1.0)
        self.assertGreater(payload["average_quality_score"], 0.5)

    def test_score_drops_when_evidence_pipeline_regresses(self) -> None:
        # A run that navigated sources but never produced extracted/assessed evidence
        # or a report (the exact failure the evidence-flow refactor risked) must score
        # far below a healthy run. The eval has to be able to fail.
        prompt = _prompt()
        degraded_session = AgentSession(research_goal=prompt.prompt)
        for source_url in [
            "https://faa.gov/ghostresearcher-eval/test",
            "https://federalregister.gov/ghostresearcher-eval/test",
        ]:
            degraded_session.register_source(source_url)
            degraded_session.add_evidence(
                url=source_url,
                title=source_url,
                claims=["shallow navigation teaser without the required facts"],
                credibility_score=0.5,
                evidence_type="navigation_fallback",
            )
        degraded_session.finalize("max_steps")
        degraded = score_prompt(
            prompt,
            PlannerSequenceResult(session=degraded_session, decisions=[], tool_results=[], synthesis=None),
        )

        self.assertLess(degraded["integrity_score"], 1.0)
        self.assertEqual(0.0, degraded["metrics"]["source_trace_score"])
        self.assertEqual(0.0, degraded["metrics"]["mean_credibility_score"])
        self.assertLess(degraded["score"], 0.5)

    def test_breadth_score_rewards_corroboration_beyond_the_minimum(self) -> None:
        self.assertEqual(0.7, _breadth_score(2, 2))
        self.assertEqual(0.85, _breadth_score(3, 2))
        self.assertEqual(1.0, _breadth_score(4, 2))
        self.assertLess(_breadth_score(1, 2), 0.7)

    async def test_live_eval_requires_non_deterministic_search_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "live_search_provider_required"):
            await run_eval_suite(prompts=[_prompt()], mode="live", settings=Settings.from_env({}))

    async def test_live_eval_can_use_injected_orchestrator(self) -> None:
        class FakeLiveOrchestrator:
            def __init__(self, settings: Settings) -> None:
                self.settings = settings

            async def run_sequence(self, research_goal: str, **kwargs: object) -> PlannerSequenceResult:
                session = AgentSession(research_goal=research_goal)
                for source_url in [
                    "https://faa.gov/ghostresearcher-eval/test",
                    "https://federalregister.gov/ghostresearcher-eval/test",
                ]:
                    session.register_source(source_url)
                    session.add_evidence(
                        url=source_url,
                        title=source_url,
                        claims=["Evidence includes deadline and affected operations with recent 2026 context."],
                        credibility_score=0.9,
                    )
                session.finalize("sufficient_coverage")
                return PlannerSequenceResult(
                    session=session,
                    decisions=[],
                    tool_results=[],
                    synthesis=ResearchReport(
                        title="Live report",
                        summary="Evidence includes deadline and affected operations with recent 2026 context.",
                        key_findings=[
                            ReportClaim(
                                text="Evidence includes deadline and affected operations with recent 2026 context.",
                                source_urls=["https://faa.gov/ghostresearcher-eval/test"],
                            )
                        ],
                        sources_used=[
                            "https://faa.gov/ghostresearcher-eval/test",
                            "https://federalregister.gov/ghostresearcher-eval/test",
                        ],
                        confidence=0.9,
                    ),
                )

        payload = await run_eval_suite(
            prompts=[_prompt()],
            mode="live",
            settings=Settings.from_env(
                {
                    "SEARCH_PROVIDER": "brave",
                    "SEARCH_API_KEY": "test-key",
                    "OPENROUTER_API_KEY": "test-openrouter",
                    "CLOAK_CDP_URL": "http://cloakbrowser:9222",
                }
            ),
            orchestrator_factory=FakeLiveOrchestrator,
            browser_healthcheck=lambda settings: BrowserHealth(
                status="ok",
                version_url="http://cloakbrowser:9222/json/version",
                browser="CloakBrowser/1.0",
                websocket_debugger_url="ws://cloakbrowser:9222/devtools/browser/abc",
            ),
        )

        self.assertEqual("live", payload["mode"])
        self.assertEqual("quality", payload["harness_kind"])
        self.assertEqual("brave", payload["search_provider"])
        self.assertEqual(2, payload["cases"][0]["metrics"]["source_count"])
        self.assertEqual("ok", payload["live_environment"]["cloakbrowser"]["status"])

    def test_validate_live_environment_requires_live_settings(self) -> None:
        with self.assertRaisesRegex(ValueError, "live_environment_missing"):
            validate_live_environment(Settings.from_env({}))

    def test_validate_live_environment_rejects_unhealthy_cloakbrowser(self) -> None:
        def fake_healthcheck(settings: Settings) -> BrowserHealth:
            return BrowserHealth(
                status="unreachable",
                version_url="http://cloakbrowser:9222/json/version",
                detail="connection refused",
            )

        settings = Settings.from_env(
            {
                "SEARCH_PROVIDER": "brave",
                "SEARCH_API_KEY": "test-key",
                "OPENROUTER_API_KEY": "test-openrouter",
                "CLOAK_CDP_URL": "http://cloakbrowser:9222",
            }
        )

        with self.assertRaisesRegex(ValueError, "live_cloakbrowser_unreachable:connection refused"):
            validate_live_environment(settings, browser_healthcheck=fake_healthcheck)

    def test_write_eval_results_creates_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = write_eval_results({"average_score": 0.5, "cases": []}, results_dir=Path(tmp_dir))

            self.assertTrue(path.exists())
            self.assertEqual(".json", path.suffix)
            self.assertIn("eval_results_", path.name)


def _prompt() -> BenchmarkPrompt:
    return BenchmarkPrompt(
        id="test",
        prompt="What are current FAA UAS deadlines?",
        domain="aviation_regulatory",
        expected_source_types=["gov"],
        expected_sources=["faa.gov", "federalregister.gov"],
        min_sources=2,
        max_steps=8,
        eval_criteria={
            "must_include": ["deadline", "affected operations"],
            "must_not_hallucinate": ["dates"],
            "freshness_required": True,
        },
        notes="test prompt",
    )


if __name__ == "__main__":
    unittest.main()
