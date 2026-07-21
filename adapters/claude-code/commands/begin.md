---
description: Start an interactive kon session. Plain chat is routed by intent — no /kon: prefix needed until /kon:finish.
argument-hint: [goal]
disable-model-invocation: true
---

User invoked `/kon:begin` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:begin`.
Read `$KON_ROOT/commands/begin.md` and run the full orchestration flow. Do not answer directly.
