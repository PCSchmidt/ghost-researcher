# SPEC.md

Blueprint v11 | Current Gate Specification  
Updated at the start of each gate

---

## CURRENT GATE

**Version:** v0.16.0
**Gate Name:** Real Search and Live Evals
**Status:** DONE

---

## GOAL

Add the real search provider boundary and an offline/live eval mode split while
keeping deterministic offline tests dependency-free.

---

## TASKS

- [x] Confirm root context docs exist (`README.md`, `SETUP.md`, `CLAUDE.md`)
- [x] Seed [evals/benchmark_prompts.json](../evals/benchmark_prompts.json) with 10 benchmark prompts
- [x] Add [.env.example](../.env.example) and [.gitignore](../.gitignore)
- [x] Create [core/ERRORS.md](./ERRORS.md)
- [x] Create [core/MEMORY_SEMANTIC.md](./MEMORY_SEMANTIC.md)
- [x] Create [core/MEMORY_EPISODIC.md](./MEMORY_EPISODIC.md)
- [x] Create [core/MEMORY_CORRECTIONS.md](./MEMORY_CORRECTIONS.md)
- [x] Create [core/DECISIONS.md](./DECISIONS.md)
- [x] Create [core/SPEC_GATES.md](./SPEC_GATES.md)
- [x] Create [core/AGENT_SPEC.md](./AGENT_SPEC.md)
- [x] Finalize dollar-denominated cost ceilings via `/costs`
- [x] Review AGENT_SPEC against `/critical-thinker`
- [x] Mark Gate 1 CONFIRMED once contract and budgets are locked
- [x] Add schema-only [backend/agent/tools.py](../backend/agent/tools.py)
- [x] Add [backend/agent/memory.py](../backend/agent/memory.py) session state
- [x] Add FastAPI entrypoint and `/health` route
- [x] Add [backend/executor/browser.py](../backend/executor/browser.py) CDP health client
- [x] Add [backend/executor/navigate.py](../backend/executor/navigate.py) first executor action
- [x] Add [backend/jobs/runner.py](../backend/jobs/runner.py) thin tool-call runner
- [x] Add [backend/agent/planner.py](../backend/agent/planner.py) planner skeleton
- [x] Add [backend/jobs/research.py](../backend/jobs/research.py) planner-to-runner orchestration path
- [x] Add [backend/api/research.py](../backend/api/research.py) `POST /research` endpoint
- [x] Add [backend/executor/extract.py](../backend/executor/extract.py) structured extraction skeleton
- [x] Add [backend/executor/credibility.py](../backend/executor/credibility.py) credibility scoring skeleton
- [x] Extend [backend/jobs/runner.py](../backend/jobs/runner.py) to dispatch navigation, extraction, and credibility tools
- [x] Extend [backend/agent/planner.py](../backend/agent/planner.py) to select navigation, extraction, and credibility steps
- [x] Extend [backend/jobs/research.py](../backend/jobs/research.py) to return multi-step sequence results
- [x] Update [backend/api/research.py](../backend/api/research.py) to return `decisions[]` and `tool_results[]`
- [x] Add [backend/executor/search.py](../backend/executor/search.py) deterministic `web_search` skeleton
- [x] Extend [backend/agent/memory.py](../backend/agent/memory.py) with queued source candidates
- [x] Extend [backend/jobs/runner.py](../backend/jobs/runner.py) to dispatch `web_search`
- [x] Extend [backend/agent/planner.py](../backend/agent/planner.py) so URL-free goals search before navigation
- [x] Extend [backend/api/research.py](../backend/api/research.py) to expose source candidates in session state
- [x] Extend [backend/config.py](../backend/config.py) with OpenRouter model and cost settings
- [x] Add [backend/agent/prompts.py](../backend/agent/prompts.py) planner prompt templates
- [x] Add [backend/agent/openrouter.py](../backend/agent/openrouter.py) OpenRouter planner adapter
- [x] Extend [backend/agent/memory.py](../backend/agent/memory.py) with model usage accounting
- [x] Extend [backend/jobs/research.py](../backend/jobs/research.py) to support async planners
- [x] Add [tests/test_agent/test_openrouter.py](../tests/test_agent/test_openrouter.py) adapter tests
- [x] Add [backend/synthesizer/schema.py](../backend/synthesizer/schema.py) report schema and source validation
- [x] Add [backend/synthesizer/report.py](../backend/synthesizer/report.py) synthesizer skeleton
- [x] Extend [backend/jobs/research.py](../backend/jobs/research.py) to synthesize after sufficient coverage
- [x] Extend [backend/api/research.py](../backend/api/research.py) to serialize synthesized reports
- [x] Add [tests/test_synthesizer/test_schema.py](../tests/test_synthesizer/test_schema.py) and [tests/test_synthesizer/test_report.py](../tests/test_synthesizer/test_report.py)
- [x] Add [backend/persistence/repository.py](../backend/persistence/repository.py) repository boundary, in-memory store, and JSON-file store
- [x] Extend [backend/api/research.py](../backend/api/research.py) to persist `POST /research` responses
- [x] Add `GET /research/{job_id}` for job retrieval
- [x] Extend [backend/main.py](../backend/main.py) with injectable research repository
- [x] Add [tests/test_persistence/test_repository.py](../tests/test_persistence/test_repository.py) repository durability tests
- [x] Add [backend/jobs/status.py](../backend/jobs/status.py) status event model and SSE encoder
- [x] Extend [backend/api/research.py](../backend/api/research.py) to persist `status_events[]` with research jobs
- [x] Add `GET /research/{job_id}/events` SSE endpoint
- [x] Add [tests/test_jobs/test_status.py](../tests/test_jobs/test_status.py) status event and SSE encoding tests
- [x] Extend [tests/test_api/test_research.py](../tests/test_api/test_research.py) with SSE endpoint coverage
- [x] Scaffold [frontend](../frontend) as a Next.js App Router project
- [x] Add typed frontend API client for `POST /research` and status event URLs
- [x] Add research submission form, status stream view, report viewer, and source cards
- [x] Add frontend tests for API client, form submission, status rendering, and report rendering
- [x] Add backend CORS configuration for frontend origin access
- [x] Add [evals/eval_runner.py](../evals/eval_runner.py) offline benchmark runner
- [x] Score benchmark completion, source count, expected source overlap, source traceability, criteria coverage, and freshness
- [x] Add [tests/test_evals/test_eval_runner.py](../tests/test_evals/test_eval_runner.py) eval harness tests
- [x] Run first 3 benchmark prompts and persist [evals/results/eval_results_20260602T114237Z.json](../evals/results/eval_results_20260602T114237Z.json)
- [x] Add active source tracking to [backend/agent/memory.py](../backend/agent/memory.py)
- [x] Extend [backend/agent/planner.py](../backend/agent/planner.py) with configurable multi-source deterministic planning
- [x] Execute `finalize_report` through [backend/jobs/runner.py](../backend/jobs/runner.py)
- [x] Preserve OpenRouter `finalize_report` calls as executable tool calls in [backend/agent/openrouter.py](../backend/agent/openrouter.py)
- [x] Update [evals/eval_runner.py](../evals/eval_runner.py) to pass benchmark `min_sources` into orchestration
- [x] Run first 3 benchmark prompts and persist [evals/results/eval_results_20260602T121216Z.json](../evals/results/eval_results_20260602T121216Z.json)
- [x] Add search provider settings to [backend/config.py](../backend/config.py) and [.env.example](../.env.example)
- [x] Add stdlib-only Brave Search provider boundary in [backend/executor/search.py](../backend/executor/search.py)
- [x] Keep deterministic search as the default provider for dependency-free tests
- [x] Add `--mode offline|live` to [evals/eval_runner.py](../evals/eval_runner.py)
- [x] Label eval artifacts with mode and search provider
- [x] Run first 3 benchmark prompts in offline mode and persist [evals/results/eval_results_20260602T122647Z.json](../evals/results/eval_results_20260602T122647Z.json)

