---
description: Toggle caveman output compression for the current session. Applies to orchestrator chat and Ui narration only — artifact files (plan.md, review.md, etc.) are never compressed.
---

# /kon:caveman

Activate or deactivate caveman-style output compression.

```
/caveman           → full (default)
/caveman lite      → drop filler, keep articles and full sentences
/caveman full      → drop articles, fragments OK, short synonyms
/caveman ultra     → maximum compression, arrows for causality
normal mode        → deactivate, revert to default prose
```

Follow [`skills/caveman`](../skills/caveman/SKILL.md) for all rules.

## What compresses

- Orchestrator chat responses
- 🌸 Ui narration beats (opening, closing, stuck-point)
- Agent status summaries in chat

## What never compresses

- Structured artifact files: `plan.md`, `review.md`, `debug.md`, `summary.md`
- Mio's 7-item checklist (exact phrases required by hooks)
- `## Decisions needed` / `## Blocked` sections
- Code blocks, file paths, CLI commands, error strings
- Irreversible action confirmations

Level persists for the rest of the session.
