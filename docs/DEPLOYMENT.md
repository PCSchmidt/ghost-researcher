# v1.0.0 Deployment Guide: GhostResearcher

This document details the configuration, deployment, health verification, and rollback procedures for the v1.0.0 GhostResearcher stack across Railway and Vercel.

## 1. System Architecture

The GhostResearcher v1.0.0 stack runs on three primary nodes:

-   **Backend API (`ghostresearcher-api`)**: Python 3.11+ FastAPI service handling LLM orchestration, openrouter integration, and job queues. (Deployed to Railway)
-   **CloakBrowser Server (`cloakserve`)**: CDP server fronting CloakBrowser's patched stealth Chromium (v1.2.1; `CLOAKSERVE_STEALTH=0` falls back to vanilla Chromium for baselines). (Deployed to Railway)
-   **Frontend App**: Next.js 16 App Router UI. (Deployed to Vercel)

---

## 2. Environment Variables

### Backend (Railway)
Ensure the following variables are configured in both Railway services where applicable:

| Variable | Description | Required? | Default |
| :--- | :--- | :--- | :--- |
| `OPENROUTER_API_KEY` | OpenRouter access token for planner/synth orchestration. | Yes | None |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | No | `https://openrouter.ai/api/v1` |
| `CLOAK_CDP_URL` | Internal Railway URL pointing to `cloakserve` on port 9222. | Yes | `http://cloakserve.railway.internal:9222` |
| `DEFAULT_PLANNER_MODEL` | Default LLM for logical planning. | No | `deepseek/deepseek-v4-flash` |
| `SEARCH_PROVIDER` | `deterministic` for offline/evals or `brave` for live web searches. | No | `deterministic` |
| `SEARCH_API_KEY` | Brave API Key if `SEARCH_PROVIDER=brave` | Conditional | None |
| `PORT` | Public port the API binds to (assigned by Railway automatically). | No | `8000` |
| `MAX_STEPS_PER_JOB` | Hard limit for agent planner execution loop. | No | `20` |

### Frontend (Vercel)
Ensure the following is configured in your Vercel Project Settings:

| Variable | Description | Required? |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Public URL of the FastAPI Railway service (e.g. `https://api.ghostresearcher.up.railway.app`). | Yes |

---

## 3. Infrastructure Configuration

### 3.1 Railway Setup (`cloakserve` and `ghostresearcher-api`)
1. Create a new Railway project.
2. Select **Deploy from GitHub repo** -> `ghost-researcher`.
3. Add **two separate services** from the same github repository.

**Service 1: `cloakserve`**
*   **Build/Root Directory:** `/`
*   **Dockerfile Path:** `docker/Dockerfile.cloak`
*   **Start Command:** Uses native CMD from Dockerfile.
*   **Networking:** Expose port `9222`. Ensure this is exposed to the private Railway network.
*   **Stealth (v1.2.1):** the image installs `cloakbrowser` and pre-downloads its patched stealth Chromium; `start_cloakserve.py` launches it by default (`CLOAKSERVE_STEALTH=1`). Set `CLOAKSERVE_STEALTH=0` to launch vanilla Chromium for a detection baseline. The image is ~5 GB, so the first build/deploy is slow.

**Service 2: `ghostresearcher-api`**
*   **Build/Root Directory:** `/`
*   **Dockerfile Path:** `Dockerfile`
*   **Start Command:** Uses native CMD from Dockerfile.
*   **Networking:** Generate a Public Domain (e.g. `https://api.ghostresearcher.app`). Use this in your Vercel frontend.
*   **Healthcheck Route:** set to `/health`.

### 3.2 Vercel Setup (Frontend)
1. Go to Vercel and create a new project targeting `ghost-researcher`.
2. Set the **Root Directory** to `frontend/`.
3. Select **Next.js** framework preset.
4. Input your `NEXT_PUBLIC_API_URL` pointing to the public URL for `ghostresearcher-api`.
5. Deploy.

---

## 4. Health Checks

### API Readiness
After deployment, verify the backend structure via the `/health` endpoint:

```bash
curl -X GET https://<YOUR_RAILWAY_API_DOMAIN>/health
```
**Expected Response Sequence:**
```json
{
  "status": "ok",
  "service": "ghostresearcher-api",
  "version": "0.1.0",
  "dependencies": {
    "anthropic": "missing",
    "cloak_cdp": {
      "status": "healthy",
      "version": "Browser/124.0.0.0"
    },
    "database": "missing",
    "redis": "missing"
  },
  "limits": {
    "max_steps_per_job": 20,
    "max_tokens_per_job": 50000
  }
}
```

*Crucial Step:* If `dependencies.cloak_cdp.status` returns anything other than `healthy`, the `ghostresearcher-api` service cannot resolve the internal `CLOAK_CDP_URL`. Confirm Railway internal networking aliases.

