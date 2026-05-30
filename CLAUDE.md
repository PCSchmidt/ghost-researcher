# GhostResearcher — Claude Code Session Context

## What This Project Is

GhostResearcher is an autonomous agentic web research engine. The user submits
a research prompt. An OpenRouter-backed LLM planner decomposes it into a multi-step
browsing strategy, dispatches tool calls to a CloakBrowser executor, extracts
and credibility-scores sources, and synthesizes a structured intelligence report.

This is a **full-stack agentic AI project** with three distinct layers:

- **Planner**: OpenRouter-backed LLM with tool use (function calling loop)
- **Executor**: CloakBrowser via CDP — stealth browser navigation and extraction
- **Synthesizer**: OpenRouter-backed LLM call that produces the final structured report

## Portfolio Purpose

GhostResearcher closes the two highest-priority gaps identified in the
pcschmidt.github.io portfolio review:

1. **Agentic AI** — real tool-use loop, not black-box API calls
2. **Evals culture** — `evals/` directory seeds a live web evals harness (Priority 3)

The credibility scorer (ML-backed source quality assessment) connects this project
to the existing inference optimization and ML pipeline work in the portfolio.

## Relationship to SkySigint

- Both projects use CloakBrowser for stealth browser automation
- Both deploy to Railway
- They do **not** share a codebase or runtime — GhostResearcher has its own
  `cloakserve` CDP server instance
- The `BaseScraper` / CDP connection pattern from SkySigint is the reference
  implementation — replicate the pattern, do not import from SkySigint
- GhostResearcher's `evals/` directory is the seed for Priority 3 (live web evals harness)

## Relationship to Syntaris

- Syntaris is installed at `C:\Users\pchri\Syntaris`
- Recipe: **bring-your-own** (GhostResearcher has a frontend; use the
  `nextjs-fastapi-supabase` recipe as a structural reference but customize heavily)
- Run `bash C:\Users\pchri\Syntaris\install.sh` from this project root before
  opening Claude Code
- Always begin every session with `/start`
- Memory files must be updated at every gate close

## Tech Stack

| Layer | Technology |
| --- | --- |
| Planner | OpenRouter model gateway with DeepSeek/Qwen default tier and optional Anthropic fallback |
| Executor | CloakBrowser (Chromium CDP) + Playwright async |
| API framework | FastAPI (Python 3.11+) |
| Job queue | Redis (research job queue) |
| Persistence | Postgres (research reports, source logs) |
| Frontend | Next.js 14 (App Router) |
| Containerization | Docker — cloakserve + ghostresearcher-api |
| Frontend deploy | Vercel |
| Backend deploy | Railway (cloakserve + ghostresearcher-api) |
| Build framework | Syntaris (bring-your-own recipe) |

## Deployment Targets

- **Backend + CloakBrowser**: Railway (single project, two services)
  - `cloakserve`: persistent CDP server, internal port 9222
  - `ghostresearcher-api`: FastAPI, public port 8000
- **Frontend**: Vercel
  - Next.js 14 App Router
  - Connects to Railway backend via `NEXT_PUBLIC_API_URL`

## Directory Structure (Target State)

```text
ghost-researcher/
├── .claude/                        # Syntaris hooks and skills
├── core/                           # Syntaris foundation files
│   ├── CONTRACT.md
│   ├── AGENT_SPEC.md               # Gate 1 exit artifact — most critical doc
│   ├── SPEC.md
│   ├── SPEC_GATES.md
│   ├── DECISIONS.md
│   ├── ERRORS.md
│   ├── MEMORY_SEMANTIC.md
│   ├── MEMORY_EPISODIC.md
│   └── MEMORY_CORRECTIONS.md
├── backend/
│   ├── main.py                     # FastAPI entrypoint
│   ├── config.py
│   ├── agent/
│   │   ├── planner.py              # LLM tool-use loop
│   │   ├── tools.py                # Tool definitions — Gate 2 exit artifact
│   │   ├── memory.py               # AgentSession state
│   │   └── prompts.py              # System prompt, planner prompt templates
│   ├── executor/
│   │   ├── browser.py              # CloakBrowser CDP connection manager
│   │   ├── navigate.py             # Tool: navigate to URL
│   │   ├── extract.py              # Tool: extract structured content
│   │   ├── search.py               # Tool: web search + return results
│   │   ├── screenshot.py           # Tool: capture page screenshot
│   │   └── credibility.py          # Source credibility scorer
│   ├── synthesizer/
│   │   ├── report.py               # LLM → structured report
│   │   ├── schema.py               # ResearchReport Pydantic model
│   │   └── scorer.py               # Report quality scoring → feeds evals/
│   ├── jobs/
│   │   ├── queue.py                # Redis-backed job queue
│   │   └── runner.py               # Async orchestrator: planner + executor
│   └── api/
│       ├── research.py             # POST /research, GET /research/{job_id}
│       ├── reports.py              # GET /reports, GET /reports/{id}
│       └── health.py               # /health
├── frontend/                       # Next.js 14
│   ├── app/
│   │   ├── page.tsx                # Research prompt submission
│   │   ├── reports/
│   │   │   ├── page.tsx            # Report list
│   │   │   └── [id]/page.tsx       # Individual report view
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ResearchForm.tsx
│   │   ├── JobStatus.tsx           # SSE status stream — shows agent steps in real time
│   │   ├── ReportViewer.tsx
│   │   └── SourceCard.tsx          # Source + credibility score display
│   └── lib/
│       └── api.ts
├── tests/
│   ├── test_agent/
│   │   ├── test_planner.py
│   │   └── test_tools.py
│   ├── test_executor/
│   │   ├── test_navigate.py
│   │   ├── test_extract.py
│   │   ├── test_search.py
│   │   └── test_credibility.py
│   └── test_synthesizer/
│       ├── test_report.py
│       └── test_scorer.py
├── evals/                          # Priority 3 seed — built from day one
│   ├── benchmark_prompts.json      # 10 research prompts with expected characteristics
│   ├── eval_runner.py              # Agent vs benchmark, scores output
│   └── results/                    # MEMORY_CORRECTIONS feeds here
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.cloak
│   └── docker-compose.yml
├── docs/
│   └── ARCHITECTURE.md
├── .env.example
├── pyproject.toml
├── requirements.txt
├── CLAUDE.md                       # This file
└── README.md
```

