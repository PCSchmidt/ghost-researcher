"""Tests for research job status event helpers."""

from __future__ import annotations

import json
import unittest

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, ToolCall
from backend.jobs.research import PlannerSequenceResult
from backend.jobs.status import build_status_events, encode_sse_event


class JobStatusEventTests(unittest.TestCase):
    def test_build_status_events_records_tool_order(self) -> None:
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

        events = build_status_events(result)

        self.assertEqual(
            ["job_started", "tool_started", "tool_completed", "job_completed"],
            [event["event_type"] for event in events],
        )
        self.assertEqual([0, 1, 2, 3], [event["sequence"] for event in events])
        self.assertEqual("navigate_to_url", events[1]["tool_name"])
        self.assertEqual("sufficient_coverage", events[-1]["payload"]["termination_reason"])

    def test_build_status_events_records_planner_stop(self) -> None:
        session = AgentSession(research_goal="Find FAA guidance")
        session.finalize("no_new_sources")
        result = PlannerSequenceResult(
            session=session,
            decisions=[PlannerDecision(tool_call=None, termination_reason="no_new_sources")],
            tool_results=[],
        )

        events = build_status_events(result)

        self.assertEqual("planner_stopped", events[1]["event_type"])
        self.assertEqual("no_new_sources", events[1]["payload"]["termination_reason"])

    def test_encode_sse_event_uses_event_stream_wire_format(self) -> None:
        event = {
            "sequence": 7,
            "event_type": "tool_completed",
            "status": "completed",
            "message": "Completed web_search",
            "tool_name": "web_search",
            "payload": {"result": {"new_result_count": 1}},
        }

        encoded = encode_sse_event(event)

        self.assertTrue(encoded.startswith("id: 7\nevent: tool_completed\ndata: "))
        self.assertTrue(encoded.endswith("\n\n"))
        data_line = [line for line in encoded.splitlines() if line.startswith("data: ")][0]
        self.assertEqual(event, json.loads(data_line.removeprefix("data: ")))


if __name__ == "__main__":
    unittest.main()