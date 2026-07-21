---
description: Summarize a GitHub issue and all discussion comments. Jun only, read-only. Writes sessions/<id>/issue-summary.md.
argument-hint: <#>
disable-model-invocation: true
---

User invoked `/kon:describe-issue` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:describe-issue`.
Read `$KON_ROOT/commands/describe-issue.md` and run the full orchestration flow. Do not answer directly.