---

## EXIT CRITERIA

1. Deterministic search remains the default provider and requires no secrets or network
2. Brave Search provider can normalize live API results through an injectable, testable boundary
3. Eval CLI supports `--mode offline|live`
4. Eval artifacts include mode and search provider metadata
5. Backend regression suite, frontend lint, frontend tests, and frontend production build pass

---

## WHAT SHIPS IN THIS GATE

- Gate 1 foundation docs in `core/`
- Locked tool catalog in `backend/agent/tools.py`
- AgentSession model in `backend/agent/memory.py`
- FastAPI health spine
- CloakBrowser CDP health client
- `navigate_to_url` executor action
- Thin runner dispatch for the first tool
- Deterministic planner skeleton
- One-step planner-to-runner orchestration path
- Minimal `POST /research` API endpoint
- `extract_structured_data` executor skeleton
- `assess_credibility` executor skeleton
- Expanded runner dispatch surface
- Multi-step deterministic planner sequence
- Multi-step API response shape
- `web_search` executor skeleton with deterministic candidate generation
- Source candidate queue in `AgentSession`
- Runner dispatch and planner transitions for search-first URL-free goals
- OpenRouter planner adapter with injectable transport for tests
- Planner prompt templates built from session state, last tool result, and locked tool catalog
- Tool-call argument validation against `backend/agent/tools.py`
- Model usage accounting and cost-limit stop decisions
- Async planner support in `ResearchOrchestrator`
- Research report schema with claim-level `source_urls`
- Source-trace validation for every report source and finding
- Report synthesizer skeleton with deterministic fallback and fakeable model transport
- API synthesis serialization after sufficient coverage
- Research repository protocol
- In-memory repository for dependency-free API tests and local runs
- JSON-file repository that survives new repository instances
- Persisted job metadata and `GET /research/{job_id}` retrieval
- Status event model with stable `sequence`, `event_type`, `status`, `message`, `tool_name`, and `payload` fields
- Persisted `status_events[]` on `POST /research` and `GET /research/{job_id}` responses
- Replayable SSE endpoint at `GET /research/{job_id}/events`
- Next.js App Router frontend in `frontend/`
- Typed frontend API client using `NEXT_PUBLIC_API_URL`
- Research workbench with submission form, status stream, report viewer, and source cards
- Frontend Vitest setup and focused component/API tests
- Backend CORS settings through `CORS_ALLOWED_ORIGINS`
- Offline eval harness in [evals/eval_runner.py](../evals/eval_runner.py)
- Eval scoring for source coverage, expected-source overlap, source traceability, criteria coverage, and freshness
- Persisted v0.14 eval artifact in [evals/results/eval_results_20260602T114237Z.json](../evals/results/eval_results_20260602T114237Z.json)
- Focused eval harness tests in [tests/test_evals/test_eval_runner.py](../tests/test_evals/test_eval_runner.py)
- Active source tracking in `AgentSession`
- Configurable `min_sources` deterministic planner behavior
- First-class `finalize_report` execution through `ResearchRunner`
- Persisted v0.15 eval artifact in [evals/results/eval_results_20260602T121216Z.json](../evals/results/eval_results_20260602T121216Z.json)
- Search provider config: `SEARCH_PROVIDER`, `SEARCH_API_KEY`, and `SEARCH_API_URL`
- Brave Search provider adapter in [backend/executor/search.py](../backend/executor/search.py)
- Eval `--mode offline|live` CLI switch
- Persisted v0.16 eval artifact in [evals/results/eval_results_20260602T122647Z.json](../evals/results/eval_results_20260602T122647Z.json)

---

## WHAT DOES NOT SHIP IN THIS GATE

- No rich report formatting yet; v0.10 ships the structured skeleton only
- No real browser integration test yet; executor tests use fakes
- No live search smoke test yet; provider tests use injected HTTP responses
- No live OpenRouter integration test yet; adapter tests use fake transport
- No Postgres/Redis production persistence yet; v0.11 ships the repository boundary and JSON-file skeleton
- No background job queue yet; v0.12 streams persisted/replayable status events rather than live concurrent worker events
- No deployed frontend yet; v0.13 is local/dev frontend only
- No committed live eval artifact yet; v0.16 adds the mode and provider boundary, but the checked artifact remains offline/deterministic
- No live smoke test suite yet; v0.17 owns opt-in live provider/runtime validation
- No deployed frontend/backend yet; deployment remains planned after live smoke validation

---

## NEXT GATE

### v0.17.0 - Live Integration Smoke Tests

Add skipped-by-default live smoke tests for configured search, OpenRouter, and CloakBrowser paths.

---

**Last updated:** 2026-06-02
**Updated by:** GitHub Copilot
