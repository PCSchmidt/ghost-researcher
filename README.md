# GhostResearcher

GhostResearcher is an agentic web research engine in progress. The current build
focuses on the backend control path: planner decisions, executor tool dispatch,
session state, synthesis skeleton, job-state persistence boundary, replayable
status events, a Next.js research workbench, a repeatable offline eval harness,
and skipped-by-default live integration smoke tests. Deployment is planned but
not shipped yet.

---

## Current Status

Current checkpoint: v0.17.0 - Live Integration Smoke Tests complete.
Next stage: v1.0.0 - Deployment.

Implemented now:

- FastAPI app factory and `/health`
- `POST /research` endpoint
- Schema-locked tool catalog
- Agent session state model
- CloakBrowser CDP health client
- Executor skeletons for `web_search`, `navigate_to_url`, `extract_structured_data`, and `assess_credibility`
- Search provider boundary with deterministic default and opt-in Brave Search provider
- Deterministic planner skeleton
- Multi-step orchestrator sequence for URL goals: `navigate_to_url -> extract_structured_data -> assess_credibility`
- Search-first orchestrator sequence for URL-free goals: `web_search -> navigate_to_url -> extract_structured_data -> assess_credibility`
- Multi-source deterministic orchestration with explicit `finalize_report` execution
- OpenRouter planner adapter with tool-call validation, usage accounting, and cost-limit stops
- Report synthesis skeleton with source-trace validation
- Research job repository boundary, in-memory job storage, JSON-file restart durability, and `GET /research/{job_id}`
- Persisted `status_events[]` and `GET /research/{job_id}/events` SSE stream for frontend status views
- Next.js research workbench with submission form, status stream view, report view, and source cards
- Offline benchmark eval runner with source traceability, report quality, and criteria coverage scoring
- Offline evals that can satisfy benchmark minimum source counts before synthesis
- Eval CLI modes: `--mode offline|live`
- Skipped-by-default live smoke tests for Brave Search, OpenRouter, and CloakBrowser
- Unit tests for backend modules, eval harness behavior, and focused frontend UI/API behavior

Not implemented yet:

- Postgres/Redis production persistence
- Docker/Railway/Vercel deployment
- Committed live eval artifact from a real provider run

See [core/VERSION_ROADMAP.md](core/VERSION_ROADMAP.md) for the full staged plan.

---

## Architecture Target

```text
User research goal
        |
        v
FastAPI /research + /research/{job_id} + /research/{job_id}/events
        |
        v
ResearchOrchestrator
        |
        v
PlannerSkeleton/OpenRouterPlanner -> ResearchRunner -> Executor tools
        |              |              |
        |              |              +-- web_search
        |              |              +-- navigate_to_url
        |              |              +-- extract_structured_data
        |              |              +-- assess_credibility
        |              |
        |              v
        |        AgentSession state -> ReportSynthesizer
        |
        v
Persisted response with job_id, status_events[], decisions[], tool_results[], session, synthesis
```

The production target remains an OpenRouter-backed planner, CloakBrowser executor, credibility
scorer, report synthesizer, persisted jobs, SSE status updates, and a Next.js UI.
The current repo intentionally builds toward that target in small verified slices.

---

## Repository Layout

```text
ghost-researcher/
+-- backend/
|   +-- agent/          # Tool catalog, session state, deterministic planner, OpenRouter adapter
|   +-- api/            # FastAPI routes: /health and /research
|   +-- executor/       # Browser health, search, navigation, extraction, credibility skeletons
|   +-- jobs/           # Runner and planner orchestration
|   +-- persistence/    # Job repository boundary and JSON-file storage skeleton
|   +-- synthesizer/    # Report schema, synthesis skeleton, source validation
|   +-- config.py       # Environment-backed settings
|   +-- main.py         # FastAPI app factory
+-- core/               # Blueprint/Syntaris contract, spec, roadmap, decisions, memory
+-- evals/              # Benchmark prompts, eval runner, and persisted result artifacts
+-- frontend/           # Next.js research workbench
+-- tests/              # Unit tests for current backend slices
+-- .env.example
+-- requirements.txt
+-- README.md
```

---

## Setup

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Create a local environment file when needed:

```bash
cp .env.example .env
```

For the default backend and eval checks, no live OpenRouter, Redis, Postgres,
CloakBrowser service, or search API key is required. Live smoke tests are
available but skip unless explicitly enabled.

Install frontend dependencies separately:

```bash
cd frontend
npm install
```

---

## Run Tests

