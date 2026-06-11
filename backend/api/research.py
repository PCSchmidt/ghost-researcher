"""Research job endpoints for GhostResearcher."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agent.memory import AgentSession
from backend.agent.planner import PlannerDecision, ToolCall
from backend.config import Settings
from backend.jobs.research import PlannerRunResult, PlannerSequenceResult, ResearchOrchestrator
from backend.jobs.status import JobStatusEvent, build_status_events, encode_sse_event
from backend.persistence import InMemoryResearchRepository, ResearchRepository
from backend.synthesizer.schema import ResearchReport

logger = logging.getLogger("ghostresearcher.api")


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


def _report_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Trim a stored job payload to a lightweight row for the /reports list."""
    session = payload.get("session") or {}
    synthesis = payload.get("synthesis") or {}
    return {
        "job_id": payload.get("job_id"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "status": payload.get("status"),
        "research_goal": session.get("research_goal"),
        "title": synthesis.get("title"),
        "confidence": synthesis.get("confidence"),
        "is_long_form": bool(synthesis.get("sections")),
        "source_count": len(session.get("sources_visited") or []),
    }


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


def _running_job_payload(research_goal: str) -> dict[str, Any]:
    """Initial record saved before a job runs so the client can poll immediately."""
    session = AgentSession(research_goal=research_goal)
    started = JobStatusEvent(
        sequence=0,
        event_type="job_started",
        status="active",
        message="Research job accepted",
        payload={"research_goal": research_goal},
    )
    return {
        "status": "running",
        "status_events": [started.to_dict()],
        "session": _serialize_session(session),
        "decisions": [],
        "tool_results": [],
        "synthesis": None,
    }


def _failed_job_payload(research_goal: str, detail: str) -> dict[str, Any]:
    """Terminal record written when a background job raises before producing a result."""
    session = AgentSession(research_goal=research_goal)
    session.finalize("error")
    events = [
        JobStatusEvent(
            sequence=0,
            event_type="job_started",
            status="active",
            message="Research job accepted",
            payload={"research_goal": research_goal},
        ).to_dict(),
        JobStatusEvent(
            sequence=1,
            event_type="job_failed",
            status="error",
            message="Research job failed",
            payload={"detail": detail},
        ).to_dict(),
    ]
    return {
        "status": "error",
        "error": detail,
        "status_events": events,
        "session": _serialize_session(session),
        "decisions": [],
        "tool_results": [],
        "synthesis": None,
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

    # A research job can take minutes. Running it synchronously inside the request
    # made mobile browsers drop the long-pending fetch ("Failed to fetch"). Instead
    # POST persists a "running" record and returns immediately; the job runs detached
    # and the client polls GET /research/{job_id}. The lock serializes execution so
    # concurrent jobs do not collide on the single shared CloakBrowser.
    job_lock = asyncio.Lock()
    background_tasks: set[asyncio.Task[Any]] = set()

    async def _persist_progress(
        job_id: str,
        session: AgentSession,
        decisions: list[PlannerDecision],
        tool_results: list[dict[str, Any]],
    ) -> None:
        # Live in-progress snapshot so the polling client sees steps/sources climb.
        # Must never raise into the planner loop, so swallow persistence errors.
        try:
            snapshot = PlannerSequenceResult(
                session=session,
                decisions=list(decisions),
                tool_results=list(tool_results),
            )
            payload = {
                "status": "running",
                "status_events": build_status_events(snapshot, final=False),
                "session": _serialize_session(session),
                "decisions": [_serialize_decision(decision) for decision in decisions],
                "tool_results": list(tool_results),
                "synthesis": None,
            }
            active_repository.update(job_id, payload)
        except Exception:  # noqa: BLE001 - progress persistence is best-effort
            logger.exception("failed to persist progress for research job %s", job_id)

    async def _execute_research_job(job_id: str, research_goal: str) -> None:
        async with job_lock:
            try:
                # Hard wall-clock backstop: the in-loop time budget only checks between
                # steps, so a single hung browser/CDP call could otherwise run forever and
                # — because jobs are serialized — stall the whole queue. Cancel and store a
                # terminal error instead.
                async def _run() -> Any:
                    return await active_orchestrator.run_sequence(
                        research_goal,
                        progress_callback=lambda s, d, t: _persist_progress(job_id, s, d, t),
                    )

                result = await asyncio.wait_for(_run(), timeout=settings.job_hard_timeout_seconds)
                payload = _serialize_sequence_result(result)
            except TimeoutError:
                logger.warning("background research job %s exceeded hard timeout for goal=%r", job_id, research_goal)
                payload = _failed_job_payload(research_goal, "job_timeout: exceeded hard wall-clock limit")
            except Exception as exc:  # noqa: BLE001 - persist failure as a terminal job, never crash the worker
                logger.exception("background research job %s failed for goal=%r", job_id, research_goal)
                payload = _failed_job_payload(research_goal, str(exc))
            if active_repository.update(job_id, payload) is None:
                logger.warning("research job %s vanished before completion could be stored", job_id)

    @router.post("/research")
    async def create_research(request: ResearchRequest) -> dict[str, Any]:
        research_goal = request.research_goal.strip()
        if not research_goal:
            raise HTTPException(status_code=422, detail="research_goal cannot be blank")
        running = active_repository.save(_running_job_payload(research_goal))
        job_id = str(running["job_id"])
        task = asyncio.create_task(_execute_research_job(job_id, research_goal))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
        return running

    @router.get("/research/{job_id}")
    async def get_research(job_id: str) -> dict[str, Any]:
        payload = active_repository.get(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="research job not found")
        return payload

    @router.get("/reports")
    async def list_reports() -> dict[str, Any]:
        return {"reports": [_report_summary(payload) for payload in active_repository.list()]}

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
