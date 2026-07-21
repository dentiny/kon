---
description: Code review only — Mio runs strict-review on uncommitted or staged diff. No implementation.
disable-model-invocation: true
---

User invoked `/kon:review` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:review`.
Read `$KON_ROOT/commands/review.md` and run the full orchestration flow. Do not answer directly.
