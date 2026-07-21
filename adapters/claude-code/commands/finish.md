---
description: Mark the current session as completed. Called explicitly by the user when they are satisfied with the work done. Equivalent to clicking ✓ in the dashboard.
disable-model-invocation: true
---

User invoked `/kon:finish` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:finish`.
Read `$KON_ROOT/commands/finish.md` and run the full orchestration flow. Do not answer directly.
