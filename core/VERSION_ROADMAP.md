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

Current stage: v1.1.1 - Evidence Flow Stabilization

Recently completed:

- v0.1.0 through v0.17.0 (see entries below)
- v1.0.0 deployment to Railway + Vercel
- v1.0.1 CDP proxy fixes
- v1.1.0 deep research quality (Brave Search, rich prompt, evidence pipeline, LLM synthesis)
- v1.1.1 evidence flow stabilization (fallback evidence provenance, assessed coverage gating, source-card credibility)

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

- Next.js App Router frontend in `frontend/`
- Research submission form
- Job status stream view backed by `EventSource`
- Source and credibility display
- Report viewer and placeholder state until synthesis is complete
- Frontend lint, component tests, API client tests, and production build validation
- Backend CORS origin settings for local frontend/API development

Exit criteria:

- User can submit a goal from the browser and receive a persisted research job
- UI renders status events, source cards, credibility scores, and synthesized reports
- Frontend lint, tests, and production build pass
- Backend accepts configured frontend origins through CORS

Status: Complete.

---

## v0.14.0 - Evals Harness

Goal: Turn benchmark prompts into repeatable quality checks.

Ships:

- `evals/eval_runner.py`
- Deterministic offline benchmark execution against `evals/benchmark_prompts.json`
- Scoring outputs in `evals/results/`
- Report quality, expected source overlap, benchmark criteria coverage, freshness, and source traceability checks
- Focused eval harness tests

Exit criteria:

- At least 3 benchmark prompts run end to end
- Results are persisted as eval artifacts

Status: Complete. v0.14 artifact: `evals/results/eval_results_20260602T114237Z.json`.

---

## v0.15.0 - Live Capability Alignment

Goal: Close the biggest alignment gap before live integrations by making the deterministic agent loop collect multiple sources and execute `finalize_report` as a real tool.

Ships:

- Multi-source deterministic planning with configurable `min_sources`
- Active source tracking in `AgentSession`
- `finalize_report` execution in `ResearchRunner`
- OpenRouter adapter preserves `finalize_report` as a tool call for runner execution
- Offline eval runner passes benchmark minimum source counts for the first 3 prompts
- Updated tests for planner, runner, orchestrator, OpenRouter adapter, and eval harness

Exit criteria:

- Deterministic URL-free benchmark runs can assess multiple sources before synthesis
- `finalize_report` returns accepted/queued status and finalizes session state
- Backend regression suite passes
- Updated eval artifact is persisted under `evals/results/`

Status: Complete. v0.15 artifact: `evals/results/eval_results_20260602T121216Z.json`.

---

## v0.16.0 - Real Search and Live Evals

Goal: Replace deterministic-only source discovery with a configurable real search provider path and add opt-in live eval execution.

Ships:

- Search provider abstraction with deterministic provider retained for tests
- Brave Search provider integration behind `SEARCH_PROVIDER=brave` and `SEARCH_API_KEY`
- `evals/eval_runner.py --mode offline|live`
- Eval artifacts labeled with mode and search provider
- Dependency-free tests for provider selection, Brave response normalization, and eval mode behavior

Exit criteria:

- Offline tests remain dependency-free
- Live mode can run at least 3 benchmark prompts with real search candidates when env vars are configured
- Eval artifacts clearly label offline vs live mode and provider configuration

Status: Complete. v0.16 artifact: `evals/results/eval_results_20260602T122647Z.json`.

---

## v0.17.0 - Live Integration Smoke Tests

Goal: Add opt-in smoke tests that exercise the configured live provider/runtime path without making CI or local regression tests depend on secrets or external services.

Ships:

- Skipped-by-default Brave Search smoke test gated by `SEARCH_PROVIDER=brave` and `SEARCH_API_KEY`
- Skipped-by-default OpenRouter planner/synthesizer smoke tests gated by `OPENROUTER_API_KEY`
- Skipped-by-default CloakBrowser navigation smoke test gated by `CLOAK_CDP_URL` and an explicit live-test flag
- Documentation for running live smoke tests and interpreting failures

Exit criteria:

- Default backend suite remains dependency-free
- Live smoke tests are discoverable and skipped clearly when env vars are absent
- At least one configured live search smoke test can return normalized candidate sources

Status: Complete. The smoke suite lives in [tests/test_live/test_smoke.py](../tests/test_live/test_smoke.py) and skips by default unless `GHOSTRESEARCHER_RUN_LIVE_TESTS=1` is set.

---

