---
description: Project todo list — add tasks to .kon/todos.json; view and manage in the dashboard.
argument-hint: <task>
disable-model-invocation: true
---

User invoked `/kon:todo` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:todo`.
Read `$KON_ROOT/commands/todo.md` and run the full orchestration flow. Do not answer directly.
