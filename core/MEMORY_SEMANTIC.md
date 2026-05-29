# MEMORY_SEMANTIC.md

Blueprint v11 | Persistent Patterns Across Projects

Updated at gate close when a pattern is validated or invalidated.

## PATTERNS

Format:

```text
### PAT-[NNN]: [title]
Confidence: LOW | MEDIUM | HIGH
Source: [project where first observed]
Description: [pattern]
Last validated: [date]
```

### PAT-001: Provider-Neutral Model Adapter Before LLM Implementation

Confidence: HIGH
Source: GhostResearcher
Description: Lock model routing and cost telemetry before implementing the planner adapter. Use OpenRouter as the default gateway, keep model slugs configurable, and validate tool-call/JSON output before accepting planner results.
Last validated: 2026-05-29
