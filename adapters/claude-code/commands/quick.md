---
description: Lightweight task entry point. Orchestrator calls Yui directly for small changes, skips Azusa / Mugi, Yui finishes and runs lightweight Mio (3-item checklist subset).
argument-hint: <task>
disable-model-invocation: true
---

User invoked `/kon:quick` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:quick`.
Read `$KON_ROOT/commands/quick.md` and run the full orchestration flow. Do not answer directly.