## Gate Model (Syntaris)

```text
CONFIRMED
    ↓
[Gate 1: CONTRACT + AGENT_SPEC]
    Exit artifacts: CONTRACT.md, AGENT_SPEC.md, SPEC.md
    Critical: AGENT_SPEC.md defines tool schemas, planner prompt contract,
              termination conditions, cost guard, and failure mode catalog
    ↓
[Gate 2: TOOL INTERFACE LOCKED]
    Exit artifact: backend/agent/tools.py (all tool schemas complete, no stubs)
    Hook: fails if tools.py missing or any tool lacks input_schema
    No executor implementation may be written before this gate closes
    ↓
[Gate 3: EXECUTOR UNIT TESTS PASS]
    Exit artifact: backend unit tests pass for all executor modules
    Hook: fails if any test missing or regression suite exit code != 0
    ↓
[Gate 4: PLANNER INTEGRATION]
    Exit artifact: planner produces valid tool call sequences for 3 benchmark prompts
    The 3 prompts live in evals/benchmark_prompts.json
    ↓
[Gate 5: END-TO-END REPORT]
    Exit artifact: 3 complete research reports generated, scored, results in evals/results/
    ↓
GO — deploy backend to Railway, frontend to Vercel
```

## AGENT_SPEC.md Requirements (Gate 1 Exit Artifact)

This is the most important document in the project. It must define:

**Planner system prompt contract:**

- What the planner knows: research goal, available tools, tool output format
- What the planner must output: structured tool calls, not free text
- Termination conditions: max_steps (hard limit), confidence threshold, no_new_sources signal
- Cost guard: max model spend per job, token budget per call

**Tool definitions (all 5):**

- `navigate_to_url(url, wait_for?, fingerprint_seed?) → PageContent`
- `extract_structured_data(selector, extraction_goal, output_schema?) → ExtractedData`
- `web_search(query, num_results?) → SearchResults`
- `assess_credibility(url, content_snippet) → CredibilityScore`
- `finalize_report(confidence, sources_used, termination_reason) → void`

**AgentSession state schema:**

- research_goal, steps_taken, sources_visited, running_cost
- detection_events (per source), termination_state, termination_reason

**Failure mode catalog (required before Gate 1 closes):**

- Agent loop: same URL visited repeatedly → URL deduplication + step counter hard stop
- Cost runaway: uncapped model calls → hard token and dollar budgets, graceful early termination
- Hallucination in synthesis: every claim traceable to an extracted source in session state
- Bot detection cascade: tool returns detection_blocked=true, planner adapts browsing plan
- Context window overflow: long research sessions accumulate tool results → summarize mid-session

## Tool Definitions (Gate 2 Exit Artifact Seed)

```python
TOOLS = [
    {
        "name": "navigate_to_url",
        "description": "Navigate the stealth browser to a URL and return page content",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "wait_for": {"type": "string", "description": "CSS selector to wait for"},
                "fingerprint_seed": {"type": "integer"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "extract_structured_data",
        "description": "Extract structured data from the current page",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "extraction_goal": {"type": "string"},
                "output_schema": {"type": "object"}
            },
            "required": ["selector", "extraction_goal"]
        }
    },
    {
        "name": "web_search",
        "description": "Execute a web search and return top results with URLs",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "num_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "assess_credibility",
        "description": "Score source credibility based on domain, content, and freshness",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "content_snippet": {"type": "string"}
            },
            "required": ["url", "content_snippet"]
        }
    },
    {
        "name": "finalize_report",
        "description": "Signal research complete and trigger report synthesis",
        "input_schema": {
            "type": "object",
            "properties": {
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "sources_used": {"type": "array", "items": {"type": "string"}},
                "termination_reason": {
                    "type": "string",
                    "enum": ["sufficient_coverage", "max_steps", "cost_limit", "no_new_sources"]
                }
            },
            "required": ["confidence", "sources_used", "termination_reason"]
        }
    }
]
```

