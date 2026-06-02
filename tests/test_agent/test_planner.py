"""Regression tests for the deterministic planner skeleton."""

from __future__ import annotations

import unittest

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerSkeleton


class PlannerSkeletonTests(unittest.TestCase):
    def test_planner_emits_navigation_call_for_first_url(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Review this source: https://example.com/report")

        decision = planner.plan_next(session)

        self.assertIsNotNone(decision.tool_call)
        self.assertEqual("navigate_to_url", decision.tool_call.name)
        self.assertEqual({"url": "https://example.com/report"}, decision.tool_call.arguments)
        self.assertFalse(decision.should_stop)

    def test_planner_skips_visited_url_and_selects_next(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(
            research_goal="Compare https://example.com/old and https://example.com/new"
        )
        session.register_source("https://example.com/old")

        decision = planner.plan_next(session)

        self.assertIsNotNone(decision.tool_call)
        self.assertEqual({"url": "https://example.com/new"}, decision.tool_call.arguments)

    def test_planner_searches_when_no_url_exists(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Find recent FAA BVLOS guidance")

        decision = planner.plan_next(session)

        self.assertFalse(decision.should_stop)
        self.assertEqual("web_search", decision.tool_call.name)
        self.assertEqual("Find recent FAA BVLOS guidance", decision.tool_call.arguments["query"])

    def test_planner_stops_when_search_query_repeats_without_candidates(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Find recent FAA BVLOS guidance")
        session.record_search_query("Find recent FAA BVLOS guidance")

        decision = planner.plan_next(session)

        self.assertTrue(decision.should_stop)
        self.assertEqual("no_new_sources", decision.termination_reason)

    def test_planner_navigates_search_candidate_after_search(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Find recent FAA BVLOS guidance")
        session.add_source_candidates(["https://search.usa.gov/search?query=faa"])
        session.increment_step()

        decision = planner.plan_next(session)

        self.assertFalse(decision.should_stop)
        self.assertEqual("navigate_to_url", decision.tool_call.name)
        self.assertEqual("https://search.usa.gov/search?query=faa", decision.tool_call.arguments["url"])

    def test_planner_emits_extraction_after_navigation(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Review https://example.com/report")
        session.register_source("https://example.com/report")
        session.increment_step()

        decision = planner.plan_next(session)

        self.assertFalse(decision.should_stop)
        self.assertEqual("extract_structured_data", decision.tool_call.name)
        self.assertEqual("body", decision.tool_call.arguments["selector"])

    def test_planner_emits_credibility_after_extraction(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Review https://example.com/report")
        session.register_source("https://example.com/report")
        session.session_summary = "Latest FAA guidance from 2026"
        session.increment_step()
        session.increment_step()

        decision = planner.plan_next(session)

        self.assertFalse(decision.should_stop)
        self.assertEqual("assess_credibility", decision.tool_call.name)
        self.assertEqual("https://example.com/report", decision.tool_call.arguments["url"])
        self.assertEqual("Latest FAA guidance from 2026", decision.tool_call.arguments["content_snippet"])

    def test_planner_finalizes_after_minimum_evidence(self) -> None:
        planner = PlannerSkeleton()
        session = AgentSession(research_goal="Review https://example.com/report")
        session.add_evidence(
            url="https://example.com/report",
            title="Example Report",
            claims=["Example claim"],
            credibility_score=0.8,
        )

        decision = planner.plan_next(session)

        self.assertFalse(decision.should_stop)
        self.assertEqual("finalize_report", decision.tool_call.name)
        self.assertEqual("sufficient_coverage", decision.tool_call.arguments["termination_reason"])
        self.assertEqual(["https://example.com/report"], decision.tool_call.arguments["sources_used"])

    def test_planner_continues_to_next_candidate_before_minimum_evidence(self) -> None:
        planner = PlannerSkeleton(min_sources=2)
        session = AgentSession(research_goal="Find FAA BVLOS guidance")
        session.add_source_candidates(["https://faa.gov/one", "https://federalregister.gov/two"])
        session.register_source("https://faa.gov/one")
        session.add_evidence(
            url="https://faa.gov/one",
            title="FAA One",
            claims=["First claim"],
            credibility_score=0.8,
        )

        decision = planner.plan_next(session)

        self.assertEqual("navigate_to_url", decision.tool_call.name)
        self.assertEqual("https://federalregister.gov/two", decision.tool_call.arguments["url"])


if __name__ == "__main__":
    unittest.main()
