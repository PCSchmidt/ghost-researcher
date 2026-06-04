"""Schema-only tool catalog for the GhostResearcher planner."""

from __future__ import annotations

from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "name": "navigate_to_url",
        "description": "Navigate the stealth browser to a URL and return normalized page state. The page always waits for domcontentloaded automatically. Only set wait_for when you need to wait for a specific CSS selector (like '.article-body' or 'h1') to appear after the page loads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "wait_for": {"type": "string", "description": "Optional CSS selector to wait for after navigation, e.g. '.main-content' or 'article'. Do NOT use 'domcontentloaded' or 'networkidle' here — those load events are handled automatically."},
                "fingerprint_seed": {"type": "integer"},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "final_url": {"type": "string"},
                "title": {"type": "string"},
                "status_code": {"type": "integer"},
                "content_excerpt": {"type": "string"},
                "links": {"type": "array", "items": {"type": "string"}},
                "detection_blocked": {"type": "boolean"},
                "blocked_reason": {"type": ["string", "null"]},
                "screenshot_path": {"type": ["string", "null"]},
                "timing_ms": {"type": "integer"},
            },
            "required": [
                "url",
                "final_url",
                "title",
                "status_code",
                "content_excerpt",
                "links",
                "detection_blocked",
                "timing_ms",
            ],
        },
        "error_contract": [
            "navigation_timeout",
            "invalid_url",
            "cdp_unavailable",
            "detection_blocked",
        ],
    },
    {
        "name": "extract_structured_data",
        "description": "Extract structured content from the current page for synthesis and scoring.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "extraction_goal": {"type": "string"},
                "output_schema": {"type": "object"},
            },
            "required": ["selector", "extraction_goal"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "extraction_goal": {"type": "string"},
                "records": {"type": "array", "items": {"type": "object"}},
                "text_excerpt": {"type": "string"},
                "record_count": {"type": "integer"},
                "schema_valid": {"type": "boolean"},
            },
            "required": [
                "selector",
                "extraction_goal",
                "records",
                "text_excerpt",
                "record_count",
                "schema_valid",
            ],
        },
        "error_contract": [
            "selector_not_found",
            "page_not_loaded",
            "schema_validation_failed",
        ],
    },
    {
        "name": "web_search",
        "description": "Search the web and return ranked candidate sources.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "num_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"},
                            "source_type": {"type": "string"},
                        },
                        "required": ["title", "url", "snippet", "source_type"],
                    },
                },
                "new_result_count": {"type": "integer"},
            },
            "required": ["query", "results", "new_result_count"],
        },
        "error_contract": [
            "search_provider_unavailable",
            "search_rate_limited",
            "empty_query",
        ],
    },
    {
        "name": "assess_credibility",
        "description": "Score a source for trustworthiness and usefulness in the report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "content_snippet": {"type": "string"},
            },
            "required": ["url", "content_snippet"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                "domain_authority": {"type": "number", "minimum": 0, "maximum": 1},
                "freshness": {"type": "number", "minimum": 0, "maximum": 1},
                "corroboration": {"type": "number", "minimum": 0, "maximum": 1},
                "detection_penalty": {"type": "number", "minimum": 0, "maximum": 1},
                "rationale": {"type": "string"},
            },
            "required": [
                "url",
                "score",
                "domain_authority",
                "freshness",
                "corroboration",
                "detection_penalty",
                "rationale",
            ],
        },
        "error_contract": ["insufficient_content", "unsupported_source"],
    },
    {
        "name": "finalize_report",
        "description": "Explicitly terminate research and hand the session to the synthesizer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "sources_used": {"type": "array", "items": {"type": "string"}},
                "termination_reason": {
                    "type": "string",
                    "enum": [
                        "sufficient_coverage",
                        "max_steps",
                        "cost_limit",
                        "no_new_sources",
                        "detection_blocked",
                    ],
                },
            },
            "required": ["confidence", "sources_used", "termination_reason"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "accepted": {"type": "boolean"},
                "queued_for_synthesis": {"type": "boolean"},
                "termination_reason": {"type": "string"},
            },
            "required": ["accepted", "queued_for_synthesis", "termination_reason"],
        },
        "error_contract": [
            "no_sources_selected",
            "invalid_confidence",
            "termination_reason_mismatch",
        ],
    },
]

TOOL_REGISTRY: dict[str, dict[str, Any]] = {tool["name"]: tool for tool in TOOLS}


def get_tool(name: str) -> dict[str, Any]:
    """Return a single tool definition by name."""
    return TOOL_REGISTRY[name]
