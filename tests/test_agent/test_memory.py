"""Regression tests for the AgentSession state model."""

from __future__ import annotations

import unittest

from backend.agent.memory import AgentSession


class AgentSessionTests(unittest.TestCase):
    def test_register_source_deduplicates_urls(self) -> None:
        session = AgentSession(research_goal="Track current FAA UAS rulemaking")

        self.assertTrue(session.register_source("https://faa.gov/example"))
        self.assertFalse(session.register_source("https://faa.gov/example"))
        self.assertEqual({"https://faa.gov/example"}, session.sources_visited)

    def test_increment_step_updates_budgets(self) -> None:
        session = AgentSession(research_goal="Summarize DoD UAS procurements")

        session.increment_step(tokens=1200, cost_usd=0.09)

        self.assertEqual(1, session.steps_taken)
        self.assertEqual(1, session.planner_turns)
        self.assertEqual(1200, session.running_tokens)
        self.assertAlmostEqual(0.09, session.running_cost_usd)

    def test_add_evidence_and_detection_event(self) -> None:
        session = AgentSession(research_goal="Assess BVLOS certification paths")

        session.add_evidence(
            url="https://faa.gov/bvlos",
            title="BVLOS guidance",
            claims=["FAA is evaluating BVLOS pathways"],
            credibility_score=0.93,
        )
        session.add_detection_event(url="https://example.com/paywall", reason="bot challenge")

        self.assertEqual(1, len(session.evidence_records))
        self.assertEqual("BVLOS guidance", session.evidence_records[0].title)
        self.assertEqual(1, len(session.detection_events))
        self.assertEqual("bot challenge", session.detection_events[0].reason)

    def test_can_continue_and_finalize(self) -> None:
        session = AgentSession(research_goal="Review RL swarm papers")
        session.increment_step(tokens=500)

        self.assertTrue(session.can_continue(max_steps=5, max_tokens=1000))

        session.finalize("sufficient_coverage")

        self.assertFalse(session.can_continue(max_steps=5, max_tokens=1000))
        self.assertEqual("finalized", session.termination_state)
        self.assertEqual("sufficient_coverage", session.termination_reason)

    def test_evidence_quality_metrics_counts_provenance(self) -> None:
        session = AgentSession(research_goal="Assess evidence quality")
        session.register_source("https://faa.gov/one")
        session.register_source("https://example.com/two")
        session.add_evidence(
            url="https://faa.gov/one",
            title="FAA",
            claims=["Assessed claim"],
            credibility_score=0.9,
            evidence_type="assessed",
        )
        session.add_evidence(
            url="https://example.com/two",
            title="Example",
            claims=["Extracted claim"],
            credibility_score=0.5,
            evidence_type="extracted",
        )
        session.add_evidence(
            url="https://example.com/two",
            title="Example",
            claims=["Fallback claim"],
            credibility_score=0.5,
            evidence_type="navigation_fallback",
        )
        session.add_detection_event(url="https://blocked.example", reason="bot_challenge")

        metrics = session.evidence_quality_metrics()

        self.assertEqual(2, metrics["sources_visited_count"])
        self.assertEqual(1, metrics["assessed_evidence_count"])
        self.assertEqual(1, metrics["extracted_evidence_count"])
        self.assertEqual(1, metrics["navigation_fallback_evidence_count"])
        self.assertEqual(0.9, metrics["average_assessed_credibility"])
        self.assertEqual(1, metrics["detection_event_count"])


if __name__ == "__main__":
    unittest.main()
