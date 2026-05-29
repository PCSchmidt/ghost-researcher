# SPEC.md

Blueprint v11 | Current Gate Specification  
Updated at the start of each gate

---

## CURRENT GATE

**Version:** v0.7.0  
**Gate Name:** Multi-Step Planner Skeleton  
**Status:** DONE

---

## GOAL

Extend deterministic orchestration from one action to a fixed sequence:
`navigate_to_url -> extract_structured_data -> assess_credibility`, still without
synthesis or persistence.

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

---

## EXIT CRITERIA

1. Planner selects the correct next tool based on session progress
2. Orchestrator executes navigation, extraction, and credibility with fake executors
3. Session records source, extraction summary, credibility result, and final status
4. API returns `decisions[]`, `tool_results[]`, session state, and `synthesis: null`
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

---

## WHAT DOES NOT SHIP IN THIS GATE

- No OpenRouter planner adapter yet
- No frontend UI yet
- No report synthesis code yet
- No real browser integration test yet; executor tests use fakes
- No persistence layer yet

---

## NEXT GATE

### v0.8.0 - Search Tool Skeleton

Add the missing `web_search` executor path so research goals without URLs can
start, then feed search results into the deterministic navigation path.

---

**Last updated:** 2026-05-29
**Updated by:** GitHub Copilot
