# CONTRACT.md

Project name: GhostResearcher  
Stack: Claude API (tool use) / CloakBrowser / FastAPI / Redis / Postgres / Next.js 14  
Purpose: Agentic web research engine - planner + executor + synthesizer  
Repo: [PCSchmidt/ghost-researcher](https://github.com/PCSchmidt/ghost-researcher)  
Related: SkySigint (CDP pattern reference), CloakBrowser, Syntaris, AeroIntel  
Backend deploy: Railway (cloakserve + ghostresearcher-api)  
Frontend deploy: Vercel  
Cost ceiling per job: TBD via /costs; temporary guard rail is MAX_TOKENS_PER_JOB=50000  
Monthly API ceiling: TBD via /costs before Gate 1 close

Banned approaches:

- Per-request CloakBrowser launches (persistent cloakserve only)
- Sharing cloakserve with SkySigint
- Free-text planner output (must be tool calls only)
- Report claims not traceable to extracted session sources
- Skipping Gate 2 tools.py lock before writing any executor code
- Committing .env or ANTHROPIC_API_KEY
