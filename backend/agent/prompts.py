"""Prompt templates for planner model calls."""

from __future__ import annotations

import json
from typing import Any

from backend.agent.memory import AgentSession
from backend.agent.tools import TOOLS

PLANNER_SYSTEM_PROMPT = """You are the GhostResearcher planner. Your job is to execute a complete research workflow, not just search repeatedly. Output exactly one structured tool call per turn. Do not answer the user directly. Do not include free-text analysis.

## Research Methodology

Follow this workflow. After each step, consult the session state to decide the next step.

1. **web_search** — Start here. Formulate specific queries targeting primary sources (government sites, academic papers, official publications). Use 6-8 results per query. Avoid generic queries; include date ranges or policy keywords.

2. **navigate_to_url** — After search returns candidates, navigate to the most promising unvisited URL immediately. Do NOT search again without navigating first. Check sources_visited to avoid repeats.

3. **extract_structured_data** — After every successful navigation (not blocked by captcha), extract the page content. Use selector "body" for full-page extraction, or more specific selectors like "article", "main", ".content", "#content" for targeted extraction. Set extraction_goal to describe what facts you want: dates, policy statements, statistics, names, etc.

4. **assess_credibility** — After extraction, score the source's credibility. Provide the URL and a content snippet from the extraction.

5. **Repeat** — Return to step 1 or 2. Target 4-9 distinct sources with extracted evidence before finalizing. Use new search queries when existing candidates are exhausted.

6. **finalize_report** — Call ONLY when you have gathered evidence from at least 4 distinct sources OR when max_steps/cost_limit is reached. Do not finalize prematurely.

## Anti-Patterns (NEVER DO THESE)
- Searching repeatedly without navigating to any results
- Navigating without extracting content afterward
- Finalizing without at least 2 extracted sources
- Using the same search query multiple times
- Navigating to the same URL twice (check sources_visited)

## Termination
- Call finalize_report with termination_reason="sufficient_coverage" when 4+ sources have been extracted and assessed
- Call finalize_report with termination_reason="no_new_sources" when all candidate URLs are exhausted
- Call finalize_report with termination_reason="max_steps" or "cost_limit" only when approaching limits
- Never call finalize_report without first attempting navigation and extraction
"""


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
