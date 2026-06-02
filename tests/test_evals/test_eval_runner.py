"""Tests for the GhostResearcher eval harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.agent.memory import AgentSession
from backend.jobs.research import PlannerSequenceResult
from backend.synthesizer.schema import ResearchReport, ReportClaim
from evals.eval_runner import BenchmarkPrompt, load_benchmark_prompts, run_eval_suite, score_prompt, write_eval_results


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
        self.assertEqual("deterministic_offline", payload["mode"])
        self.assertEqual("test", payload["cases"][0]["id"])
        self.assertIn("source_count_below_benchmark_minimum", payload["cases"][0]["limitations"])

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
        max_steps=4,
        eval_criteria={
            "must_include": ["deadline", "affected operations"],
            "must_not_hallucinate": ["dates"],
            "freshness_required": True,
        },
        notes="test prompt",
    )


if __name__ == "__main__":
    unittest.main()