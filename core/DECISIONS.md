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

## DEC-008: Shareable report output splits link sharing from file export

Status: ACCEPTED (planned, deferred to v1.3.0)
Date: 2026-06-08
Decision: Shareable report output is a planned, deferred stage ([v1.3.0](./VERSION_ROADMAP.md)) with two distinct mechanisms: (1) link sharing via a stable `/reports/[id]` permalink plus OpenGraph/Twitter Card metadata for social/chat previews, and (2) file sharing via a downloadable PDF plus print-optimized CSS for email, save, and print. The PDF engine, server-vs-client generation, OG image strategy, and public-access model are deferred sub-decisions to be resolved at stage start.
Alternatives considered: A single "export to PDF" feature treated as the whole of sharing; client-only print-to-PDF with no permalink; building it now versus deferring after live validation.
Reason: Social platforms render a shared link's preview card, not an attached PDF, so "share to social media" and "share a PDF" are different features and were scoped separately to avoid a half-built experience. The work is sequenced after v1.2.0 live validation because a shareable artifact is only worth publishing once live report quality is validated. The report content is currently a schema skeleton, so a synthesis-formatting upgrade is a noted prerequisite.

## DEC-009: CloakBrowser is the stealth browser layer; integrate it in phases

Status: ACCEPTED (planned, v1.2.1)
Date: 2026-06-08
Decision: GhostResearcher will use the CloakBrowser library (pip `cloakbrowser`; the namesake of the project) as its real anti-detection browser layer, replacing the vanilla headless Chromium that `cloakserve` currently launches. Integration is phased: Phase 1 swaps `cloakserve` to launch CloakBrowser's patched stealth binary over CDP (minimal executor change, keeps the two-service topology, fast production unblock); Phase 2 migrates the executor to in-process `launch_context_async` for per-source fingerprint variation (honoring the currently-stubbed `fingerprint_seed`), per-source proxy rotation, geoip, and human input emulation.
Alternatives considered: going straight to in-process launch (bigger refactor, heavier API image, drops the separate service); server swap only (no per-source stealth depth); keeping the hand-rolled vanilla launcher (status quo — production reports come back empty due to Cloudflare blocking).
Reason: The "ghost" premise depends on defeating bot detection, and the deployed browser does not — `fingerprint_seed` is discarded, `PROXY_*` is unused, and headless Chromium from a Railway datacenter IP is trivially blocked. CloakBrowser already provides the stealth (patched binary, fingerprint flags, proxy/geoip/WebRTC, humanize) and ships its own CDP `serve` mode, so the server swap is small and reversible. Phasing unblocks production fast, then deepens. CloakBrowser stays an upstream pinned dependency, not vendored.

## DEC-010: Residential proxy is measurement-gated, not assumed

Status: ACCEPTED (planned, v1.2.1)
Date: 2026-06-08
Decision: Wire the proxy path (`--proxy-server` / `launch(proxy=...)`) during CloakBrowser integration but do not provision a paid residential/mobile proxy until measurement shows it is needed. Integrate the stealth binary, run live evals from Railway, measure the blocked-source rate, and only sign up for a residential proxy if Cloudflare still blocks at a material rate.
Alternatives considered: provisioning a residential proxy upfront (guaranteed cost before evidence it is needed); never using a proxy (accepts blocking on aggressive IP/ASN-based sites).
Reason: The stealth binary fixes the browser fingerprint, which defeats much detection, but Cloudflare also weighs IP/ASN reputation, so a datacenter IP may still be challenged. The discriminative eval (blocked-source rate, live `quality_score`) is the instrument to decide with data instead of paying for proxy egress speculatively.

Resolution (2026-06-09): measured. On the Railway datacenter IP the CloakBrowser stealth binary brought the block rate from ~100% to 37.5% (62.5% of hard targets usable), and a production research run produced a 0.68-confidence report with 5 cited findings from 7 sources. Decision: **option 1 — no proxy for now**, since report quality at 62.5% coverage is already useful. The remaining blocks are IP/ASN-driven, so when/if coverage proves insufficient the targeted fix is **option 3 — proxy-on-retry** (route only `detection_blocked` pages through a residential proxy), specced as an optional v1.2.1 Phase 2 item rather than a blanket all-traffic residential proxy (option 2, most expensive).
