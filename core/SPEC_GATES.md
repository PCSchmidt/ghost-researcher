# SPEC_GATES.md

Blueprint v11 | Gate Plan

This is the compact gate checklist. Use [VERSION_ROADMAP.md](./VERSION_ROADMAP.md)
for detailed stage descriptions and [SPEC.md](./SPEC.md) for the current active
stage.

---

## Stage Sequence

### v0.1.0 - Foundation + Agent Contract

- Exit artifacts: [CONTRACT.md](./CONTRACT.md), [AGENT_SPEC.md](./AGENT_SPEC.md), memory files, [ERRORS.md](./ERRORS.md), [benchmark_prompts.json](../evals/benchmark_prompts.json)
- Exit token: `CONFIRMED`
- Status: Complete

### v0.2.0 - Tool Interface Lock

- Exit artifacts: [backend/agent/tools.py](../backend/agent/tools.py), tool schema tests
- Exit token: `TOOLS CONFIRMED`
- Status: Complete

### v0.3.0 - First Executor Action

- Exit artifacts: browser health client, `navigate_to_url`, runner dispatch, executor tests
- Exit token: `TESTS CONFIRMED`
- Status: Complete

### v0.4.0 - Planner Integration Skeleton

- Exit artifacts: deterministic planner and planner-to-runner orchestration
- Exit token: `PLANNER SKELETON CONFIRMED`
- Status: Complete

### v0.5.0 - API Research Endpoint Skeleton

- Exit artifacts: `POST /research` endpoint and route tests
- Exit token: `API SKELETON CONFIRMED`
- Status: Complete

### v0.6.0 - Extract and Credibility Skeletons

- Exit artifacts: `extract_structured_data`, `assess_credibility`, expanded runner dispatch
- Exit token: `EXECUTOR TOOLS CONFIRMED`
- Status: Complete

### v0.7.0 - Multi-Step Planner Skeleton

- Exit artifacts: fixed sequence `navigate_to_url -> extract_structured_data -> assess_credibility`
- Exit token: `SEQUENCE CONFIRMED`
- Status: Complete

### v0.8.0 - Search Tool Skeleton

- Exit artifacts: `web_search` executor path, runner dispatch, URL-free goal fallback
- Exit token: `SEARCH CONFIRMED`
- Status: Next

### v0.9.0 - OpenRouter Planner Adapter

- Exit artifacts: OpenRouter adapter, prompt templates, tool-call validation, cost checks
- Exit token: `MODEL PLANNER CONFIRMED`
- Status: Planned

### v0.10.0 - Synthesizer Skeleton

- Exit artifacts: report schema, synthesizer adapter, claim-source validation
- Exit token: `SYNTHESIS CONFIRMED`
- Status: Planned

### v0.11.0 - Persistence and Job State

- Exit artifacts: Postgres schema, Redis queue, persisted job/report/source logs
- Exit token: `PERSISTENCE CONFIRMED`
- Status: Planned

### v0.12.0 - Live Status Stream

- Exit artifacts: SSE endpoint and job status event model
- Exit token: `STATUS STREAM CONFIRMED`
- Status: Planned

### v0.13.0 - Frontend Research UI

- Exit artifacts: Next.js research form, job status stream view, report viewer, source cards
- Exit token: `FRONTEND CONFIRMED`
- Status: Planned

### v0.14.0 - Evals Harness

- Exit artifacts: eval runner, benchmark scoring, results artifacts
- Exit token: `EVALS CONFIRMED`
- Status: Planned

### v1.0.0 - Deployment

- Exit artifacts: Railway backend/cloakserve, Vercel frontend, healthy production endpoints
- Exit token: `DEPLOY CONFIRMED`
- Status: Planned