## v1.0.0 - Deployment

Goal: Deploy backend and frontend with health checks and rollback path.

Ships:

- Railway backend deployment (Prep complete)
- Railway CloakBrowser service (Prep complete)
- Vercel frontend deployment (Prep complete)
- Environment configuration docs (docs/DEPLOYMENT.md)

Exit criteria:

- `/health` returns healthy dependency status
- `POST /research` works against deployed backend
- Frontend can run a demo research job

Status: Historical prep complete. Superseded by the completed deployment entry below.

---

## v1.0.0 - Deployment

Goal: Deploy backend and frontend with health checks and rollback path.

Ships:

- Railway backend deployment (ghostresearcher-api)
- Railway CloakBrowser service (cloakserve)
- Vercel frontend deployment
- Environment configuration docs (docs/DEPLOYMENT.md)
- `RAILWAY_REQUEST_TIMEOUT=300` for long research runs

Exit criteria:

- `/health` returns healthy dependency status
- `POST /research` works against deployed backend
- Frontend can run a demo research job

Status: Complete. Backend on Railway, frontend on Vercel. Deployed June 2026.

---

## v1.0.1 - CDP Stability Fixes

Goal: Fix CloakBrowser connectivity issues discovered after first deployment.

Ships:

- CDP WebSocket Host header rewriting (Railway internal DNS)
- DNS-rebinding protection bypass
- HTTP readiness polling before CDP connect
- `wait_for` selector guard in navigate_to_url
- Post-loop evidence auto-creation
- Synthesis gate removal (synthesize whenever evidence exists)

Exit criteria:

- CDP connects reliably on Railway internal network
- Research runs complete without CDP connection errors

Status: Complete.

---

## v1.1.0 - Deep Research Operational

Goal: Deliver a working end-to-end pipeline with real sources, evidence, and LLM synthesis.

Ships:

- Brave Search enabled on Railway (`SEARCH_PROVIDER=brave`)
- Raised budgets: `MAX_TOKENS_PER_JOB=125000`, `MAX_MODEL_COST_PER_JOB_USD=0.15`
- Rich planner system prompt with full research methodology
- OpenRouter adapter retry when model returns text instead of tool call
- Page sharing fix: navigate keeps page open, extract reuses `context.pages[-1]`
- Extract Chrome Incognito banner stripping and HTML fallback
- Evidence created directly from navigate_to_url results (title + content_excerpt)
- Synthesis triggered on any termination reason when evidence exists

Exit criteria:

- Planner navigates 8+ real sources per run
- Synthesis produces structured report with 4+ cited findings
- Frontend renders full report and source cards
- 89 backend tests pass, 5 skipped

Status: Complete. Confirmed working June 5, 2026.

---

## v1.1.1 - Evidence Flow Stabilization

Goal: Prevent navigation-created fallback evidence from satisfying coverage before extraction and credibility assessment.

Ships:

- Evidence provenance markers: `navigation_fallback`, `extracted`, and `assessed`
- Planner coverage rules count only assessed evidence toward `sufficient_coverage`
- Orchestrator guard reroutes premature `finalize_report` calls into extraction or credibility when possible
- Synthesizer prefers assessed evidence and deduplicates to one best record per source
- Frontend source cards read credibility from session evidence records
- Extraction regression fix so normal `document.body.innerText` records are preserved

Exit criteria:

- Normal source path is `navigate_to_url -> extract_structured_data -> assess_credibility -> finalize_report`
- Navigation fallback evidence remains available for synthesis resilience but does not complete coverage
- Backend and frontend checks pass

Status: Complete locally. Ready for live validation and deployment.

---

## v1.2.0 - Evidence Quality and Live Validation

Goal: Improve evidence depth and validate the stabilized live planner path under configured production-like services.

Ships:

- Configured live run or live eval artifact confirming extract and credibility behavior
- Richer extraction strategy for requested selectors plus article/main/content regions
- Navigation diagnostics for PDF, paywall, blocked, and thin-SPA pages
- Metadata and hard-page limitation records from extraction
- Evidence quality metrics in API/session/status payloads
- Stronger credibility/corroboration signals across source-diverse, claim-overlapping, and previously extracted evidence
- Production-facing monitoring for model cost, CDP failures, and blocked-source rates
- Discriminative eval scoring: offline harness split into `integrity_score`
  (regression gate) and `quality_score` (sub-1.0, rewards source breadth and real
  assessed credibility); offline labeled `harness_kind=regression`, live labeled
  `harness_kind=quality`; navigation/extraction fixtures decoupled from the scorer
  so evidence-flow regressions are visible. Artifact: `evals/results/eval_results_20260609T004059Z.json`

