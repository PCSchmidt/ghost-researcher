# SPEC_GATES.md

Blueprint v11 | Gate Plan

## Gate Sequence

### v0.1.0 - Foundation + Agent Contract

- Contract, AGENT_SPEC, memory files, ERRORS, benchmark prompts
- Exit token: `CONFIRMED`

### v0.2.0 - Tool Interface Lock

- `backend/agent/tools.py` complete, schema only, no stubs
- Exit token: `TOOLS CONFIRMED`

### v0.3.0 - Executor Unit Tests

- Browser connection manager, executor slices, and unit tests pass
- Exit token: `TESTS CONFIRMED`

### v0.4.0 - Planner Integration

- Planner generates valid tool call sequences for benchmark prompts
- Exit token: `PLANNER CONFIRMED`

### v0.5.0 - End-to-End Reports

- Complete reports generated and scored into `evals/results/`
- Exit token: `REPORTS CONFIRMED`

### v1.0.0 - Deployment

- Railway backend and Vercel frontend deployed with healthy status endpoints
- Exit token: `DEPLOY CONFIRMED`
