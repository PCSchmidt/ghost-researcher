# GhostResearcher

GhostResearcher is an agentic web research engine in progress. The current build
focuses on the backend control path: planner decisions, executor tool dispatch,
session state, and a minimal FastAPI API. Frontend, persistence, Claude planner
integration, synthesis, live browser integration tests, and deployment are planned
but not shipped yet.

---

## Current Status

Current checkpoint: v0.7.0 - Multi-Step Planner Skeleton complete.  
Next stage: v0.8.0 - Search Tool Skeleton.

Implemented now:

- FastAPI app factory and `/health`
- `POST /research` endpoint
- Schema-locked tool catalog
- Agent session state model
- CloakBrowser CDP health client
- Executor skeletons for `navigate_to_url`, `extract_structured_data`, and `assess_credibility`
- Deterministic planner skeleton
- Multi-step orchestrator sequence: `navigate_to_url -> extract_structured_data -> assess_credibility`
- Unit tests for config, API routes, planner, runner, and executor modules

Not implemented yet:

- Claude API planner adapter
- `web_search` executor implementation
- Report synthesis
- Postgres/Redis persistence
- Frontend UI
- Docker/Railway/Vercel deployment
- Live CloakBrowser integration test

See [core/VERSION_ROADMAP.md](core/VERSION_ROADMAP.md) for the full staged plan.

---

## Architecture Target

```text
User research goal
        |
        v
FastAPI /research
        |
        v
ResearchOrchestrator
        |
        v
PlannerSkeleton -> ResearchRunner -> Executor tools
        |              |              |
        |              |              +-- navigate_to_url
        |              |              +-- extract_structured_data
        |              |              +-- assess_credibility
        |              |
        |              v
        |        AgentSession state
        |
        v
Response with decisions[], tool_results[], session, synthesis=null
```

The production target remains a Claude planner, CloakBrowser executor, credibility
scorer, report synthesizer, persisted jobs, SSE status updates, and a Next.js UI.
The current repo intentionally builds toward that target in small verified slices.

---

## Repository Layout

```text
ghost-researcher/
+-- backend/
|   +-- agent/          # Tool catalog, session state, deterministic planner skeleton
|   +-- api/            # FastAPI routes: /health and /research
|   +-- executor/       # Browser health, navigation, extraction, credibility skeletons
|   +-- jobs/           # Runner and planner orchestration
|   +-- config.py       # Environment-backed settings
|   +-- main.py         # FastAPI app factory
+-- core/               # Blueprint/Syntaris contract, spec, roadmap, decisions, memory
+-- evals/              # Benchmark prompt seed
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

For the current fake-tested backend slices, no live Anthropic, Redis, Postgres, or
CloakBrowser service is required. A live CloakBrowser instance will be required
for later integration testing.

---

## Run Tests

```bash
python -m unittest tests.test_config tests.test_agent.test_tools tests.test_agent.test_memory tests.test_agent.test_planner tests.test_api.test_health tests.test_api.test_research tests.test_executor.test_browser tests.test_executor.test_navigate tests.test_executor.test_extract tests.test_executor.test_credibility tests.test_jobs.test_runner tests.test_jobs.test_research
```

Current validated result: 41 tests passing.

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

The response currently returns planner decisions, tool results, session state, and
`synthesis: null`. Report synthesis is planned for a later stage.

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=
CLOAK_CDP_URL=http://localhost:9222
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379
PROXY_URL=
PROXY_USER=
PROXY_PASS=
MAX_STEPS_PER_JOB=20
MAX_TOKENS_PER_JOB=50000
SCRAPE_ENABLED=true
LOG_LEVEL=INFO
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
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
- v0.9.0 - Claude Planner Adapter
- v0.10.0 - Synthesizer Skeleton
- v0.11.0 - Persistence and Job State
- v0.12.0 - Live Status Stream
- v0.13.0 - Frontend Research UI
- v0.14.0 - Evals Harness
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
