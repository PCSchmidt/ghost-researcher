# ERRORS.md

Blueprint v11 | Living Failure Log

Every debugged issue is logged here. Check this FIRST before diagnosing.
Format: ERR-[NNN]: [title], root cause, fix, prevention

## KNOWN ERRORS

### ERR-001: Agent loop on repeated URLs

Root cause: Planner revisits already-visited URLs without improving coverage.
Fix: Cache results by URL and force source diversification after repeated visits.
Prevention: Track `sources_visited` and hard-stop repeated loops.

### ERR-002: Cost runaway from uncapped planner calls

Root cause: Planner keeps calling tools after the useful coverage frontier is reached.
Fix: Enforce `MAX_TOKENS_PER_JOB`, `MAX_STEPS_PER_JOB`, and `MAX_MODEL_COST_PER_JOB_USD`, then finalize early.
Prevention: Token, step, and dollar budget check before every planner turn.

### ERR-003: Unsupported claims in synthesized report

Root cause: Report text contains claims not grounded in extracted evidence.
Fix: Reject any synthesized output whose claims do not map to `evidence_records`.
Prevention: Make source traceability a hard validation rule before returning a report.

### ERR-004: Bot detection cascade

Root cause: High-value sources block automation, and the planner keeps retrying the same path.
Fix: Record detection events and pivot to alternate discovery paths or finalize with limitations.
Prevention: Detection-aware planning and limited retries per domain.

### ERR-005: Context overflow in long research sessions

Root cause: Raw tool outputs accumulate until the planner loses usable context.
Fix: Summarize older steps and retain only normalized evidence.
Prevention: Mid-session compression after every 10 tool calls.

### ERR-006: CDP server unavailable

Root cause: CloakBrowser or its transport endpoint is offline.
Fix: Fail executor tools fast and surface degraded health state to the runner.
Prevention: Health checks at startup and before navigation-heavy jobs.

### ERR-007: Status endpoint overload from polling

Root cause: Frequent client polling amplifies API load across concurrent jobs.
Fix: Stream status updates over SSE and reserve polling as a fallback.
Prevention: Keep UI transport aligned with DEC-006.

### ERR-008: Invalid model tool calls across providers

Root cause: Lower-cost models may vary in function calling and structured JSON reliability.
Fix: Validate every planner response against the tool schema, retry once, then escalate or finalize safely.
Prevention: Keep model routing behind an adapter and never trust raw model output without schema validation.

### ERR-009: Missing model cost telemetry

Root cause: Model calls do not persist usage and reported cost metadata.
Fix: Record model slug, prompt tokens, completion tokens, reported cost, and fallback tier for every model call.
Prevention: Make cost logging part of planner/synthesizer adapter tests.

### ERR-010: Job hangs at planner turn 0 to the hard timeout (unbounded model call)

Root cause: A single OpenRouter call has no overall wall-clock bound. The blocking
`urlopen(timeout=30)` runs in a worker thread, but OpenRouter sends keep-alive
`: OPENROUTER PROCESSING` comment bytes during long generations, which keeps the socket
active and defeats the per-socket 30s timeout. A slow/stuck generation therefore runs
until the job's `JOB_HARD_TIMEOUT_SECONDS` cap. Observed in production (job a90b4ac0):
the FIRST planner call (`run_sequence` step 0 is `_plan_next`, before any browser op)
hung for the full 420s → `planner_turns=0, tokens=0, sources=[]`, terminal
`job_timeout: exceeded hard wall-clock limit`, STEPS/SOURCES 0 in the UI. Not the
stale-browser issue (no browser op runs before the first planner call; health was OK; a
fresh job ran fine).
Fix: `OpenRouterChatClient.complete` wraps the `to_thread` await in `asyncio.wait_for`
bounded by `MODEL_CALL_TIMEOUT_SECONDS` (default 90s); on timeout it raises
`PlannerAdapterError("openrouter_timeout")`. The planner loop's broad except finalizes on
gathered evidence; the synthesizer degrades to its deterministic build. So one stuck
generation now fails fast and the job returns/ends in ~90s instead of hanging 420s.
Prevention: bound every external call with an overall wall-clock deadline, not just a
per-socket timeout — keep-alive bytes make socket timeouts insufficient. Mirrors the
navigate bounding (ERR-006 family).
