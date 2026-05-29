# MEMORY_CORRECTIONS.md

Blueprint v11 | Reflexion Entries and Estimation Calibration

New entries added ABOVE previous, newest first.
Used by build-rules.md to calibrate future estimates.

## REFLEXION LOG

Format per entry:

```text
## REFLEXION: v[X.X.X] -- [Gate Name]
Date: [date]
Project: [name]
ESTIMATE: Predicted [X] hrs, Actual [X] hrs, Variance [+/-X]%
TECHNICAL PREDICTIONS VS REALITY: [what was expected vs what happened]
CORRECTION FOR FUTURE: [what changes]
MEMORY_SEMANTIC.md UPDATE: [pattern added/updated or none]
```

## ESTIMATION CALIBRATION LOG

## REFLEXION: Gate 1 -- Contract and Agent Spec

Date: 2026-05-29
Project: GhostResearcher
ESTIMATE: Predicted n/a, Actual n/a, Variance n/a
TECHNICAL PREDICTIONS VS REALITY: Initial prototype assumed direct Anthropic planner/synthesizer calls. Cost review showed OpenRouter can provide cheaper capable models with one OpenAI-compatible API surface, usage metadata, fallback routing, tool calling, and structured outputs.
CORRECTION FOR FUTURE: Decide provider gateway and dollar ceilings before implementing the model adapter. Treat premium frontier models as explicit fallback, not default runtime.
MEMORY_SEMANTIC.md UPDATE: PAT-001 added.

---

## PRE-FILL ACCURACY LOG

[Empty until first interrogation with pre-fills]