---

## 5. Rollback Procedures

### Rollback Triggers
Initiate a rollback if:
1. Railway healthchecks fail for >3 consecutive redeploy attempts.
2. The SSE streams fail on the Vercel frontend resulting in perpetual stalling immediately after `POST /research`.
3. `cloakserve` exhibits zombies/memory-leaking from unclosed CDP connections causing OOM kills on Railway.

### How to Rollback
1. **Frontend (Vercel):** Navigate to the Deployments tab of the Vercel dashboard and click **Promote to Production** on the latest stable `v0.17` commit.
2. **Backend (Railway):** Navigate to the project dashboard. Locate the previous successful deployment and click the **Rollback** / **Redeploy** button.
3. If memory leaks occur on `cloakserve`, set a manual restart policy via crontab or Railway instance refresh limit before downgrading entirely.

---

## 6. Live Validation Run On Railway

Run the live eval from a Railway shell or one-off job attached to `ghostresearcher-api`, not from a local workstation.

Use the internal CloakBrowser hostname that only resolves inside Railway:

```bash
SEARCH_PROVIDER=brave SEARCH_API_KEY=... OPENROUTER_API_KEY=... CLOAK_CDP_URL=http://cloakbrowser.railway.internal:9222 python -m evals.eval_runner --mode live --limit 3
```

Expected behavior:
- the eval runner performs a CloakBrowser readiness probe first
- a healthy Railway run writes a JSON artifact under `evals/results/`
- `live_environment.cloakbrowser.status` should report `ok`
- if Railway networking is wrong, the run should fail fast with a clear preflight error instead of a partial benchmark artifact

The CLI loads configuration from the project-root `.env` merged with the process
environment (process environment wins). `SEARCH_PROVIDER`, `SEARCH_API_KEY`,
`OPENROUTER_API_KEY`, `CLOAK_CDP_URL`, and `SCRAPE_ENABLED` must be set.

### Local live run (alternative)

The Railway-internal CDP hostname does not resolve off-network, so to run the
live eval locally, start CloakBrowser locally and override `CLOAK_CDP_URL` to point
at it (the process-environment override beats the `.env` value):

```bash
docker compose -f docker/docker-compose.yml up -d cloakserve
```

```powershell
# PowerShell
$env:CLOAK_CDP_URL = "http://localhost:9222"
python -m evals.eval_runner --mode live --limit 3
```

The discriminating quality score lives in `average_quality_score` /
`quality_score` (live artifacts are labeled `harness_kind: quality`); offline
artifacts are a regression harness (`harness_kind: regression`).

## 7. CloakBrowser Stealth Block-Rate Measurement (v1.2.1)

The decisive proof that the stealth swap defeats Cloudflare is a datacenter-IP
before/after, because the production block is IP/ASN-driven (it does not reproduce
from a residential IP). Run [evals/blocked_rate.py](../evals/blocked_rate.py) from a
shell on `ghostresearcher-api` (it navigates the real targets that returned
Cloudflare walls in the first production run):

```bash
# after: stealth (the new default)
python -m evals.blocked_rate --label stealth-railway

# before: baseline — set CLOAKSERVE_STEALTH=0 on the cloakserve service, redeploy,
# run, then revert
python -m evals.blocked_rate --label vanilla-railway
```

A successful unblock shows `block_rate` dropping (and `usable_rate` rising) from the
vanilla baseline to the stealth run. If blocking persists despite stealth, the cause
is the datacenter IP, and a residential/mobile proxy is the next lever (DEC-010): set
`PROXY_URL` on `cloakserve`.

## 8. Build Watch Paths (stop rebuilding cloakserve on every push)

Both services build from the same repo, so by default *any* push to `main` rebuilds
both — including the ~5 GB `cloakserve` image — even for API-only or docs-only
changes. Per-service watch paths fix this. The repo ships two config-as-code files
with only `build.watchPatterns` (they merge with, and do not override, dashboard
build settings):

- [railway.cloak.json](../railway.cloak.json) — rebuild `CloakBrowser` only on
  `docker/Dockerfile.cloak`, `backend/scripts/start_cloakserve.py`, or
  `requirements.txt` changes
- [railway.api.json](../railway.api.json) — rebuild `ghost-researcher` on
  `backend/**`, `evals/**`, `Dockerfile`, or `requirements.txt` changes

One-time setup: in the Railway dashboard, for each service open **Settings →
Config-as-code** and set the config file path:

- `ghost-researcher` → `railway.api.json`
- `CloakBrowser` → `railway.cloak.json`

After that, docs- and API-only changes no longer trigger the slow `cloakserve`
rebuild.
