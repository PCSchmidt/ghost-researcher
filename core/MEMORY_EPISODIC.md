# MEMORY_EPISODIC.md

Blueprint v11 | Session Log and Gate Outcomes

Appended by writethru-episodic hook on Stop events.
Updated at gate close with gate outcome rows.

## SESSION LOG

| Date | Project | Gate | Outcome | Tests | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-05-28 | GhostResearcher | v0.1.0 | IN PROGRESS | n/a | Reconstructed repo from prototype docs and created missing Gate 1 artifacts |
| 2026-05-29 | GhostResearcher | Gate 1 | CONFIRMED | 41 passing | Cost ceilings locked; AGENT_SPEC critical review completed; OpenRouter-first model routing accepted |
| 2026-05-30 | GhostResearcher | v0.8.0 | COMPLETE | 48 passing | Added deterministic web_search skeleton, queued source candidates, and search-first URL-free sequence |
| 2026-05-30 | GhostResearcher | v0.9.0 | COMPLETE | 54 passing | Added fake-tested OpenRouter planner adapter, prompt templates, validation, and model usage accounting |
| 2026-05-30 | GhostResearcher | v0.10.0 | COMPLETE | 63 passing | Added report schema, source-trace validation, synthesizer skeleton, and API synthesis serialization |
| 2026-06-01 | GhostResearcher | v0.11.0 | COMPLETE | 68 passing | Added research repository boundary, job IDs, JSON-file durability, and `GET /research/{job_id}` |
| 2026-06-01 | GhostResearcher | v0.12.0 | COMPLETE | 73 passing | Added persisted status events and `GET /research/{job_id}/events` SSE stream |
| 2026-06-01 | GhostResearcher | v0.13.0 | COMPLETE | 73 backend, 8 frontend | Added Next.js research workbench, EventSource status view, report/source cards, and CORS settings |
| 2026-06-02 | GhostResearcher | v0.14.0 | COMPLETE | 77 backend, 8 frontend | Added offline eval runner, benchmark scoring, source-trace checks, and persisted 3-prompt eval artifact |
| 2026-06-02 | GhostResearcher | v0.15.0 | COMPLETE | 80 backend, 8 frontend | Added multi-source deterministic planning, executable `finalize_report`, and 3-prompt eval artifact with source counts met |
| 2026-06-02 | GhostResearcher | v0.16.0 | COMPLETE | 85 backend, 8 frontend | Added search provider boundary, Brave adapter, eval `--mode offline|live`, and mode-labeled eval artifact |
| 2026-06-02 | GhostResearcher | v0.17.0 | COMPLETE | 90 backend OK, 8 frontend | Added skipped-by-default live smoke tests for Brave Search, OpenRouter planner/synthesizer, and CloakBrowser health/navigation |
| 2026-06-03 | GhostResearcher | v1.0.0 | COMPLETE | 89 backend, 8 frontend | Deployed backend to Railway (ghostresearcher-api + cloakserve) and frontend to Vercel; RAILWAY_REQUEST_TIMEOUT=300 set |
| 2026-06-04 | GhostResearcher | v1.0.1 | COMPLETE | 89 backend, 8 frontend | Fixed CDP Host header rewriting, DNS-rebinding bypass, HTTP readiness polling, wait_for guard, synthesis gate removal, evidence auto-creation |
| 2026-06-05 | GhostResearcher | v1.1.0 | COMPLETE | 89 backend, 8 frontend | Deep research operational: Brave Search, rich planner prompt, evidence from navigate results, LLM synthesis — full report rendered in frontend |
| 2026-06-08 | GhostResearcher | v1.2.0 | IN PROGRESS | 105 backend, 11 frontend | Reviewed 3 Codex branches (sound, on-plan); fixed compose/deploy Dockerfile refs; made offline eval discriminate via integrity/quality split (was tautological flat 1.0); surfaced bp_004/bp_007 as under-specified |

## STOP EVENTS

[Appended automatically by writethru-episodic hook]