## Architectural Decisions (Do Not Revisit Without Updating DECISIONS.md)

1. **Separate repo and separate cloakserve from SkySigint** — different compute profiles,
   different fingerprint strategies, different deployment lifecycles. Shared pattern,
   not shared infrastructure.

2. **LLM as planner, CloakBrowser as executor** — the model never touches the browser
   directly. The tool-use interface is the only contract between planner and executor.
   This separation makes the executor independently testable.

3. **finalize_report is a tool, not a stop condition** — the planner signals completion
   by calling finalize_report, not by returning end_turn. This gives the runner explicit
   control over when synthesis begins and prevents premature termination.

4. **evals/ built from day one** — benchmark_prompts.json is created at Gate 1.
   Every Gate 5 report run produces scored output into evals/results/. The evals
   harness is not a future feature — it is part of the Gate 5 exit artifact.

5. **Credibility scoring is explicit and documented** — not a vibe check. Features:
   domain authority signals (gov/edu TLD), content freshness, cross-source
   corroboration count, detection resistance penalty. Logistic regression or
   hand-tuned scoring function over labeled features. Score feeds report confidence.

6. **Frontend shows agent steps in real time** — JobStatus.tsx consumes the SSE
    status stream and renders each tool call as it completes. This is the primary portfolio demo moment.
   A hiring audience watching the agent navigate, extract, and score sources in real time
   understands immediately what the system does.

## Known Failure Modes (Pre-seeded in ERRORS.md)

- **Agent loop**: planner revisits same URL → detect via session_state.sources_visited set,
  return cached result, increment loop_detection counter, terminate if > 3 repeats
- **Cost runaway**: no token or dollar budget → set max_tokens_per_job and max_model_cost_per_job_usd in config, track running_cost
  in AgentSession, call finalize_report with termination_reason="cost_limit" when exceeded
- **Hallucination in synthesis**: model invents sources in report → every cited source
  must exist in session_state.sources_visited; synthesizer validates before returning report
- **Context window overflow**: long sessions accumulate tool results → mid-session
  summarization step after every 10 tool calls, compress older results
- **CDP server crash**: cloakserve down → all executor tools fail simultaneously →
  Railway restart policy, /health endpoint detects and reports cloakserve status
- **Frontend polling storm**: many concurrent jobs, each JobStatus polling /research/{job_id}
  every 2s → use SSE (Server-Sent Events) instead of polling for job status updates
- **Model routing variance**: cheaper models vary in tool-call/JSON reliability → validate
    every model output against schemas, retry once, then escalate or finalize safely

## Environment Variables Required

```bash
# Model gateway
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_PLANNER_MODEL=deepseek/deepseek-v4-flash
FALLBACK_PLANNER_MODEL=deepseek/deepseek-v4-pro
DEFAULT_SYNTHESIZER_MODEL=deepseek/deepseek-v4-flash
FALLBACK_SYNTHESIZER_MODEL=moonshotai/kimi-k2.6

# Optional premium fallback
ANTHROPIC_API_KEY=

# CloakBrowser CDP server
CLOAK_CDP_URL=http://localhost:9222

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Proxy (for high bot-risk sources)
PROXY_URL=
PROXY_USER=
PROXY_PASS=

# Agent behavior
MAX_STEPS_PER_JOB=20
MAX_TOKENS_PER_JOB=50000
MAX_MODEL_COST_PER_JOB_USD=0.05
WARN_MODEL_COST_PER_JOB_USD=0.02
SCRAPE_ENABLED=true
LOG_LEVEL=INFO

# Frontend (Vercel env var)
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
```

## Current Implementation Checkpoint

- Current checkpoint: v0.10.0 - Synthesizer Skeleton complete
- Next stage: v0.11.0 - Persistence and Job State
- Current regression baseline: 63 tests passing
- `web_search` is a deterministic skeleton, not a real provider integration yet
- URL-free goals now run `web_search -> navigate_to_url -> extract_structured_data -> assess_credibility`
- OpenRouter planner adapter is fake-tested; no live OpenRouter integration test yet
- Report synthesis is source-validated and fake-tested; no live synthesizer integration test yet

## Resume Checklist

- [x] `core/CONTRACT.md` filled and CONFIRMED
- [x] `core/AGENT_SPEC.md` complete before Gate 1 closes; `/critical-thinker` outcome logged in DECISIONS.md
- [x] `evals/benchmark_prompts.json` created with 10 prompts
- [x] `backend/agent/tools.py` complete before executor work
- [x] `.env.example` committed, `.env` in `.gitignore`
- [x] v0.8.0 search skeleton complete and documented
- [x] v0.9.0 OpenRouter planner adapter complete and documented
- [x] v0.10.0 synthesizer skeleton complete and documented
- [ ] v0.11.0 persistence and job state not started

## Session Start Command

```text
/start
```

Always. Every session. No exceptions.
