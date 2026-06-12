"""Regression tests for report synthesis."""

from __future__ import annotations

import json
import unittest
from typing import Any

from backend.agent.memory import AgentSession
from backend.config import Settings
from backend.synthesizer.report import ReportSynthesizer, SynthesisError


def _session_with_evidence() -> AgentSession:
    session = AgentSession(research_goal="Assess FAA BVLOS guidance")
    session.add_evidence(
        url="https://faa.gov/bvlos",
        title="FAA BVLOS guidance",
        claims=["FAA is evaluating BVLOS pathways."],
        credibility_score=0.91,
    )
    return session


class ReportSynthesizerTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_synthesis_uses_session_evidence(self) -> None:
        session = _session_with_evidence()
        synthesizer = ReportSynthesizer(Settings.from_env({}))

        report = await synthesizer.synthesize(session)

        self.assertEqual("Research Report: Assess FAA BVLOS guidance", report.title)
        self.assertEqual(["https://faa.gov/bvlos"], report.sources_used)
        self.assertEqual("FAA is evaluating BVLOS pathways.", report.key_findings[0].text)
        self.assertEqual(["https://faa.gov/bvlos"], report.key_findings[0].source_urls)
        self.assertEqual(0.91, report.confidence)

    async def test_model_synthesis_parses_json_and_records_usage(self) -> None:
        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "FAA BVLOS Report",
                                    "summary": "FAA is evaluating BVLOS pathways.",
                                    "key_findings": [
                                        {
                                            "text": "FAA is evaluating BVLOS pathways.",
                                            "source_urls": ["https://faa.gov/bvlos"],
                                        }
                                    ],
                                    "sources_used": ["https://faa.gov/bvlos"],
                                    "confidence": 0.88,
                                    "limitations": ["single source"],
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 200, "completion_tokens": 80, "cost": 0.002},
            }

        session = _session_with_evidence()
        synthesizer = ReportSynthesizer(Settings.from_env({}), transport=fake_transport)

        report = await synthesizer.synthesize(session)

        self.assertEqual("FAA BVLOS Report", report.title)
        self.assertEqual(280, session.running_tokens)
        self.assertEqual(0.002, session.running_cost_usd)

    async def test_model_synthesis_rejects_unsupported_claim_source(self) -> None:
        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "Unsupported",
                                    "summary": "Unsupported source.",
                                    "key_findings": [
                                        {"text": "Unsupported claim", "source_urls": ["https://example.com"]}
                                    ],
                                    "sources_used": ["https://example.com"],
                                    "confidence": 0.5,
                                    "limitations": [],
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            }

        synthesizer = ReportSynthesizer(Settings.from_env({}), transport=fake_transport)

        with self.assertRaisesRegex(ValueError, "unsupported_source"):
            await synthesizer.synthesize(_session_with_evidence())

    async def test_synthesis_rejects_missing_evidence(self) -> None:
        synthesizer = ReportSynthesizer(Settings.from_env({}))

        with self.assertRaisesRegex(SynthesisError, "no_evidence_records"):
            await synthesizer.synthesize(AgentSession(research_goal="No evidence"))

    async def test_synthesis_degrades_to_deterministic_when_token_budget_spent(self) -> None:
        # The research loop can exhaust the shared token budget before synthesis runs.
        # A run that gathered evidence must still return a report (deterministic, no
        # tokens), not None — and must not call the model when already over budget.
        session = _session_with_evidence()
        session.record_model_usage(prompt_tokens=200_000, completion_tokens=0, cost_usd=0.0)
        called = False

        async def fake_transport(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal called
            called = True
            return {"choices": [{"message": {"content": "{}"}}], "usage": {}}

        synthesizer = ReportSynthesizer(Settings.from_env({}), transport=fake_transport)

        with self.assertLogs("ghostresearcher.synthesis", level="WARNING") as captured:
            report = await synthesizer.synthesize(session)

        self.assertFalse(called)  # over budget -> no model call
        self.assertIsNotNone(report)
        self.assertEqual(["https://faa.gov/bvlos"], report.sources_used)
        # The silent over-budget skip now leaves a trace so a deterministic
        # report is diagnosable from the logs.
        self.assertTrue(any("over_budget" in line for line in captured.output))


def _two_source_session() -> AgentSession:
    session = AgentSession(research_goal="Assess data center energy efficiency in 2025")
    session.add_evidence(
        url="https://a.gov/x",
        title="Cooling study",
        claims=["Direct-to-chip cooling lowers PUE substantially."],
        credibility_score=0.9,
    )
    session.add_evidence(
        url="https://b.org/y",
        title="Adoption report",
        claims=["Hyperscaler adoption is accelerating in 2025."],
        credibility_score=0.6,
    )
    return session


def _long_form_transport():
    async def transport(payload: dict[str, Any]) -> dict[str, Any]:
        system = payload["messages"][0]["content"]
        if "outline" in system:
            content = json.dumps(
                {
                    "title": "Data Center Energy Efficiency in 2025",
                    "sections": [
                        {"heading": "Cooling", "source_urls": ["https://a.gov/x"]},
                        {"heading": "Adoption", "source_urls": ["https://b.org/y"]},
                    ],
                }
            )
        elif "drafting ONE section" in system:
            content = json.dumps(
                {
                    "paragraphs": [
                        {
                            "text": "This paragraph is comfortably longer than the minimum length filter and is grounded in evidence.",
                            "citations": ["https://a.gov/x", "https://b.org/y"],
                        }
                    ]
                }
            )
        elif "abstract, conclusion" in system:
            content = json.dumps(
                {
                    "abstract": "This paper surveys data-center efficiency strategies in 2025.",
                    "conclusion": "Cooling and siting drive the largest efficiency gains.",
                    "key_findings": [
                        {"text": "Direct-to-chip cooling lowers PUE.", "source_urls": ["https://a.gov/x"]}
                    ],
                }
            )
        else:
            content = "{}"
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.001},
        }

    return transport


class LongFormSynthesizerTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_long_form_builds_structured_paper(self) -> None:
        settings = Settings.from_env({"LONGFORM_ENABLED": "true"})
        synthesizer = ReportSynthesizer(settings)

        report = await synthesizer.synthesize(_two_source_session())

        self.assertTrue(report.is_long_form)
        self.assertGreaterEqual(len(report.sections), 1)
        self.assertEqual(2, len(report.references))
        self.assertTrue(report.references[0].credibility_score >= report.references[1].credibility_score)
        self.assertTrue(report.abstract)
        self.assertTrue(report.key_findings)

    async def test_multi_pass_long_form_assembles_and_records_usage(self) -> None:
        settings = Settings.from_env({"LONGFORM_ENABLED": "true"})
        session = _two_source_session()
        synthesizer = ReportSynthesizer(settings, transport=_long_form_transport())

        report = await synthesizer.synthesize(session)

        self.assertTrue(report.is_long_form)
        self.assertEqual("Data Center Energy Efficiency in 2025", report.title)
        self.assertEqual(2, len(report.sections))
        self.assertEqual("This paper surveys data-center efficiency strategies in 2025.", report.abstract)
        self.assertTrue(report.conclusion)
        self.assertIn("https://a.gov/x", report.sources_used)
        self.assertIn("https://b.org/y", report.sources_used)
        # outline + 2 sections + framing = 4 calls, each cost 0.001
        self.assertAlmostEqual(0.004, session.running_cost_usd, places=6)
        self.assertEqual(600, session.running_tokens)

    async def test_long_form_degrades_to_deterministic_on_bad_outline(self) -> None:
        async def bad_outline_transport(payload: dict[str, Any]) -> dict[str, Any]:
            # Outline pass returns JSON with no usable sections -> long-form must
            # degrade to a deterministic structured build rather than failing.
            return {
                "choices": [{"message": {"content": json.dumps({"title": "x"})}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0005},
            }

        settings = Settings.from_env({"LONGFORM_ENABLED": "true"})
        synthesizer = ReportSynthesizer(settings, transport=bad_outline_transport)

        report = await synthesizer.synthesize(_two_source_session())

        self.assertTrue(report.is_long_form)  # deterministic fallback still produces sections
        self.assertTrue(report.references)


if __name__ == "__main__":
    unittest.main()
