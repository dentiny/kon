---
name: kon
description: >
  Multi-agent software engineering workflow. Use when the user mentions /kon:
  commands in plain text — including /kon:team, /kon:design, /kon:quick,
  /kon:debug, /kon:ask, /kon:review, /kon:review-pr, /kon:hunt, /kon:gc,
  /kon:research, /kon:describe-issue, /kon:begin, /kon:finish, /kon:summarize,
  /kon:retro, /kon:address-comments, /kon:todo, /kon:understand-codebase.
  Prefer the explicit /kon:<command> slash commands when available.
---

# kon — Multi-Agent Workflow

When the user invokes any `/kon:*` command (slash command or plain text), **stop answering directly** and run the orchestration flow.

Read and follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for the active command.

Resolve `KON_ROOT` once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```
