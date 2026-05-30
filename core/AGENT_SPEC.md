# AGENT_SPEC.md

Blueprint v11 | Planner, Tool, and Session Contract  
Gate 1 exit artifact for GhostResearcher

---

## PURPOSE

Define the contract between the LLM planner, the CloakBrowser-backed executor,
the report synthesizer, and the session state manager before implementation begins.

---

## PLANNER SYSTEM PROMPT CONTRACT

The planner adapter should call models through OpenRouter by default. Anthropic
direct access is a premium fallback only, not the normal runtime path.

### Inputs available to the planner

- `research_goal`: user research question or prompt
- `session_state`: current AgentSession snapshot
- `tool_catalog`: full tool schemas and output contracts
- `last_tool_result`: normalized result from the previous executor step
- `policy_constraints`: max steps, token budget, source traceability, dedup rules
- `session_summary`: compressed summary of earlier tool results after context compaction

### Required planner behavior

- Output structured tool calls only
- Call exactly one tool per planning step
- Never emit free-text analysis as the terminal action
- Prefer new, higher-value sources over revisiting prior URLs
- Reuse cached results when a URL or query has already been executed in-session
- Call `finalize_report` when sufficient coverage is reached or a hard stop is hit

### Termination conditions

- `max_steps`: hard stop when `steps_taken >= MAX_STEPS_PER_JOB`
- `cost_limit`: hard stop when `running_tokens >= MAX_TOKENS_PER_JOB` or `running_cost_usd >= MAX_MODEL_COST_PER_JOB_USD`
- `sufficient_coverage`: minimum source count met, source diversity met, and planner confidence >= 0.80
- `no_new_sources`: two consecutive search/navigation attempts produce no novel usable sources
- `detection_blocked`: high-value paths are repeatedly blocked and the planner can no longer diversify the plan

### Cost guard

- Default token budget per job: `MAX_TOKENS_PER_JOB=50000`
- Default step budget per job: `MAX_STEPS_PER_JOB=20`
- Default planner completion budget: 12 planner turns per job
- Default model spend hard ceiling per job: `MAX_MODEL_COST_PER_JOB_USD=0.05`
- Default model spend warning threshold per job: `WARN_MODEL_COST_PER_JOB_USD=0.02`
- Any step that would exceed the remaining token or dollar budget must route directly to `finalize_report`
- Every model response must record model slug, prompt tokens, completion tokens, and reported cost when available

### Model routing policy

| Tier | Purpose | Default candidates | Trigger |
| --- | --- | --- | --- |
| Default | Planner tool selection, normal extraction normalization, normal synthesis | `deepseek/deepseek-v4-flash`, `qwen/qwen3-235b-a22b-2507` | First attempt for routine jobs |
| Quality fallback | Harder synthesis or failed tool/JSON validation | `deepseek/deepseek-v4-pro`, `moonshotai/kimi-k2.6`, `moonshotai/kimi-k2-thinking` | Validation failure, complex comparison, or confidence below threshold |
| Premium fallback | Last resort for repeated failures | `anthropic/claude-sonnet-latest` or direct Anthropic adapter | Explicit configuration only |

Routing rules:

- Model slugs are configuration, not hard-coded business logic.
- Prefer the cheapest configured model that supports the required behavior.
- Validate tool calls and structured JSON before accepting planner output.
- Retry once on the default tier, then escalate to quality fallback if the result still fails validation.
- Do not escalate if doing so would exceed `MAX_MODEL_COST_PER_JOB_USD`; finalize with `cost_limit` instead.

---

## TOOL CONTRACTS

### 1. `navigate_to_url`

**Purpose:** Navigate the stealth browser to a URL and return normalized page state.

#### navigate_to_url input schema

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string", "format": "uri"},
    "wait_for": {"type": "string"},
    "fingerprint_seed": {"type": "integer"}
  },
  "required": ["url"]
}
```

#### navigate_to_url output schema

```json
{
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
    "timing_ms": {"type": "integer"}
  },
  "required": [
    "url",
    "final_url",
    "title",
    "status_code",
    "content_excerpt",
    "links",
    "detection_blocked",
    "timing_ms"
  ]
}
```

#### navigate_to_url error contract

- `navigation_timeout`
- `invalid_url`
- `cdp_unavailable`
- `detection_blocked`

### 2. `extract_structured_data`

**Purpose:** Extract structured content from the current page for synthesis and scoring.

#### extract_structured_data input schema

```json
{
  "type": "object",
  "properties": {
    "selector": {"type": "string"},
    "extraction_goal": {"type": "string"},
    "output_schema": {"type": "object"}
  },
  "required": ["selector", "extraction_goal"]
}
```

#### extract_structured_data output schema

```json
{
  "type": "object",
  "properties": {
    "selector": {"type": "string"},
    "extraction_goal": {"type": "string"},
    "records": {"type": "array", "items": {"type": "object"}},
    "text_excerpt": {"type": "string"},
    "record_count": {"type": "integer"},
    "schema_valid": {"type": "boolean"}
  },
  "required": [
    "selector",
    "extraction_goal",
    "records",
    "text_excerpt",
    "record_count",
    "schema_valid"
  ]
}
```

#### extract_structured_data error contract

- `selector_not_found`
- `page_not_loaded`
- `schema_validation_failed`

### 3. `web_search`

**Purpose:** Search the web and return ranked candidate sources.

#### web_search input schema

```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"},
    "num_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10}
  },
  "required": ["query"]
}
```

#### web_search output schema

```json
{
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
          "source_type": {"type": "string"}
        },
        "required": ["title", "url", "snippet", "source_type"]
      }
    },
    "new_result_count": {"type": "integer"}
  },
  "required": ["query", "results", "new_result_count"]
}
```

#### web_search error contract

- `search_provider_unavailable`
- `search_rate_limited`
- `empty_query`

### 4. `assess_credibility`

**Purpose:** Score a source for trustworthiness and usefulness in the report.

#### assess_credibility input schema

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string", "format": "uri"},
    "content_snippet": {"type": "string"}
  },
  "required": ["url", "content_snippet"]
}
```

