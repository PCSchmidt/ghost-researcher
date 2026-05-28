# GhostResearcher — First Session Setup

Complete these steps **in order** before opening Claude Code or writing any
application code. Each step is a hard prerequisite for the next.

---

## Step 1 — Clone CloakBrowser (if not already done for SkySigint)

```bash
git clone https://github.com/PCSchmidt/CloakBrowser.git
cd CloakBrowser
# Build and verify cloakserve --version works
```

If you already cloned CloakBrowser for SkySigint, confirm it still builds cleanly.
GhostResearcher runs its **own** `cloakserve` instance — do not share with SkySigint.

**Checkpoint:** `cloakserve --version` returns without error.

---

## Step 2 — Install Syntaris into This Project

From the `ghost-researcher/` project root:

```bash
bash C:\Users\pchri\Syntaris\install.sh
bash C:\Users\pchri\Syntaris\syntaris-doctor.sh
```

All checks must pass before proceeding.

**Checkpoint:** `syntaris-doctor.sh` exits clean. `.claude/` and `core/` directories exist.

---

## Step 3 — Copy CLAUDE.md into Project Root

`CLAUDE.md` is already written. Place it at the project root alongside README.md and this file.

It contains the full agent architecture, tool definitions, gate model, failure mode catalog,
architectural decisions, and first session checklist. Claude Code reads it at every `/start`.

**Checkpoint:** `CLAUDE.md` exists at `ghost-researcher/` root.

---

## Step 4 — Create evals/benchmark_prompts.json

This file must exist before Gate 1 can close. Create it now with 10 research prompts.
Gate 4 uses 3 of these as the integration test. Gate 5 runs all 10.

Format:

```json
[
  {
    "id": "bp_001",
    "prompt": "Summarize DoD uncrewed systems procurement activity from the past 30 days",
    "domain": "defense_aerospace",
    "expected_source_types": ["gov", "news", "procurement"],
    "min_sources": 3,
    "max_steps": 15,
    "notes": "Should hit SAM.gov, defense news outlets, USASpending"
  },
  {
    "id": "bp_002",
    "prompt": "What are the most recent FAA rulemaking actions affecting commercial UAS operations?",
    "domain": "aviation_regulatory",
    "expected_source_types": ["gov", "legal", "industry"],
    "min_sources": 3,
    "max_steps": 12,
    "notes": "Should hit FAA.gov rulemaking portal, federal register"
  }
  // ... 8 more prompts covering your target research domains
]
```

Write prompts in domains you can verify answers for — this lets you score report quality
honestly when Gate 5 runs.

**Checkpoint:** `evals/benchmark_prompts.json` exists with at least 10 prompts.

---

## Step 5 — Create .env.example and .gitignore

**.env.example** (commit this):

```bash
# Claude API — required, no default
ANTHROPIC_API_KEY=

# CloakBrowser CDP
CLOAK_CDP_URL=http://localhost:9222

# Data layer
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379

# Proxy (for high bot-risk sources)
PROXY_URL=
PROXY_USER=
PROXY_PASS=

# Agent behavior
MAX_STEPS_PER_JOB=20
MAX_TOKENS_PER_JOB=50000
LOG_LEVEL=INFO

# Frontend (set in Vercel environment, not here)
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
```

**.gitignore** (commit this):

```
.env
.env.local
.env.*.local
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.coverage
.vscode/
.idea/
.DS_Store
Thumbs.db
playwright-report/
test-results/
screenshots/
.next/
node_modules/
```

**Checkpoint:** Both files committed. `.env` confirmed absent from git tracking.

---

## Step 6 — Open Claude Code in VSCode

With Steps 1–5 complete:

```
/start
```

Syntaris loads memory files, detects fresh project, prompts for recipe and CONTRACT.md.

**Recipe selection:** `bring-your-own`
Use `nextjs-fastapi-supabase` as a structural reference but customize for this stack —
GhostResearcher has no Supabase dependency and adds the agent/executor/synthesizer layers.

---

## Step 7 — Run These Skills Before Gate 1 Closes

**`/build-rules`** — full interrogation of constraints. Specifically address:
- Token budget per research job (cost ceiling before you write the planner loop)
- Max steps per job (hard limit, not a soft suggestion)
- What counts as "sufficient coverage" for finalize_report confidence threshold

