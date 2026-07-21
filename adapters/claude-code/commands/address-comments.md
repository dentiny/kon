---
description: Fetch review comments on the current branch's PR, triage with the user, route each item to /kon:quick or /kon:team, implement one work item at a time. Blocks if no PR.
disable-model-invocation: true
---

User invoked `/kon:address-comments` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:address-comments`.
Read `$KON_ROOT/commands/address-comments.md` and run the full orchestration flow. Do not answer directly.
