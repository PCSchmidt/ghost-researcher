# SPEC.md

Blueprint v11 | Current Gate Specification  
Updated at the start of each gate

---

## CURRENT GATE

**Version:** v0.8.0
**Gate Name:** Search Tool Skeleton
**Status:** DONE

---

## GOAL

Add the missing `web_search` executor path so research goals without URLs can
start with candidate source discovery, then feed the first novel search result
into the deterministic navigation, extraction, and credibility sequence.

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

---

## EXIT CRITERIA

1. URL-free research goal produces `web_search`
2. Search results feed the next navigation step
3. Tests cover empty, duplicate, and new-result cases
4. Orchestrator executes `web_search -> navigate_to_url -> extract_structured_data -> assess_credibility`
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

---

## WHAT DOES NOT SHIP IN THIS GATE

- No OpenRouter planner adapter yet
- No frontend UI yet
- No report synthesis code yet
- No real browser integration test yet; executor tests use fakes
- No real search provider yet; `web_search` is a deterministic skeleton
- No persistence layer yet

---

## NEXT GATE

### v0.9.0 - OpenRouter Planner Adapter

Replace deterministic planning with an OpenRouter-backed adapter while preserving
the same tool-call contract and budget guardrails.

---

**Last updated:** 2026-05-30
**Updated by:** GitHub Copilot
