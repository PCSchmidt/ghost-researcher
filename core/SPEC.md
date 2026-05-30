# SPEC.md

Blueprint v11 | Current Gate Specification  
Updated at the start of each gate

---

## CURRENT GATE

**Version:** v0.10.0
**Gate Name:** Synthesizer Skeleton
**Status:** DONE

---

## GOAL

Produce a structured report from extracted evidence without allowing unsupported
claims. The synthesizer uses deterministic fallback when no model transport is
configured and validates every cited claim against session evidence.

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

---

## EXIT CRITERIA

1. Report contains cited claims only
2. Unsupported claims fail validation
3. `synthesis` is returned from `POST /research` when sufficient evidence exists
4. Deterministic fallback works without live OpenRouter credentials
5. Current backend regression suite passes

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

---

## WHAT DOES NOT SHIP IN THIS GATE

- No frontend UI yet
- No rich report formatting yet; v0.10 ships the structured skeleton only
- No real browser integration test yet; executor tests use fakes
- No real search provider yet; `web_search` is a deterministic skeleton
- No live OpenRouter integration test yet; adapter tests use fake transport
- No persistence layer yet

---

## NEXT GATE

### v0.11.0 - Persistence and Job State

Persist research jobs, step events, sources, and synthesized reports.

---

**Last updated:** 2026-05-30
**Updated by:** GitHub Copilot
