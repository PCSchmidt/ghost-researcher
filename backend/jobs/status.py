"""Research job status event helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from backend.agent.planner import PlannerDecision
from backend.jobs.research import PlannerSequenceResult


@dataclass(frozen=True, slots=True)
class JobStatusEvent:
    """Frontend-facing status event for a research job."""

    sequence: int
    event_type: str
    status: str
    message: str
    tool_name: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "tool_name": self.tool_name,
            "payload": self.payload,
        }


def build_status_events(result: PlannerSequenceResult) -> list[dict[str, Any]]:
    """Build ordered status events from a completed planner sequence."""
    events: list[JobStatusEvent] = [
        JobStatusEvent(
            sequence=0,
            event_type="job_started",
            status="active",
            message="Research job accepted",
            payload={"research_goal": result.session.research_goal},
        )
    ]
    sequence = 1
    tool_results = iter(result.tool_results)

    for decision in result.decisions:
        if decision.tool_call is None:
            events.append(_planner_stop_event(sequence, decision))
            sequence += 1
            continue

        tool_name = decision.tool_call.name
        events.append(
            JobStatusEvent(
                sequence=sequence,
                event_type="tool_started",
                status="active",
                message=f"Started {tool_name}",
                tool_name=tool_name,
                payload={"arguments": decision.tool_call.arguments},
            )
        )
        sequence += 1

        tool_result = next(tool_results, None)
        if tool_result is not None:
            events.append(
                JobStatusEvent(
                    sequence=sequence,
                    event_type="tool_completed",
                    status="completed",
                    message=f"Completed {tool_name}",
                    tool_name=tool_name,
                    payload={"result": tool_result},
                )
            )
            sequence += 1

    if result.synthesis is not None:
        events.append(
            JobStatusEvent(
                sequence=sequence,
                event_type="synthesis_completed",
                status="completed",
                message="Synthesized research report",
                payload={"title": result.synthesis.title, "confidence": result.synthesis.confidence},
            )
        )
        sequence += 1

    events.append(
        JobStatusEvent(
            sequence=sequence,
            event_type="job_completed",
            status=result.session.termination_state,
            message="Research job finished",
            payload={
                "termination_reason": result.session.termination_reason,
                "evidence_quality": result.session.evidence_quality_metrics(),
            },
        )
    )
    return [event.to_dict() for event in events]


def encode_sse_event(event: dict[str, Any]) -> str:
    """Encode one status event using the Server-Sent Events wire format."""
    event_name = str(event.get("event_type", "message"))
    event_id = str(event.get("sequence", ""))
    event_data = json.dumps(event, sort_keys=True)
    return f"id: {event_id}\nevent: {event_name}\ndata: {event_data}\n\n"


def _planner_stop_event(sequence: int, decision: PlannerDecision) -> JobStatusEvent:
    reason = decision.termination_reason or "no_tool_call"
    return JobStatusEvent(
        sequence=sequence,
        event_type="planner_stopped",
        status="stopped",
        message="Planner stopped without a tool call",
        payload={"termination_reason": reason, "should_stop": decision.should_stop},
    )


__all__ = ["JobStatusEvent", "build_status_events", "encode_sse_event"]
