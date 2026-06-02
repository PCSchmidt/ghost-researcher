# GhostResearcher Frontend

Next.js App Router workbench for submitting GhostResearcher jobs and inspecting
status events, sources, credibility scores, and synthesized reports.

## Setup

```bash
npm install
```

The UI defaults to the local backend at `http://localhost:8000`. Override it with:

```bash
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
```

The FastAPI backend must include the frontend origin in `CORS_ALLOWED_ORIGINS`.

## Run

```bash
npm run dev
```

Open `http://localhost:3000`.

## Validate

```bash
npm run lint
npm test
npm run build
```

Current validated baseline: lint clean, 8 Vitest tests passing, production build passing.

## Deployment Target

The frontend deployment target is Vercel. Deployment is planned after v0.17 live
integration smoke tests verify the configured backend, search provider,
OpenRouter, and CloakBrowser paths.

See [../README.md](../README.md) and [../SETUP.md](../SETUP.md) for the current
project checkpoint and full validation baseline.
