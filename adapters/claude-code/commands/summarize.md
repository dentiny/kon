---
description: Write a clean session summary. Called automatically at the end of every run, or on-demand to summarize a past session.
disable-model-invocation: true
---

User invoked `/kon:summarize` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:summarize`.
Read `$KON_ROOT/commands/summarize.md` and run the full orchestration flow. Do not answer directly.
