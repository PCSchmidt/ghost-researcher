# DECISIONS.md

Blueprint v11 | Locked Architectural Decisions

## DEC-001: Separate runtime from SkySigint

Status: ACCEPTED
Date: 2026-05-28
Decision: GhostResearcher owns its own repository, CloakBrowser service, and deployment lifecycle.
Reason: The project has a different workload shape and should not share runtime fate with SkySigint.

## DEC-002: LLM plans, executor executes

Status: ACCEPTED
Date: 2026-05-28
Decision: The planner model is limited to tool selection and orchestration. Browser control lives entirely behind executor tools.
Reason: This keeps the browser layer testable and prevents prompt logic from owning transport details.

## DEC-003: `finalize_report` is a tool

Status: ACCEPTED
Date: 2026-05-28
Decision: The planner signals completion by calling `finalize_report`, not by ending the conversation implicitly.
Reason: The runner needs an explicit handoff point to start synthesis and log termination reason.

## DEC-004: Evals are part of the product, not backlog

Status: ACCEPTED
Date: 2026-05-28
Decision: `evals/benchmark_prompts.json` is a first-class artifact from Gate 1 onward.
Reason: The portfolio value depends on proving agent quality, not just claiming it.

## DEC-005: Credibility scoring is explicit

Status: ACCEPTED
Date: 2026-05-28
Decision: Credibility is represented as structured features and a numeric score, not an informal heuristic note.
Reason: Report confidence needs a defensible basis and a later evaluation hook.

## DEC-006: SSE is the default status transport

Status: ACCEPTED
Date: 2026-05-28
Decision: The frontend receives job status by Server-Sent Events by default. Polling is fallback-only.
Reason: Polling was identified as a scaling failure mode in the design notes.

## DEC-007: OpenRouter is the default model gateway

Status: ACCEPTED
Date: 2026-05-29
Decision: GhostResearcher will use OpenRouter as the default gateway for planner and synthesizer model calls. Cheaper capable models such as DeepSeek, Qwen, and Kimi are the default route; Anthropic is kept as an explicit premium fallback.
Alternatives considered: Direct Anthropic-only integration; direct provider-specific integrations for each low-cost model; OpenRouter plus optional fallback routing.
Critical review: The approach is cost-efficient and reversible because the planner contract remains provider-neutral. The main risk is inconsistent tool-call and structured-output behavior across models. Mitigation is strict schema validation, cost tracking from provider usage metadata, and fallback escalation only after validation failure.
Reason: The project scope needs reliable tool selection and synthesis, not the highest-cost frontier model for every call. OpenRouter gives model choice, usage metadata, and fallback routing while preserving one API surface.
