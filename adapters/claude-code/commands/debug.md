---
description: Bug investigation pipeline — reproduce with runtime evidence before fixing. Azusa investigates, Mugi proposes multiple fixes, user approves, then Yui implements. Mio reviews.
argument-hint: <bug>
disable-model-invocation: true
---

User invoked `/kon:debug` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:debug`.
Read `$KON_ROOT/commands/debug.md` and run the full orchestration flow. Do not answer directly.
