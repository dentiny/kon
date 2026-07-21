---
description: External lookup — Jun searches docs and the web, writes .kon/research.md. Read-only for source code; session tracked.
argument-hint: <question>
disable-model-invocation: true
---

User invoked `/kon:research` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:research`.
Read `$KON_ROOT/commands/research.md` and run the full orchestration flow. Do not answer directly.
