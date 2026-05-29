# COSTS.md

Blueprint v11 | GhostResearcher Cost Plan  
Created: 2026-05-29

---

## Cost Policy

Primary model access should go through OpenRouter, not direct Anthropic, for MVP
planning and synthesis. Anthropic models remain an optional premium fallback, but
must not be the default path.

Hard ceilings:

- Per research job hard ceiling: `$0.05` model spend
- Per research job warning threshold: `$0.02` model spend
- Development monthly API ceiling: `$25`
- Launch monthly API warning threshold: `$75`
- Scale monthly API warning threshold: `$200`

Runtime rules:

- Track model cost from provider usage metadata whenever available.
- Stop or downgrade before a request that would exceed the per-job hard ceiling.
- Prefer cheaper default models for planner routing, extraction normalization, and
  draft synthesis.
- Escalate to stronger models only when the cheaper model fails validation or the
  task requires deeper reasoning.
- Log model slug, prompt tokens, completion tokens, and reported cost for every
  planner and synthesizer call.

---

## Model Routing Plan

| Tier | Purpose | Candidate models | Notes |
| --- | --- | --- | --- |
| Default | Planner tool selection and normal synthesis | `deepseek/deepseek-v4-flash`, `qwen/qwen3-235b-a22b-2507` | Very low token cost; suitable first path for this scope. |
| Quality fallback | Harder synthesis, ambiguous source comparison, failed JSON/tool-call validation | `deepseek/deepseek-v4-pro`, `moonshotai/kimi-k2.6`, `moonshotai/kimi-k2-thinking` | Use only after validation failure or complex reasoning trigger. |
| Premium fallback | Last resort for high-stakes or repeated failures | `anthropic/claude-sonnet-latest` or explicit Anthropic direct adapter | Disabled by default; must be intentionally configured. |

OpenRouter supports OpenAI-compatible chat completions, tool calling, structured
outputs, model fallback routing, and response usage metadata. The implementation
should use a provider abstraction so model slugs stay configuration, not business
logic.

---

## Build Costs

| Gate | API Tokens | Estimated Cost | Hours | Total |
| --- | --- | --- | --- | --- |
| v0.8.0 Search Tool Skeleton | 0 runtime model tokens expected | `$0` | TBD | TBD |
| v0.9.0 OpenRouter Planner Adapter | 50k-150k test/eval tokens | `< $1` with default tier | TBD | TBD |
| v0.10.0 Synthesizer Skeleton | 100k-300k test/eval tokens | `< $3` with default/fallback mix | TBD | TBD |

---

## Operational Costs

Assumption for early estimates: 5 research jobs per active user per month.
Average model cost target: `$0.01` per completed job. Hard max model cost:
`$0.05` per completed job.

| Service | Free Tier | At 100 users | At 1000 users | At 10000 users |
| --- | --- | --- | --- | --- |
| OpenRouter model calls | Pay per token | `$5 avg / $25 hard-max` | `$50 avg / $250 hard-max` | `$500 avg / $2500 hard-max` |
| Railway backend + cloakserve | Limited/free varies | `$10-$25` | `$25-$75` | `$150+` |
| Postgres + Redis | Free/dev tiers vary | `$0-$25` | `$25-$100` | `$200+` |
| Vercel frontend | Free hobby tier | `$0` | `$0-$20` | `$20+` |

The model plan keeps development under the `$25/month` soft warning threshold
when traffic is limited to test/eval usage. At real launch traffic, the product
must enforce job quotas or billing before public access.

---

## Cost Review Outcome

Decision: adopt OpenRouter as the default model gateway before implementing the
planner adapter. This reduces vendor lock-in and makes low-cost model routing a
first-class part of the architecture.

Risk accepted: tool-call and structured-output behavior varies by model. The
mitigation is strict output validation plus fallback escalation only when needed.
