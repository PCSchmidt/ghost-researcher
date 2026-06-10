"""Regression tests for the async POST /research lifecycle.

POST enqueues a job and returns a "running" record immediately; the job runs
detached and the client polls GET /research/{job_id} for the terminal result.
"""

from __future__ import annotations

import asyncio
import unittest

from httpx import ASGITransport, AsyncClient

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, ToolCall
from backend.jobs.research import PlannerSequenceResult
from backend.main import create_app
from backend.persistence import InMemoryResearchRepository
from backend.synthesizer.schema import ReportClaim, ResearchReport


class FakeResearchOrchestrator:
    def __init__(self, result: PlannerSequenceResult) -> None:
        self.result = result
        self.received_goal: str | None = None

    async def run_sequence(self, research_goal: str) -> PlannerSequenceResult:
        self.received_goal = research_goal
        return self.result


class RaisingResearchOrchestrator:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def run_sequence(self, research_goal: str) -> PlannerSequenceResult:
        raise self.error


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _wait_for_terminal(client: AsyncClient, job_id: str, *, timeout: float = 2.0) -> dict:
    """Poll the job until it leaves the 'running' state (or timeout)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        response = await client.get(f"/research/{job_id}")
        payload = response.json()
        if payload.get("status") != "running":
            return payload
        if asyncio.get_event_loop().time() >= deadline:
            return payload
        await asyncio.sleep(0.01)


class ResearchRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_returns_running_record_immediately(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        result = PlannerSequenceResult(session=session, decisions=[], tool_results=[])
        app = create_app({}, research_orchestrator=FakeResearchOrchestrator(result))

        async with _client(app) as client:
            response = await client.post("/research", json={"research_goal": " Review https://example.com/report "})
            payload = response.json()

            self.assertEqual(200, response.status_code)
            self.assertEqual("running", payload["status"])
            self.assertIn("job_id", payload)
            self.assertIsNone(payload["synthesis"])
            self.assertEqual(
                ["job_started"],
                [event["event_type"] for event in payload["status_events"]],
            )
            self.assertEqual("Review https://example.com/report", payload["session"]["research_goal"])

    async def test_job_completes_with_tool_results_and_session_state(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        session.increment_step()
        session.register_source("https://example.com/report")
        session.finalize("sufficient_coverage")
        result = PlannerSequenceResult(
            session=session,
            decisions=[
                PlannerDecision(
                    tool_call=ToolCall(name="navigate_to_url", arguments={"url": "https://example.com/report"})
                )
            ],
            tool_results=[
                {"url": "https://example.com/report", "final_url": "https://example.com/report", "title": "Example Report"}
            ],
        )
        orchestrator = FakeResearchOrchestrator(result)
        app = create_app({}, research_orchestrator=orchestrator)

        async with _client(app) as client:
            created = await client.post("/research", json={"research_goal": " Review https://example.com/report "})
            job_id = created.json()["job_id"]
            payload = await _wait_for_terminal(client, job_id)

            self.assertEqual("completed", payload["status"])
            self.assertEqual("navigate_to_url", payload["decisions"][0]["tool_call"]["name"])
            self.assertEqual(
                ["job_started", "tool_started", "tool_completed", "job_completed"],
                [event["event_type"] for event in payload["status_events"]],
            )
            self.assertEqual("https://example.com/report", payload["tool_results"][0]["final_url"])
            self.assertEqual(["https://example.com/report"], payload["session"]["sources_visited"])
            self.assertIsNone(payload["synthesis"])
            self.assertEqual("Review https://example.com/report", orchestrator.received_goal)

    async def test_job_serializes_synthesis_when_available(self) -> None:
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
        app = create_app({}, research_orchestrator=FakeResearchOrchestrator(result))

        async with _client(app) as client:
            created = await client.post("/research", json={"research_goal": "Review https://example.com/report"})
            payload = await _wait_for_terminal(client, created.json()["job_id"])

            self.assertEqual("Example synthesis", payload["synthesis"]["title"])
            self.assertEqual("Example claim", payload["synthesis"]["key_findings"][0]["text"])

    async def test_job_returns_safe_stop_without_tool_result(self) -> None:
        session = AgentSession(research_goal="Find FAA BVLOS guidance")
        session.finalize("no_new_sources")
        result = PlannerSequenceResult(
            session=session,
            decisions=[PlannerDecision(tool_call=None, termination_reason="no_new_sources")],
            tool_results=[],
        )
        app = create_app({}, research_orchestrator=FakeResearchOrchestrator(result))

        async with _client(app) as client:
            created = await client.post("/research", json={"research_goal": "Find FAA BVLOS guidance"})
            payload = await _wait_for_terminal(client, created.json()["job_id"])

            self.assertEqual("stopped", payload["status"])
            self.assertTrue(payload["decisions"][0]["should_stop"])
            self.assertIsNone(payload["decisions"][0]["tool_call"])
            self.assertEqual("no_new_sources", payload["session"]["termination_reason"])

    async def test_job_records_error_when_run_sequence_raises(self) -> None:
        # A background failure must be persisted as a terminal "error" job, never
        # crash the worker or leave the job stuck "running".
        app = create_app(
            {},
            research_orchestrator=RaisingResearchOrchestrator(RuntimeError("connect_over_cdp boom")),
        )

        async with _client(app) as client:
            created = await client.post("/research", json={"research_goal": "Find FAA BVLOS guidance"})
            payload = await _wait_for_terminal(client, created.json()["job_id"])

            self.assertEqual("error", payload["status"])
            self.assertIn("connect_over_cdp boom", payload["error"])
            self.assertIsNone(payload["synthesis"])
            self.assertEqual("error", payload["session"]["termination_reason"])

    async def test_completed_job_streams_persisted_status_events(self) -> None:
        session = AgentSession(research_goal="Review https://example.com/report")
        session.finalize("sufficient_coverage")
        result = PlannerSequenceResult(
            session=session,
            decisions=[
                PlannerDecision(
                    tool_call=ToolCall(name="navigate_to_url", arguments={"url": "https://example.com/report"})
                )
            ],
            tool_results=[{"final_url": "https://example.com/report"}],
        )
        repository = InMemoryResearchRepository()
        app = create_app({}, research_orchestrator=FakeResearchOrchestrator(result), research_repository=repository)

        async with _client(app) as client:
            created = await client.post("/research", json={"research_goal": "Review https://example.com/report"})
            job_id = created.json()["job_id"]
            await _wait_for_terminal(client, job_id)
            stream_response = await client.get(f"/research/{job_id}/events")

            self.assertEqual(200, stream_response.status_code)
            body = stream_response.text
            self.assertIn("event: job_started", body)
            self.assertIn("event: tool_started", body)
            self.assertIn("event: tool_completed", body)
            self.assertIn("event: job_completed", body)

    async def test_post_rejects_blank_goal(self) -> None:
        app = create_app({})
        async with _client(app) as client:
            response = await client.post("/research", json={"research_goal": "   "})
            self.assertEqual(422, response.status_code)

    async def test_get_returns_404_for_missing_job(self) -> None:
        app = create_app({})
        async with _client(app) as client:
            response = await client.get("/research/missing-job")
            self.assertEqual(404, response.status_code)

    async def test_get_returns_404_for_missing_event_stream(self) -> None:
        app = create_app({})
        async with _client(app) as client:
            response = await client.get("/research/missing-job/events")
            self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
