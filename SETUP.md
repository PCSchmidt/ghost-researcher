# GhostResearcher Setup And Resume Guide

This project has moved past the initial prototype setup. Use this document to
prepare a local environment, verify the current baseline, and resume work from
the staged roadmap.

---

## Current Baseline

Current checkpoint: v0.16.0 - Real Search and Live Evals complete.
Next stage: v0.17.0 - Live Integration Smoke Tests.

Gate 1 is confirmed:

- [core/CONTRACT.md](core/CONTRACT.md) contains dollar-denominated model cost ceilings.
- [core/AGENT_SPEC.md](core/AGENT_SPEC.md) defines the planner, tool, session, and failure contracts.
- [core/COSTS.md](core/COSTS.md) locks the OpenRouter-first cost plan.
- [core/DECISIONS.md](core/DECISIONS.md) records the critical review outcome.
- [evals/benchmark_prompts.json](evals/benchmark_prompts.json) contains 10 benchmark prompts.
- [backend/agent/tools.py](backend/agent/tools.py) contains the schema-locked tool catalog.

The current backend and eval harness are fake-tested. No live OpenRouter, Redis,
Postgres, CloakBrowser service, or real search provider is required to run the
regression suite or offline benchmark eval.

---

## Local Setup

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

Never commit `.env` or real API keys.

---

## Environment Variables

OpenRouter is the default model gateway. Anthropic is an optional premium
fallback only.

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
SCRAPE_ENABLED=true
LOG_LEVEL=INFO
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-vercel-app.vercel.app
```

---

## Verify The Baseline

Run the full backend regression suite:

```bash
python -m unittest tests.test_config tests.test_agent.test_tools tests.test_agent.test_memory tests.test_agent.test_planner tests.test_agent.test_openrouter tests.test_api.test_health tests.test_api.test_research tests.test_executor.test_browser tests.test_executor.test_navigate tests.test_executor.test_extract tests.test_executor.test_credibility tests.test_executor.test_search tests.test_synthesizer.test_schema tests.test_synthesizer.test_report tests.test_persistence.test_repository tests.test_jobs.test_runner tests.test_jobs.test_research tests.test_jobs.test_status tests.test_evals.test_eval_runner
```

Expected current result: 85 backend tests passing.

Run the offline eval harness:

```bash
python -m evals.eval_runner --mode offline --limit 3
```

Expected current eval result: 3 benchmark prompts run in offline mode with the
deterministic search provider, average score 1.0, and a JSON artifact written
under `evals/results/`.

Live eval mode is opt-in:

```bash
SEARCH_PROVIDER=brave SEARCH_API_KEY=... python -m evals.eval_runner --mode live --limit 3
```

Live mode uses configured provider/runtime services and is not part of the
dependency-free regression suite.

Run the frontend checks:

```bash
cd frontend
npm run lint
npm test
npm run build
```

Expected current frontend result: lint clean, 8 tests passing, production build passing.

---

## Run The API Locally

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

The response currently includes planner decisions, tool results, status events,
session state, `synthesis` when sufficient evidence exists, and a `job_id` for
retrieval with `GET /research/{job_id}`. Persisted status events are also
available as SSE with `GET /research/{job_id}/events`.

Run the frontend locally in a second terminal:

```bash
cd frontend
npm run dev
```

The frontend defaults to `NEXT_PUBLIC_API_URL=http://localhost:8000`.

---

## CloakBrowser Setup For Later Gates

Live browser integration is not required for the current fake-tested backend
baseline. Before live executor tests, clone and verify CloakBrowser separately:

```bash
git clone https://github.com/PCSchmidt/CloakBrowser.git
cd CloakBrowser
# Build and verify cloakserve --version works
```

GhostResearcher must run its own `cloakserve` instance. Do not share runtime
state with SkySigint.

---

## Resume Workflow

Start each coding session with `/start`, then read:

1. [README.md](README.md)
2. [core/VERSION_ROADMAP.md](core/VERSION_ROADMAP.md)
3. [core/SPEC.md](core/SPEC.md)
4. [core/AGENT_SPEC.md](core/AGENT_SPEC.md)

The next build slice is v0.17.0: add skipped-by-default live smoke tests for the
configured search provider, OpenRouter, and CloakBrowser path.

---

## Gate Checklist

| Stage | Exit Artifacts | Status |
| --- | --- | --- |
| v0.1.0 | Contract, AGENT_SPEC, memory files, ERRORS, benchmark prompts | Complete |
| v0.2.0 | `backend/agent/tools.py` complete schemas | Complete |
| v0.3.0 | Browser health, navigation executor, runner tests | Complete |
| v0.4.0 | Deterministic planner integration skeleton | Complete |
| v0.5.0 | `POST /research` endpoint skeleton | Complete |
| v0.6.0 | Extraction and credibility executor skeletons | Complete |
| v0.7.0 | Multi-step planner sequence | Complete |
| v0.8.0 | Search tool skeleton | Complete |
| v0.9.0 | OpenRouter planner adapter | Complete |
| v0.10.0 | Synthesizer skeleton | Complete |
| v0.11.0 | Persistence and job state | Complete |
| v0.12.0 | SSE live status stream | Complete |
| v0.13.0 | Frontend research UI | Complete |
| v0.14.0 | Evals harness | Complete |
| v0.15.0 | Live capability alignment | Complete |
| v0.16.0 | Real search and live evals | Complete |
| v0.17.0 | Live integration smoke tests | Next |
| v1.0.0 | Railway and Vercel deployment | Planned |