**`/critical-thinker`** — challenge every significant architectural decision.
Ask it to pressure-test specifically:
- The `finalize_report` as tool (vs. stop_reason="end_turn") decision
- SSE vs. polling for frontend job status (polling storm failure mode)
- Context window management strategy for long research sessions
- Whether credibility scoring needs a trained model or if a scoring function suffices

**`/costs`** — Claude API is the primary cost driver here, not compute.
Set a per-job token budget and a monthly API cost ceiling before the planner loop exists.
A runaway research job with no token limit will drain your API budget fast.

**`/security`** — ANTHROPIC_API_KEY is now in the mix alongside proxy credentials
and a shared database. Get the OWASP checklist before Gate 1 closes.

---

## Step 8 — Fill Out core/CONTRACT.md

```
Project name: GhostResearcher
Stack: Claude API (tool use) / CloakBrowser / FastAPI / Redis / Postgres / Next.js 14
Purpose: Agentic web research engine — planner + executor + synthesizer
Repo: https://github.com/PCSchmidt/ghost-researcher
Related: SkySigint (CDP pattern reference), CloakBrowser, Syntaris, AeroIntel
Backend deploy: Railway (cloakserve + ghostresearcher-api)
Frontend deploy: Vercel
Cost ceiling per job: [set from /costs output]
Monthly API ceiling: [set from /costs output]
Banned approaches:
  - Per-request CloakBrowser launches (persistent cloakserve only)
  - Sharing cloakserve with SkySigint
  - Free-text planner output (must be tool calls only)
  - Report claims not traceable to extracted session sources
  - Skipping Gate 2 tools.py lock before writing any executor code
  - Committing .env or ANTHROPIC_API_KEY
```

---

## Step 9 — Produce AGENT_SPEC.md (Gate 1 Critical Exit Artifact)

This is the most important document in the project. Gate 1 does not close without it.
Run `/critical-thinker` against a draft before finalizing.

It must define:

**Planner system prompt contract** — what the planner knows, what it must output,
termination conditions (max_steps, confidence threshold, no_new_sources),
cost guard (max tokens per job).

**All 5 tool schemas** — input schema, output schema, error contract for each tool.
The seed is in CLAUDE.md under "Tool Definitions." Expand with full output schemas
and explicit error cases (e.g. navigate_to_url when CloakBrowser returns detection_blocked).

**AgentSession state schema** — every field tracked across the research session:
research_goal, steps_taken, sources_visited (set for deduplication), running_cost,
detection_events, termination_state, termination_reason.

**Failure mode catalog** — all 6 failure modes from CLAUDE.md documented with
detection condition, mitigation, and which ERRORS.md entry they map to.

**Checkpoint:** `core/AGENT_SPEC.md` exists, complete, reviewed by `/critical-thinker`.

---

## Step 10 — Gate 2: Lock tools.py Before Any Executor Code

After Gate 1 closes, the next action is completing `backend/agent/tools.py`.
This is a schema-only file — no implementation. Every tool from AGENT_SPEC.md
expressed as a Python structure matching the Claude API tool use format.

Gate 2 hook fails if:
- `tools.py` does not exist
- Any tool is missing `input_schema`
- Any tool has `NotImplemented`, `pass`, or `...` stubs

Run `/testing` to generate schema validation tests before Gate 2 closes.

**After Gate 2: you may begin writing `backend/executor/browser.py`.**

---

## Gate Checklist

| Gate | Exit Artifacts | Human Token |
|---|---|---|
| 1 | CONTRACT.md, AGENT_SPEC.md, SPEC.md, evals/benchmark_prompts.json | CONFIRMED |
| 2 | backend/agent/tools.py (complete schemas) | TOOLS CONFIRMED |
| 3 | pytest passes, all test_executor/ + test_agent/ | TESTS CONFIRMED |
| 4 | Planner produces valid sequences for 3 benchmark prompts | PLANNER CONFIRMED |
| 5 | 3 reports in evals/results/, scored | REPORTS CONFIRMED |
| GO | Railway + Vercel deployed, /health 200 | DEPLOY CONFIRMED |

---

## Files That Must Exist Before First Claude Code Session

- [x] `README.md`
- [x] `CLAUDE.md`
- [x] `SETUP.md`
- [ ] `evals/benchmark_prompts.json` — 10 prompts (Step 4)
- [ ] `.env.example` — committed (Step 5)
- [ ] `.gitignore` — committed (Step 5)
- [ ] Syntaris installed → `.claude/` and `core/` exist (Step 2)
