# CONTRACT.md

Project name: GhostResearcher  
Stack: OpenRouter model gateway / optional Anthropic fallback / CloakBrowser / FastAPI / Redis / Postgres / Next.js 14
Purpose: Agentic web research engine - planner + executor + synthesizer  
Repo: [PCSchmidt/ghost-researcher](https://github.com/PCSchmidt/ghost-researcher)  
Related: SkySigint (CDP pattern reference), CloakBrowser, Syntaris, AeroIntel  
Backend deploy: Railway (cloakserve + ghostresearcher-api)  
Frontend deploy: Vercel  
Cost ceiling per job: hard stop at `$0.05` model spend; warn at `$0.02`
Monthly API ceiling: `$25` development, `$75` launch warning, `$200` scale warning
Default model route: OpenRouter default tier (`deepseek/deepseek-v4-flash` or configured equivalent)
Fallback model route: OpenRouter quality tier; Anthropic only as an explicit premium fallback

Banned approaches:

- Per-request CloakBrowser launches (persistent cloakserve only)
- Sharing cloakserve with SkySigint
- Free-text planner output (must be tool calls only)
- Report claims not traceable to extracted session sources
- Skipping Gate 2 tools.py lock before writing any executor code
- Committing .env or ANTHROPIC_API_KEY
- Using premium Anthropic models as the default planner/synthesizer path
- Making model calls without recording model slug, token usage, and reported cost
