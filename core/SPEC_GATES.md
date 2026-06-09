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

- Exit artifacts: `web_search` executor path, runner dispatch, URL-free goal fallback, source candidate queue
- Exit token: `SEARCH CONFIRMED`
- Status: Complete

### v0.9.0 - OpenRouter Planner Adapter

- Exit artifacts: OpenRouter adapter, prompt templates, tool-call validation, cost checks
- Exit token: `MODEL PLANNER CONFIRMED`
- Status: Complete

### v0.10.0 - Synthesizer Skeleton

- Exit artifacts: report schema, synthesizer adapter, claim-source validation, API synthesis serialization
- Exit token: `SYNTHESIS CONFIRMED`
- Status: Complete

### v0.11.0 - Persistence and Job State

- Exit artifacts: repository boundary, persisted job payloads, `GET /research/{job_id}`, restart durability test
- Exit token: `PERSISTENCE CONFIRMED`
- Status: Complete

### v0.12.0 - Live Status Stream

- Exit artifacts: SSE endpoint and job status event model
- Exit token: `STATUS STREAM CONFIRMED`
- Status: Complete

### v0.13.0 - Frontend Research UI

- Exit artifacts: Next.js research form, job status stream view, report viewer, source cards
- Exit token: `FRONTEND CONFIRMED`
- Status: Complete

### v0.14.0 - Evals Harness

- Exit artifacts: eval runner, benchmark scoring, results artifacts
- Exit token: `EVALS CONFIRMED`
- Status: Complete

### v0.15.0 - Live Capability Alignment

- Exit artifacts: multi-source deterministic planner flow, executable `finalize_report`, improved offline eval artifact
- Exit token: `LIVE CAPABILITY ALIGNMENT CONFIRMED`
- Status: Complete

### v0.16.0 - Real Search and Live Evals

- Exit artifacts: real search provider boundary, opt-in live eval mode, mode-labeled offline eval artifact
- Exit token: `LIVE SEARCH CONFIRMED`
- Status: Complete

### v0.17.0 - Live Integration Smoke Tests

- Exit artifacts: skipped-by-default live smoke tests for search provider, OpenRouter, and CloakBrowser path
- Exit token: `LIVE SMOKE CONFIRMED`
- Status: Complete

### v1.0.0 - Deployment

- Exit artifacts: Railway backend/cloakserve, Vercel frontend, healthy production endpoints
- Exit token: `DEPLOY CONFIRMED`
- Status: Complete

### v1.0.1 - CDP Stability Fixes

- Exit artifacts: Host header rewrite, DNS-rebinding bypass, HTTP readiness polling, wait_for guard, synthesis gate removal
- Exit token: `CDP STABLE CONFIRMED`
- Status: Complete

### v1.1.0 - Deep Research Operational

- Exit artifacts: Brave Search live, evidence from navigate results, LLM synthesis with cited findings, frontend report render confirmed
- Exit token: `DEEP RESEARCH CONFIRMED`
- Status: Complete

### v1.1.1 - Evidence Flow Stabilization

- Exit artifacts: evidence provenance markers, assessed-coverage gating, premature-finalize guard, source-card credibility
- Exit token: `EVIDENCE FLOW CONFIRMED`
- Status: Complete

### v1.2.0 - Evidence Quality and Live Validation

- Exit artifacts: deeper extraction + hard-page diagnostics, claim-overlap corroboration, live eval readiness probe, discriminative eval scoring (integrity/quality split), configured live validation run
- Exit token: `LIVE VALIDATION CONFIRMED`
- Status: In progress (configured live run pending)

### v1.2.1 - Ghost: CloakBrowser Anti-Detection Integration

- Exit artifacts: Phase 1 — cloakserve runs CloakBrowser's patched stealth binary, blocked-source-rate metric, measurable drop in `detection_blocked`; Phase 2 — in-process `launch_context_async`, `fingerprint_seed` honored, per-source proxy rotation
- Exit token: `GHOST STEALTH CONFIRMED`
- Status: Planned (immediate priority after v1.2.0). Phased; proxy measurement-gated (DEC-009, DEC-010)

### v1.3.0 - Shareable Report Output (Deferred)

- Exit artifacts: `/reports/[id]` permalink + `/reports` list, OG/Twitter preview, print CSS, server-rendered PDF export, share/download affordances
- Exit token: `SHAREABLE OUTPUT CONFIRMED`
- Status: Planned / Deferred (after v1.2.0). PDF layout expected to need visual iteration.
