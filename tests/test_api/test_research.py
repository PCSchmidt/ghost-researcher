"""Regression tests for the POST /research endpoint."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, ToolCall
from backend.jobs.research import PlannerSequenceResult
from backend.main import create_app
from backend.persistence import InMemoryResearchRepository
from backend.synthesizer.schema import ResearchReport, ReportClaim


class FakeResearchOrchestrator:
    def __init__(self, result: PlannerSequenceResult) -> None:
        self.result = result
        self.received_goal: str | None = None

    async def run_sequence(self, research_goal: str) -> PlannerSequenceResult:
        self.received_goal = research_goal
        return self.result


class ResearchRouteTests(unittest.TestCase):
    def test_research_route_returns_tool_result_and_session_state(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        session.increment_step()
        session.register_source("https://example.com/report")
        session.finalize("sufficient_coverage")
        result = PlannerSequenceResult(
            session=session,
            decisions=[PlannerDecision(
                tool_call=ToolCall(
                    name="navigate_to_url",
                    arguments={"url": "https://example.com/report"},
                )
            )],
            tool_results=[
                {
                    "url": "https://example.com/report",
                    "final_url": "https://example.com/report",
                    "title": "Example Report",
                }
            ],
        )
        orchestrator = FakeResearchOrchestrator(result)
        client = TestClient(create_app({}, research_orchestrator=orchestrator))

        response = client.post("/research", json={"research_goal": " Review https://example.com/report "})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("completed", payload["status"])
        self.assertEqual("navigate_to_url", payload["decisions"][0]["tool_call"]["name"])
        self.assertIn("job_id", payload)
        self.assertIn("created_at", payload)
        self.assertIn("updated_at", payload)
        self.assertEqual(
            ["job_started", "tool_started", "tool_completed", "job_completed"],
            [event["event_type"] for event in payload["status_events"]],
        )
        self.assertEqual("https://example.com/report", payload["tool_results"][0]["final_url"])
        self.assertEqual(["https://example.com/report"], payload["session"]["sources_visited"])
        self.assertEqual([], payload["session"]["source_candidates"])
        self.assertIsNone(payload["synthesis"])
        self.assertEqual("Review https://example.com/report", orchestrator.received_goal)

    def test_research_route_persists_and_fetches_job_by_id(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        result = PlannerSequenceResult(
            session=session,
            decisions=[PlannerDecision(tool_call=None, termination_reason="no_new_sources")],
            tool_results=[],
        )
        repository = InMemoryResearchRepository()
        client = TestClient(
            create_app(
                {},
                research_orchestrator=FakeResearchOrchestrator(result),
                research_repository=repository,
            )
        )

        create_response = client.post("/research", json={"research_goal": "Review https://example.com/report"})
        job_id = create_response.json()["job_id"]
        get_response = client.get(f"/research/{job_id}")

        self.assertEqual(200, get_response.status_code)
        self.assertEqual(job_id, get_response.json()["job_id"])
        self.assertEqual("Review https://example.com/report", get_response.json()["session"]["research_goal"])

    def test_research_route_streams_persisted_status_events(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        session.finalize("sufficient_coverage")
        result = PlannerSequenceResult(
            session=session,
            decisions=[
                PlannerDecision(
                    tool_call=ToolCall(
                        name="navigate_to_url",
                        arguments={"url": "https://example.com/report"},
                    )
                )
            ],
            tool_results=[{"final_url": "https://example.com/report"}],
        )
        repository = InMemoryResearchRepository()
        client = TestClient(
            create_app(
                {},
                research_orchestrator=FakeResearchOrchestrator(result),
                research_repository=repository,
            )
        )

        create_response = client.post("/research", json={"research_goal": "Review https://example.com/report"})
        job_id = create_response.json()["job_id"]
        stream_response = client.get(f"/research/{job_id}/events")

        self.assertEqual(200, stream_response.status_code)
        self.assertEqual("text/event-stream; charset=utf-8", stream_response.headers["content-type"])
        body = stream_response.text
        self.assertIn("event: job_started", body)
        self.assertIn("event: tool_started", body)
        self.assertIn("event: tool_completed", body)
        self.assertIn("event: job_completed", body)
        self.assertIn('"tool_name": "navigate_to_url"', body)

    def test_research_route_returns_404_for_missing_event_stream(self) -> None:
        client = TestClient(create_app({}))

        response = client.get("/research/missing-job/events")

        self.assertEqual(404, response.status_code)

    def test_research_route_returns_404_for_missing_job(self) -> None:
        client = TestClient(create_app({}))

        response = client.get("/research/missing-job")

        self.assertEqual(404, response.status_code)

    def test_research_route_serializes_synthesis_when_available(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        session.register_source("https://example.com/report")
        session.finalize("sufficient_coverage")
        result = PlannerSequenceResult(
            session=session,
            decisions=[PlannerDecision(tool_call=None, termination_reason="sufficient_coverage")],
            tool_results=[],
            synthesis=ResearchReport(
                title="Example synthesis",
                summary="Example report summary",
                key_findings=[ReportClaim(text="Example claim", source_urls=["https://example.com/report"])],
                sources_used=["https://example.com/report"],
                confidence=0.8,
            ),
        )
        client = TestClient(create_app({}, research_orchestrator=FakeResearchOrchestrator(result)))

        response = client.post("/research", json={"research_goal": "Review https://example.com/report"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("Example synthesis", payload["synthesis"]["title"])
        self.assertEqual("Example claim", payload["synthesis"]["key_findings"][0]["text"])

    def test_research_route_returns_safe_stop_without_tool_result(self) -> None:
        session = AgentSession(research_goal="Find FAA BVLOS guidance")
        session.finalize("no_new_sources")
        result = PlannerSequenceResult(
            session=session,
            decisions=[PlannerDecision(tool_call=None, termination_reason="no_new_sources")],
            tool_results=[],
        )
        client = TestClient(create_app({}, research_orchestrator=FakeResearchOrchestrator(result)))

        response = client.post("/research", json={"research_goal": "Find FAA BVLOS guidance"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("stopped", payload["status"])
        self.assertTrue(payload["decisions"][0]["should_stop"])
        self.assertIsNone(payload["decisions"][0]["tool_call"])
        self.assertEqual("no_new_sources", payload["session"]["termination_reason"])
        self.assertEqual([], payload["tool_results"])

    def test_research_route_rejects_blank_goal(self) -> None:
        client = TestClient(create_app({}))

        response = client.post("/research", json={"research_goal": "   "})

        self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
