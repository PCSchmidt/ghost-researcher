"""Prompt templates for planner model calls."""

from __future__ import annotations

import json
from typing import Any

from backend.agent.memory import AgentSession
from backend.agent.tools import TOOLS

PLANNER_SYSTEM_PROMPT = """You are the GhostResearcher planner. Output exactly one structured tool call.
Do not answer the user directly. Do not include free-text analysis. Select from the provided tool catalog only.
Call finalize_report only when coverage is sufficient or a hard stop is required.
Respect source deduplication, cost limits, and the current session state."""


def _session_snapshot(session: AgentSession) -> dict[str, Any]:
    return {
        "research_goal": session.research_goal,
        "steps_taken": session.steps_taken,
        "planner_turns": session.planner_turns,
        "running_tokens": session.running_tokens,
        "running_cost_usd": session.running_cost_usd,
        "sources_visited": sorted(session.sources_visited),
        "search_queries": session.search_queries,
        "source_candidates": session.source_candidates,
        "evidence_count": len(session.evidence_records),
        "detection_events": [
            {"url": event.url, "reason": event.reason, "timestamp": event.timestamp.isoformat()}
            for event in session.detection_events
        ],
        "termination_state": session.termination_state,
        "termination_reason": session.termination_reason,
        "session_summary": session.session_summary,
    }


def build_planner_messages(session: AgentSession, *, last_tool_result: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Build OpenAI-compatible chat messages for one planner turn."""
    payload = {
        "session_state": _session_snapshot(session),
        "last_tool_result": last_tool_result,
        "available_tools": TOOLS,
        "planner_rules": [
            "Return exactly one tool call using the chat-completions tool calling interface.",
            "Prefer unvisited sources and queued source candidates over repeated URLs.",
            "Use web_search when no usable URL or candidate source exists.",
            "Use finalize_report for sufficient_coverage, no_new_sources, max_steps, cost_limit, or detection_blocked.",
        ],
    }
    return [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, sort_keys=True)},
    ]
