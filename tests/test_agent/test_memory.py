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


if __name__ == "__main__":
    unittest.main()
