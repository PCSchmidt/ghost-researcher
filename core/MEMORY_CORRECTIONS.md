# MEMORY_CORRECTIONS.md

Blueprint v11 | Reflexion Entries and Estimation Calibration

New entries added ABOVE previous, newest first.
Used by build-rules.md to calibrate future estimates.

## REFLEXION LOG

Format per entry:

```text
## REFLEXION: v[X.X.X] -- [Gate Name]
Date: [date]
Project: [name]
ESTIMATE: Predicted [X] hrs, Actual [X] hrs, Variance [+/-X]%
TECHNICAL PREDICTIONS VS REALITY: [what was expected vs what happened]
CORRECTION FOR FUTURE: [what changes]
MEMORY_SEMANTIC.md UPDATE: [pattern added/updated or none]
```

## ESTIMATION CALIBRATION LOG

## REFLEXION: v0.13.0 -- Frontend Research UI

Date: 2026-06-01
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: The frontend could stay thin because v0.12 already exposed persisted status events. The one backend support task needed for a real browser workflow was CORS configuration for local and deployed frontend origins.
CORRECTION FOR FUTURE: When a frontend gate starts consuming an API from a different origin, add CORS as part of the frontend integration slice and validate it with backend config tests.
MEMORY_SEMANTIC.md UPDATE: none.

---

## REFLEXION: v0.12.0 -- Live Status Stream

Date: 2026-06-01
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: A true live stream needs background job execution, but the current API still runs jobs synchronously. The useful v0.12 slice was a replayable SSE contract over persisted status events, which gives the frontend EventSource semantics without introducing Redis workers early.
CORRECTION FOR FUTURE: Add status events as persisted, ordered domain records before queueing; swap the producer from replay to live publication once background execution exists.
MEMORY_SEMANTIC.md UPDATE: none.

---

## REFLEXION: v0.11.0 -- Persistence and Job State

Date: 2026-06-01
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: Full Postgres/Redis persistence would be premature before status streaming and deployment shape are fixed. A repository boundary plus JSON-file durability gives testable job state without locking database schema too early.
CORRECTION FOR FUTURE: Add persistence behind a narrow repository protocol first, then swap backing stores once API retrieval and event models settle.
MEMORY_SEMANTIC.md UPDATE: none.

---

## REFLEXION: v0.10.0 -- Synthesizer Skeleton

Date: 2026-05-30
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: Synthesis fit cleanly once evidence records were already created by credibility assessment. The important boundary was not report prose, but rejecting any claim source absent from session evidence.
CORRECTION FOR FUTURE: Build report schemas around source traceability before adding model polish or formatting features.
MEMORY_SEMANTIC.md UPDATE: none.

---

## REFLEXION: v0.9.0 -- OpenRouter Planner Adapter

Date: 2026-05-30
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: The adapter needed async planner support in the orchestrator before it could fit cleanly beside the deterministic planner. Keeping transport injectable made validation testable without live model calls.
CORRECTION FOR FUTURE: Add model adapters as fake-tested ports first, then layer live-provider tests after the contract and budget behavior are stable.
MEMORY_SEMANTIC.md UPDATE: none.

---

## REFLEXION: v0.8.0 -- Search Tool Skeleton

Date: 2026-05-30
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: Adding search was not just a runner branch. The planner needed source candidate state so URL-free goals could search first, then navigate a novel result without reverting to the old no-URL safe stop.
CORRECTION FOR FUTURE: When adding executor discovery tools, update session state first so planner transitions can be expressed from state instead of step count alone.
MEMORY_SEMANTIC.md UPDATE: none.

---

## REFLEXION: Gate 1 -- Contract and Agent Spec

Date: 2026-05-29
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: Initial prototype assumed direct Anthropic planner/synthesizer calls. Cost review showed OpenRouter can provide cheaper capable models with one OpenAI-compatible API surface, usage metadata, fallback routing, tool calling, and structured outputs.
CORRECTION FOR FUTURE: Decide provider gateway and dollar ceilings before implementing the model adapter. Treat premium frontier models as explicit fallback, not default runtime.
MEMORY_SEMANTIC.md UPDATE: PAT-001 added.

---

## PRE-FILL ACCURACY LOG

[Empty until first interrogation with pre-fills]
