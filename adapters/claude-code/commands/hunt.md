---
description: Read-only bug hunt — Azusa analyzes bugs from source code and suggests best-effort repro SQL/tests. No fixes, no repo writes.
argument-hint: <bug>
disable-model-invocation: true
---

User invoked `/kon:hunt` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:hunt`.
Read `$KON_ROOT/commands/hunt.md` and run the full orchestration flow. Do not answer directly.
