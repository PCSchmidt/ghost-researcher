# VERSION_ROADMAP.md

Blueprint v11 | GhostResearcher Sequential Build Roadmap  
Created: 2026-05-28

---

## Purpose

This roadmap is the stable stage plan for building GhostResearcher from the
current prototype into a deployable agentic research system. Use this file to
decide what stage comes next. Use [SPEC.md](./SPEC.md) for the current active
gate details and [SPEC_GATES.md](./SPEC_GATES.md) for the compact gate checklist.

---

## Stage Rules

- Build in order unless a blocker requires a narrow support task.
- Keep every stage independently testable.
- Do not add frontend, persistence, or synthesis before the backend control path is stable.
- Executor behavior must remain callable through `ResearchRunner`; avoid bypass paths.
- Every gate close updates `SPEC.md`, memory files, and this roadmap if the plan changes.

---

## Current Status

Current stage: v0.13.0 - Frontend Research UI

Recently completed:

- v0.1.0 foundation docs and memory files
- v0.2.0 tool schema lock
- v0.3.0 first executor action, `navigate_to_url`
- v0.4.0 deterministic planner integration skeleton
- v0.5.0 `POST /research` API skeleton
- v0.6.0 extraction and credibility executor skeletons
- v0.7.0 multi-step planner skeleton
- v0.8.0 search tool skeleton
- v0.9.0 OpenRouter planner adapter
- v0.10.0 synthesizer skeleton
- v0.11.0 persistence and job state
- v0.12.0 live status stream

Foundation items resolved on 2026-05-29:

- Dollar-denominated cost ceilings are locked in [CONTRACT.md](./CONTRACT.md) and [COSTS.md](./COSTS.md)
- [AGENT_SPEC.md](./AGENT_SPEC.md) passed critical review with the OpenRouter-first model-routing decision logged in [DECISIONS.md](./DECISIONS.md)
- Gate 1 is confirmed for continued implementation

---

## v0.1.0 - Foundation + Agent Contract

Goal: Convert prototype notes into build contracts.

Ships:

- [CONTRACT.md](./CONTRACT.md)
- [AGENT_SPEC.md](./AGENT_SPEC.md)
- [SPEC.md](./SPEC.md)
- [ERRORS.md](./ERRORS.md)
- Memory files
- [benchmark_prompts.json](../evals/benchmark_prompts.json)

Exit criteria:

- Required core docs exist
- Benchmark prompts exist
- Hard guard rails are documented
- Cost ceilings and critical review are resolved before formal close

Status: Complete.

---

## v0.2.0 - Tool Interface Lock

Goal: Turn the planned tool catalog into executable schema definitions.

Ships:

- [backend/agent/tools.py](../backend/agent/tools.py)
- Tool catalog tests

Exit criteria:

- All five tools have `input_schema`
- No stubs in the tool catalog
- Tests verify expected names and required schema sections

Status: Complete.

---

## v0.3.0 - First Executor Action

Goal: Prove the executor seam with one real browser action.

Ships:

- [backend/executor/browser.py](../backend/executor/browser.py)
- [backend/executor/navigate.py](../backend/executor/navigate.py)
- [backend/jobs/runner.py](../backend/jobs/runner.py)
- Executor and runner tests

Exit criteria:

- CDP health check exists
- `navigate_to_url` returns schema-shaped output
- Runner can dispatch navigation and update `AgentSession`

Status: Complete with fake page tests; live CloakBrowser integration remains later.

---

## v0.4.0 - Planner Integration Skeleton

Goal: Add deterministic planner-to-runner orchestration before the LLM planner exists.

Ships:

- [backend/agent/planner.py](../backend/agent/planner.py)
- [backend/jobs/research.py](../backend/jobs/research.py)

Exit criteria:

- Planner emits a structured `navigate_to_url` call from a URL-bearing goal
- Orchestrator dispatches through `ResearchRunner`
- URL-free goals terminate without executor dispatch at this stage; this historical behavior is superseded by v0.8 search

Status: Complete.

---

## v0.5.0 - API Research Endpoint Skeleton

Goal: Expose the planner/runner path through the API without persistence or synthesis.

Ships:

- [backend/api/research.py](../backend/api/research.py)
- FastAPI route tests

Exit criteria:

- `POST /research` accepts a non-empty research goal
- Endpoint invokes the orchestrator
- Response includes session state, planner decision, tool output, and `synthesis: null`

Status: Complete.

---

## v0.6.0 - Extract and Credibility Skeletons