#### assess_credibility output schema

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string"},
    "score": {"type": "number", "minimum": 0, "maximum": 1},
    "domain_authority": {"type": "number", "minimum": 0, "maximum": 1},
    "freshness": {"type": "number", "minimum": 0, "maximum": 1},
    "corroboration": {"type": "number", "minimum": 0, "maximum": 1},
    "detection_penalty": {"type": "number", "minimum": 0, "maximum": 1},
    "rationale": {"type": "string"}
  },
  "required": [
    "url",
    "score",
    "domain_authority",
    "freshness",
    "corroboration",
    "detection_penalty",
    "rationale"
  ]
}
```

#### assess_credibility error contract

- `insufficient_content`
- `unsupported_source`

### 5. `finalize_report`

**Purpose:** Explicitly terminate research and hand the session to the synthesizer.

#### finalize_report input schema

```json
{
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
        "detection_blocked"
      ]
    }
  },
  "required": ["confidence", "sources_used", "termination_reason"]
}
```

#### finalize_report output schema

```json
{
  "type": "object",
  "properties": {
    "accepted": {"type": "boolean"},
    "queued_for_synthesis": {"type": "boolean"},
    "termination_reason": {"type": "string"}
  },
  "required": ["accepted", "queued_for_synthesis", "termination_reason"]
}
```

#### finalize_report error contract

- `no_sources_selected`
- `invalid_confidence`
- `termination_reason_mismatch`

---

## AGENT SESSION STATE SCHEMA

```json
{
  "research_goal": "string",
  "steps_taken": "integer",
  "planner_turns": "integer",
  "running_tokens": "integer",
  "running_cost_usd": "number",
  "sources_visited": ["string"],
  "search_queries": ["string"],
  "source_candidates": ["string"],
  "evidence_records": [
    {
      "url": "string",
      "title": "string",
      "extracted_at": "datetime",
      "credibility_score": "number",
      "claims": ["string"]
    }
  ],
  "detection_events": [
    {
      "url": "string",
      "reason": "string",
      "timestamp": "datetime"
    }
  ],
  "termination_state": "active|finalized|failed",
  "termination_reason": "string|null",
  "session_summary": "string|null"
}
```

### Session rules

- `sources_visited` is the primary deduplication set
- `source_candidates` queues novel URLs discovered by `web_search` before navigation
- Every synthesized claim must map to at least one `evidence_record`
- `detection_events` must influence future source selection
- `session_summary` is refreshed after every 10 tool calls or when context pressure rises

---

## FAILURE MODE CATALOG

| Error ID | Failure mode | Detection | Mitigation |
| --- | --- | --- | --- |
| ERR-001 | Agent revisits the same URL repeatedly | URL appears in `sources_visited` 3+ times | Return cached result, increment loop counter, force planner to diversify |
| ERR-002 | Planner exceeds token, step, or dollar budget | `running_tokens`, `steps_taken`, or `running_cost_usd` reaches hard limit | Route directly to `finalize_report` with hard-stop reason |
| ERR-003 | Synthesizer hallucinates unsupported claims | Claim lacks source trace in `evidence_records` | Reject synthesis output until every claim maps to evidence |
| ERR-004 | Bot detection cascade blocks key sources | Multiple `detection_events` on high-value domains | Switch search path, lower-risk domains, or finalize with explicit limitation |
| ERR-005 | Context window overflow in long sessions | Tool results exceed summarization threshold | Summarize older results and keep structured evidence only |
| ERR-006 | CloakBrowser or CDP server unavailable | Health check fails or navigation returns transport error | Fail executor tools fast and surface degraded health state |
| ERR-007 | Frontend status transport overload | High-frequency polling increases API load | Use SSE as the default status channel, polling only as fallback |
| ERR-008 | Model routing produces invalid tool calls | Planner output fails schema validation | Retry once on default model, then escalate to quality fallback or finalize safely |

---

## IMPLEMENTATION NOTES

- SSE is the intended default for job status updates; prior polling references are legacy planning notes
- `finalize_report` is the planner's only valid completion signal
- Gate 2 implementation begins with schema-only tool definitions in `backend/agent/tools.py`
- OpenRouter is the default model gateway; direct Anthropic use is a premium fallback path only
- The OpenRouter planner adapter uses fakeable transport in tests and validates every tool call against `backend/agent/tools.py` before execution