Status: In progress. Local extraction, corroboration, offline sequence validation,
live eval readiness probing, and discriminative eval scoring are complete;
configured live validation remains pending because this shell lacks live network
access.

Eval finding (2026-06-08): the discriminative scorer surfaced that benchmark
prompts `bp_004` and `bp_007` specify `min_sources=4` but list only 3
`expected_sources`, so they can never reach `sufficient_coverage` offline
(integrity 0.5). Decide whether to raise their expected source lists or lower
`min_sources` before treating offline as an all-green regression baseline.

---

## v1.2.1 - Ghost: CloakBrowser Anti-Detection Integration

Goal: Make CloakBrowser's stealth the actual browser layer so production research
returns real extracted content from protected (Cloudflare / Turnstile / DataDome)
sites. This is the "ghost" premise of the project and the current top
report-quality blocker.

Status: Planned. Immediate priority after v1.2.0 live validation. Phased. See
[DEC-009](./DECISIONS.md) and [DEC-010](./DECISIONS.md).

### Finding that motivates this stage

The deployed `cloakserve` launches **vanilla headless Chromium** with only
`--disable-blink-features=AutomationControlled`
([backend/scripts/start_cloakserve.py](../backend/scripts/start_cloakserve.py)).
`fingerprint_seed` is discarded (`del fingerprint_seed` in
[backend/executor/navigate.py](../backend/executor/navigate.py)), and the
`PROXY_*` settings are never used by the executor. In production, research reports
come back empty (0% confidence) because Cloudflare blocks the datacenter-IP
headless browser on every source. The project's namesake library, **CloakBrowser**
(pip `cloakbrowser`; clone at
`C:\Users\pchri\Documents\AIEngineeringProjects\CloakBrowser`), provides the real
stealth that was never wired in: a patched Chromium binary, `--fingerprint-*`
flags (not detectable CDP emulation), HTTP/SOCKS5 proxy with geoip-matched
timezone/locale and WebRTC IP spoofing, human input emulation, and an optional
`patchright` backend.

### Phase 1 - Stealth server swap (fast unblock, minimal change)

Ships:

- Add `cloakbrowser[serve,geoip]` as a dependency of the cloakserve service
- Replace the vanilla Chromium launch in `start_cloakserve.py` with CloakBrowser's
  patched stealth binary exposed over CDP (reuse CloakBrowser's `serve` mode, or
  launch `ensure_binary()` with stealth args), keeping the existing Host-header /
  DNS-rebinding shim that makes Railway internal networking work
