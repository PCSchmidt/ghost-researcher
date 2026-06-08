"""Research job endpoints for GhostResearcher."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, ToolCall
from backend.config import Settings
from backend.jobs.research import PlannerRunResult, PlannerSequenceResult, ResearchOrchestrator
from backend.jobs.status import build_status_events, encode_sse_event
from backend.persistence import InMemoryResearchRepository, ResearchRepository
from backend.synthesizer.schema import ResearchReport


class ResearchOrchestratorLike(Protocol):
    async def run_sequence(self, research_goal: str, **kwargs: Any) -> PlannerSequenceResult: ...


class ResearchRequest(BaseModel):
    research_goal: str = Field(..., min_length=1, max_length=4000)


def _serialize_tool_call(tool_call: ToolCall | None) -> dict[str, Any] | None:
    if tool_call is None:
        return None
    return {"name": tool_call.name, "arguments": tool_call.arguments}


def _serialize_decision(decision: PlannerDecision) -> dict[str, Any]:
    return {
        "tool_call": _serialize_tool_call(decision.tool_call),
        "termination_reason": decision.termination_reason,
        "should_stop": decision.should_stop,
    }


def _serialize_session(session: AgentSession) -> dict[str, Any]:
    return {
        "research_goal": session.research_goal,
        "steps_taken": session.steps_taken,
        "planner_turns": session.planner_turns,
        "running_tokens": session.running_tokens,
        "running_cost_usd": session.running_cost_usd,
        "sources_visited": sorted(session.sources_visited),
        "current_source_url": session.current_source_url,
        "search_queries": session.search_queries,
        "source_candidates": session.source_candidates,
        "detection_events": [
            {
                "url": event.url,
                "reason": event.reason,
                "timestamp": event.timestamp.isoformat(),
            }
            for event in session.detection_events
        ],
        "termination_state": session.termination_state,
        "termination_reason": session.termination_reason,
        "evidence_quality": session.evidence_quality_metrics(),
        "evidence_records": [
            {
                "url": ev.url,
                "title": ev.title,
                "claims_count": len(ev.claims),
                "credibility_score": ev.credibility_score,
                "evidence_type": ev.evidence_type,
            }
            for ev in session.evidence_records
        ],
    }


def _serialize_synthesis(report: ResearchReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return report.to_dict()


def _serialize_run_result(result: PlannerRunResult) -> dict[str, Any]:
    return {
        "status": "completed" if result.session.steps_taken > 0 else "stopped",
        "session": _serialize_session(result.session),
        "decision": _serialize_decision(result.decision),
        "tool_result": result.tool_result,
        "synthesis": None,
    }


def _serialize_sequence_result(result: PlannerSequenceResult) -> dict[str, Any]:
    status = "completed" if result.tool_results else "stopped"
    return {
        "status": status,
        "status_events": build_status_events(result),
        "session": _serialize_session(result.session),
        "decisions": [_serialize_decision(decision) for decision in result.decisions],
        "tool_results": result.tool_results,
        "synthesis": _serialize_synthesis(result.synthesis),
    }


def create_research_router(
    settings: Settings,
    *,
    orchestrator: ResearchOrchestratorLike | None = None,
    repository: ResearchRepository | None = None,
) -> APIRouter:
    """Create the research endpoint bound to current settings."""
    router = APIRouter(tags=["research"])
    active_orchestrator = orchestrator or ResearchOrchestrator(settings)
    active_repository = repository or InMemoryResearchRepository()

    @router.post("/research")
    async def create_research(request: ResearchRequest) -> dict[str, Any]:
        research_goal = request.research_goal.strip()
        if not research_goal:
            raise HTTPException(status_code=422, detail="research_goal cannot be blank")
        try:
            result = await active_orchestrator.run_sequence(research_goal)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return active_repository.save(_serialize_sequence_result(result))

    @router.get("/research/{job_id}")
    async def get_research(job_id: str) -> dict[str, Any]:
        payload = active_repository.get(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="research job not found")
        return payload

    @router.get("/research/{job_id}/events")
    async def stream_research_events(job_id: str) -> StreamingResponse:
        payload = active_repository.get(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="research job not found")
        status_events = payload.get("status_events", [])
        if not isinstance(status_events, list):
            status_events = []

        async def event_stream():
            for event in status_events:
                if isinstance(event, dict):
                    yield encode_sse_event(event)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router


__all__ = [
    "ResearchRequest",
    "ResearchRepository",
    "create_research_router",
]
