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


if __name__ == "__main__":
    unittest.main()
