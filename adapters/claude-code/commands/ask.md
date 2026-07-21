---
description: Read-only Q&A about the codebase. Azusa investigates and answers — zero repo writes (no code, no .kon/ artifacts); session JSON is tracked under ~/.kon/projects/.
argument-hint: <question>
disable-model-invocation: true
---

User invoked `/kon:ask` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:ask`.
Read `$KON_ROOT/commands/ask.md` and run the full orchestration flow. Do not answer directly.
