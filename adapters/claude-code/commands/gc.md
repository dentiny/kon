---
description: Garbage-collect the codebase — Sawako identifies dead code, redundant comments, and bloated docs, presents an inventory for user confirmation, then cleans up. Mio reviews.
argument-hint: [target]
disable-model-invocation: true
---

User invoked `/kon:gc` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:gc`.
Read `$KON_ROOT/commands/gc.md` and run the full orchestration flow. Do not answer directly.