```bash
python -m unittest tests.test_config tests.test_agent.test_tools tests.test_agent.test_memory tests.test_agent.test_planner tests.test_agent.test_openrouter tests.test_api.test_health tests.test_api.test_research tests.test_executor.test_browser tests.test_executor.test_navigate tests.test_executor.test_extract tests.test_executor.test_credibility tests.test_executor.test_search tests.test_synthesizer.test_schema tests.test_synthesizer.test_report tests.test_persistence.test_repository tests.test_jobs.test_runner tests.test_jobs.test_research tests.test_jobs.test_status tests.test_evals.test_eval_runner tests.test_live.test_smoke
```

Current validated result: 90 backend tests OK by default, with 85 executed and
5 live smoke tests skipped.

Run the offline eval harness:

```bash
python -m evals.eval_runner --mode offline --limit 3
```

Current v0.16 result: 3 benchmark prompts completed in offline mode with the
deterministic search provider, average score 1.0, with results persisted under
`evals/results/`. Live mode is opt-in and requires `SEARCH_PROVIDER=brave`,
`SEARCH_API_KEY`, and live browser/search dependencies.

Run live smoke tests only when local services and keys are configured:

```bash
GHOSTRESEARCHER_RUN_LIVE_TESTS=1 SEARCH_PROVIDER=brave SEARCH_API_KEY=... OPENROUTER_API_KEY=... CLOAK_CDP_URL=http://localhost:9222 python -m unittest tests.test_live.test_smoke
```

If any required variable is absent, the corresponding smoke test is skipped with
a clear reason. The normal regression suite must remain dependency-free.

Run frontend checks:

```bash
cd frontend
npm run lint
npm test
npm run build
```

Current frontend result: 8 tests passing, lint clean, production build passing.

---

## Run API Locally

```bash
uvicorn backend.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Research skeleton request:

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"research_goal":"Review https://example.com/report"}'
```

The response currently returns planner decisions, tool results, status events,
session state, `synthesis` when sufficient evidence exists, and a `job_id` that
can be fetched with `GET /research/{job_id}`. Status events can be streamed as
SSE with `GET /research/{job_id}/events`.

---

## Environment Variables

```bash
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_APP_TITLE=GhostResearcher
OPENROUTER_HTTP_REFERER=http://localhost:8000
DEFAULT_PLANNER_MODEL=deepseek/deepseek-v4-flash
FALLBACK_PLANNER_MODEL=deepseek/deepseek-v4-pro
DEFAULT_SYNTHESIZER_MODEL=deepseek/deepseek-v4-flash
FALLBACK_SYNTHESIZER_MODEL=moonshotai/kimi-k2.6
ANTHROPIC_API_KEY=
CLOAK_CDP_URL=http://localhost:9222
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379
SEARCH_PROVIDER=deterministic
SEARCH_API_KEY=
SEARCH_API_URL=https://api.search.brave.com/res/v1/web/search
PROXY_URL=
PROXY_USER=
PROXY_PASS=
MAX_STEPS_PER_JOB=20
MAX_TOKENS_PER_JOB=50000
MAX_MODEL_COST_PER_JOB_USD=0.05
WARN_MODEL_COST_PER_JOB_USD=0.02
GHOSTRESEARCHER_RUN_LIVE_TESTS=0
SCRAPE_ENABLED=true
LOG_LEVEL=INFO
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-vercel-app.vercel.app
```

---

## Roadmap

The build is intentionally staged:

- v0.1.0 - Foundation + Agent Contract
- v0.2.0 - Tool Interface Lock
- v0.3.0 - First Executor Action
- v0.4.0 - Planner Integration Skeleton
- v0.5.0 - API Research Endpoint Skeleton
- v0.6.0 - Extract and Credibility Skeletons
- v0.7.0 - Multi-Step Planner Skeleton
- v0.8.0 - Search Tool Skeleton
- v0.9.0 - OpenRouter Planner Adapter
- v0.10.0 - Synthesizer Skeleton
- v0.11.0 - Persistence and Job State
- v0.12.0 - Live Status Stream
- v0.13.0 - Frontend Research UI
- v0.14.0 - Evals Harness
- v0.15.0 - Live Capability Alignment
- v0.16.0 - Real Search and Live Evals
- v0.17.0 - Live Integration Smoke Tests
- v1.0.0 - Deployment

Full details live in [core/VERSION_ROADMAP.md](core/VERSION_ROADMAP.md).

---

## Related Projects

| Project | Role |
| --- | --- |
| [SkySigint](https://github.com/PCSchmidt/sigint) | CDP/CloakBrowser pattern reference |
| [CloakBrowser](https://github.com/PCSchmidt/CloakBrowser) | Stealth Chromium runtime |
| [Syntaris](https://github.com/PCSchmidt/Syntaris) | Build framework |

---

## License

MIT