Goal: Make the remaining executor-side tools callable through the runner.

Ships:

- [backend/executor/extract.py](../backend/executor/extract.py)
- [backend/executor/credibility.py](../backend/executor/credibility.py)
- Expanded `ResearchRunner` dispatch

Exit criteria:

- `extract_structured_data` returns schema-shaped extraction output
- `assess_credibility` returns score features and rationale
- Runner dispatches navigation, extraction, and credibility

Status: Complete.

---

## v0.7.0 - Multi-Step Planner Skeleton

Goal: Extend deterministic orchestration from one action to a fixed sequence.

Sequence:

1. `navigate_to_url`
2. `extract_structured_data`
3. `assess_credibility`

Ships:

- Multi-step planner state transitions
- Multi-step orchestrator result type
- `POST /research` sequence response
- Tests for full sequence trace

Exit criteria:

- Planner selects the correct next tool based on session progress
- Orchestrator executes all three steps with fake executors
- Session records source, extraction summary, credibility result, and final status
- API returns `decisions[]`, `tool_results[]`, session state, and `synthesis: null`

Status: Complete.

---

## v0.8.0 - Search Tool Skeleton

Goal: Add the missing `web_search` executor path so research goals without URLs can start.

Ships:

- `backend/executor/search.py`
- Runner dispatch for `web_search`
- Planner fallback from no URL to search query
- Source candidate queue in `AgentSession`

Exit criteria:

- URL-free research goal produces `web_search`
- Search results feed the next navigation step
- Tests cover empty, duplicate, and new-result cases

Status: Complete.

---

## v0.9.0 - OpenRouter Planner Adapter

Goal: Replace deterministic planning with an OpenRouter-backed adapter while preserving the same tool-call contract.

Ships:

- OpenRouter planner adapter
- Prompt templates
- Tool-call validation
- Token and dollar budget checks before each planner turn

Exit criteria:

- Adapter emits validated tool calls only
- Invalid/free-text planner output is rejected safely
- Token, step, and dollar budgets are enforced
- Model slug, token usage, and reported cost are logged for each planner call

Status: Complete.

---

## v0.10.0 - Synthesizer Skeleton

Goal: Produce a structured report from extracted evidence without allowing unsupported claims.

Ships:

- Report schema
- Synthesizer adapter
- Claim-to-source validation
- API synthesis serialization

Exit criteria:

- Report contains cited claims only
- Unsupported claims fail validation
- Sufficient coverage triggers synthesis path

Status: Complete.

---

## v0.11.0 - Persistence and Job State

Goal: Persist research jobs, step events, sources, and reports.

Ships:

- Repository layer
- Job status storage
- API response backed by stored state
- In-memory repository for dependency-free runs
- JSON-file repository proving restart durability

Exit criteria:

- Research jobs survive process restart
- Step history can be retrieved by job ID
- Report and source records are queryable

Status: Complete.

---

## v0.12.0 - Live Status Stream

Goal: Add SSE job status streaming for frontend integration.

Ships:

- `backend/jobs/status.py` status event model
- Persisted `status_events[]` on research job responses
- `GET /research/{job_id}/events` SSE endpoint
- SSE wire-format tests

Exit criteria:

- Frontend can consume ordered job, tool, planner stop, synthesis, and completion events
- Status views can use EventSource against a persisted job without polling `GET /research/{job_id}`
- Missing job streams return 404

Status: Complete.

---

## v0.13.0 - Frontend Research UI

Goal: Build the first usable Next.js interface around real backend behavior.

Ships:

- Research submission form
- Job status view
- Source and credibility display
- Report placeholder state until synthesis is complete

Exit criteria:

- User can submit a goal and watch steps execute
- UI renders navigation, extraction, and credibility events clearly

Status: Next.

---

## v0.14.0 - Evals Harness

Goal: Turn benchmark prompts into repeatable quality checks.

Ships:

- `evals/eval_runner.py`
- Scoring outputs in `evals/results/`
- Report quality and source traceability checks

Exit criteria:

- At least 3 benchmark prompts run end to end
- Results are persisted as eval artifacts

Status: Planned.

---

## v1.0.0 - Deployment

Goal: Deploy backend and frontend with health checks and rollback path.

Ships:

- Railway backend deployment
- Railway CloakBrowser service
- Vercel frontend deployment
- Environment configuration docs

Exit criteria:

- `/health` returns healthy dependency status
- `POST /research` works against deployed backend
- Frontend can run a demo research job

Status: Planned.
