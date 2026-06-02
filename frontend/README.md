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

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