- Update [docker/Dockerfile.cloak](../docker/Dockerfile.cloak) to install
  `cloakbrowser`, pre-download the binary at build (`ensure_binary()`), and add the
  required system deps + xvfb (CloakBrowser's own Dockerfile is the reference)
- Wire optional `--proxy-server` from `PROXY_URL`/`PROXY_USER`/`PROXY_PASS` into the
  launch (off by default; ready for the proxy decision)
- Add a blocked-source-rate metric to live eval and status payloads to instrument
  the measurement
- Executor unchanged (still connects over CDP)

Exit criteria:

- cloakserve runs the CloakBrowser patched binary; `/json/version` healthy
- A live eval / production run shows a measurable drop in `detection_blocked` rate
  vs the vanilla baseline (capture before/after numbers)
- Backend suite green; no executor regressions

Phase 1 status (2026-06-09): implemented and locally validated.
[start_cloakserve.py](../backend/scripts/start_cloakserve.py) now launches
CloakBrowser's patched binary (`CLOAKSERVE_STEALTH=1`, the default) and keeps the
vanilla path under `CLOAKSERVE_STEALTH=0` for the baseline.
[Dockerfile.cloak](../docker/Dockerfile.cloak) installs `cloakbrowser` and
pre-downloads the binary at build. The CDP `/json/version` UA changed from
`HeadlessChrome/130` to `Chrome/146` (no "Headless" tell). The executor drives the
stealth browser over CDP end to end, and the new
[evals/blocked_rate.py](../evals/blocked_rate.py) harness scored block_rate 0.0 on
the exact production-failing targets from a residential IP.

Deployed and measured on Railway (2026-06-09, merge 47ac653): the CloakBrowser
service now serves `Chrome/146` (was `HeadlessChrome`). The decisive datacenter-IP
`blocked_rate` run (via `railway ssh` on `ghost-researcher`) went from ~100% blocked
(the documented empty 0%-confidence reports) to **block_rate 0.375 / usable_rate
0.625** — 5 of 8 previously-blocked targets now return usable content
(energy.gov, pewresearch, belfercenter, goldmansachs, coresite). Loop closed: a
production research run (via the deployed API) on the topic that previously returned
an empty 0%-confidence report now returns a **0.68-confidence report with 5 cited
findings from 7 sources**. **Phase 1 DONE.** The 3 still blocked (iea.org,
bloomenergy, datacenterknowledge) are IP/ASN-driven (good fingerprint, datacenter
IP), which is the residential-proxy decision point under DEC-010 — deferred (option 1,
no proxy) because 62.5% coverage already yields usable reports.

### Phase 2 - In-process launch (per-source stealth depth)

Ships:

- Add `cloakbrowser` to the API service; container pre-downloads the binary
- Replace `_default_page_context` in navigate.py and extract.py with
  `cloakbrowser.launch_context_async(...)` (or a shared CloakBrowser session
  manager): honor `fingerprint_seed` (remove the `del`), enable per-source proxy
  rotation, geoip timezone/locale match, WebRTC IP spoofing, and optional
  `humanize`
- Decide cloakserve's fate (retire the separate service, or keep for parallelism)
- Optional persistent context for cookie/session reuse across steps to reduce
  repeat challenges
- Optional (cost-capping) **proxy-on-retry**: navigate normally on the datacenter IP;
  only when a page returns `detection_blocked`, retry that single page through a
  residential/mobile proxy (`launch(proxy=...)` / `--proxy-server`). This targets the
  ~37.5% IP/ASN-blocked sites without paying residential-proxy bandwidth for every
  page. `detection_blocked` is already surfaced by the executor, so the retry hook is
  small. Gated by DEC-010 (only build if 62.5% coverage proves insufficient).

Exit criteria:

- `fingerprint_seed` actually varies the browser fingerprint per source
- Per-source proxy assignment works
- Blocked-source rate and live `quality_score` improve on protected targets

### Decisions to resolve at stage start

- cloakserve launch method: reuse CloakBrowser `serve` CLI vs adapt
  `start_cloakserve.py` to launch the patched binary + stealth args + keep the
  Host-rewrite shim
- `patchright` vs `playwright` backend (default `playwright` — we need proxy auth,
  which patchright breaks)
- Headless vs headed+xvfb (some WebGL/GPU stealth wants headed+xvfb per
  CloakBrowser's Dockerfile) — decide from detection results
- Image size / build-time budget for the patched binary + system deps on Railway
- BINARY-LICENSE.md terms for deployment use

Dependency: CloakBrowser is upstream (pip `cloakbrowser`, clone at the
AIEngineeringProjects path). Pin a version; do not vendor its source.

---

## v1.3.0 - Shareable Report Output (Deferred)

Goal: Turn a completed research report from an ephemeral in-app web view into a
durable, shareable artifact — linkable, embeddable on social platforms, and
exportable to a clean PDF for email, saving, and printing.

Status: Planned / Deferred. Sequenced after v1.2.0 live validation. Not started.
See [DEC-008](./DECISIONS.md) for the architecture decision.

### Two sharing modes (deliberately distinct)

These are different mechanisms and must not be conflated:

- Link sharing (social media, chat apps, "send someone the report"): a stable
  public permalink plus OpenGraph/Twitter Card metadata so the link unfurls into a
  preview card. Social platforms render the *link*, not a PDF file — you cannot
  "post a PDF" to X/LinkedIn and have it preview.
- File sharing (email attachment, local save, print): a downloadable, self-contained
  PDF plus a print-optimized stylesheet so the browser "Save as PDF" path also
  produces a clean document.

### Prerequisite

Report content is currently a schema skeleton (`title`, `summary`,
`key_findings[]`, `sources_used[]`, `confidence`, `limitations[]`) with no length
or structure contract. A PDF will expose that thinness. Either upgrade the
synthesis prompt for length/section structure as part of this stage, or accept a
deliberately terse one-page brief. Resolve before build.

### Ships

- Report permalink page `/reports/[id]` backed by existing persistence
- Report list page `/reports` (history browsing — also closes the long-standing
  gap that the target structure specified these routes but they were never built)
- Public read API for a single report by id, suitable for unauthenticated link access
- OpenGraph + Twitter Card meta on the permalink (title, summary, confidence,
  source count) and an OG preview image (static template or dynamically generated)
- Print-optimized CSS (`@media print`) for clean browser "Save as PDF"
- Server-rendered PDF export (e.g. `GET /reports/{id}/pdf`) producing a consistent,
  attachable file — engine decided at stage start (Chromium print-to-PDF reusing
  the existing CloakBrowser/Playwright stack, vs WeasyPrint/HTML, vs client-only)
- UI affordances: Download PDF, Copy share link, and share intents
  (`mailto:`, X/LinkedIn share URLs)

### PDF look and format (design intent)

- Letter/A4, single column, ~11pt body, clear typographic hierarchy, GhostResearcher
  branding in header/footer
- Cover/header block: report title, the original research goal, generated timestamp,
  and a confidence badge
- Executive summary section
- Key findings as a numbered list, each finding carrying inline citation markers that
  resolve to the sources appendix
- Sources appendix: each source with its credibility score
- Limitations + a short methodology note (agentic browse → extract → assess →
  synthesize), page numbers in the footer

### PDF layout is an iteration loop, not a one-shot

The PDF layout and typography are expected to take several visual passes to get
right — this is explicitly planned, not a sign of going off-track. Approach:

- Pin a fixed sample report (a known-good live artifact) as the rendering fixture so
  every layout pass renders the same content and only the design changes
- Produce the PDF from an HTML/CSS template (whatever engine is chosen) so iteration
  is CSS edits, not code rewrites
- Each pass: generate the sample PDF, eyeball it against the design intent, refine.
  Budget multiple rounds; treat layout sign-off as its own checkpoint
- Hold the data contract stable while iterating on presentation, so layout churn does
  not destabilize synthesis or the schema
- Capture the approved reference render (a committed sample PDF/screenshot) as the
  visual baseline so later changes are diffable

### Exit criteria

- A completed report is reachable at a stable, shareable URL
- That URL renders a social preview card (OG/Twitter validated)
- A user can download a PDF and print cleanly from the browser
- The PDF includes title, research goal, summary, findings with citations, sources
  with credibility scores, and limitations
- The report list shows prior persisted reports

### Decisions to resolve at stage start (log in DECISIONS.md)

- PDF engine: reuse Chromium via Playwright print-to-PDF, WeasyPrint, or client-only
  print-to-PDF
- Whether PDFs are generated server-side (attachable, automatable) or client-side only
- OG preview image: static template vs dynamic generation (e.g. `@vercel/og`)
- Public/unauthenticated report access model (the app is currently single-user with
  no auth; link sharing implies public-by-id reports)

---

## v1.4.0 - Scholarly Source Coverage (Deferred)

Goal: Give the agent first-class access to scholarly/research repositories instead
of relying on generic web search to surface them, so a "research" engine actually
reaches the research literature.

Status: Planned / Deferred. Sequenced after the v1.2.x stealth work.

### Context

Runtime source discovery is generic Brave web search ([search.py](../backend/executor/search.py));
there is no integration with academic/research repositories (arXiv, Semantic
Scholar, PubMed/Europe PMC, CORE, OpenReview, Crossref). The benchmark prompts
*expect* academic sources (`expected_source_types: academic/preprint`), but the
pipeline does not target them — they appear only if Brave happens to surface them.

### Ships

- A research-source-provider layer mirroring the existing search-provider boundary:
  providers for arXiv (Atom API, no key), Semantic Scholar (Graph API), PubMed /
  Europe PMC, CORE, Crossref — most are free / keyless
- Planner access via either a `scholarly_search` tool or a `source_type` argument on
  `web_search`, merging results into the source-candidate queue
- Keyless fallback: bias web-search queries toward scholarly domains (`site:` filters)
  when no provider is configured, so the default path stays dependency-free
- Credibility scoring extended with scholarly signals (peer-reviewed venue, citation
  count, recency, author/institution)
- Evals: academic benchmark prompts validate repository coverage; a scholarly-coverage
  metric in the harness

### Exit criteria

- A research goal in an academic domain surfaces and cites real repository sources
  (e.g. arxiv.org papers) in the report
- Scholarly providers are configurable and dependency-free by default (deterministic
  offline provider for tests)
- The eval shows improved expected-source coverage on academic prompts

### Decisions to resolve at stage start

- Which APIs first (arXiv + Semantic Scholar are free and keyless — likely first)
- New `scholarly_search` tool vs a `source_type` parameter on `web_search`
- Scholarly PDF handling — ties to the deferred full-PDF-parsing extraction item
