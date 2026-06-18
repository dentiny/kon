---
description: Project todo list — add tasks to .kon/todos.json; view and manage in the dashboard.
---

# /kon:todo

Track tasks in **`.kon/todos.json`** (project-local, readable and committable). Manage items from chat or the session dashboard **Todos** tab (mark done, delete, reopen).

No agent spawn — the orchestrator runs `scripts/kon_todo.py` directly.

## Usage

```
/kon:todo <task description>              # add (default)
/kon:todo add <task description>
/kon:todo list
/kon:todo list --open
/kon:todo done <id>
/kon:todo open <id>                       # reopen
/kon:todo delete <id>
```

Examples:

```
/kon:todo add rate limiting to the API
/kon:todo fix dashboard session delete bug
/kon:todo list
/kon:todo done 20260618-120000-rate-limiting
```

## Storage

| File | Purpose |
|------|---------|
| `.kon/todos.json` | Canonical todo store for this project |

Schema:

```json
{
  "version": 1,
  "items": [
    {
      "id": "20260618-120000-rate-limiting",
      "text": "add rate limiting to the API",
      "status": "open",
      "created_at": "2026-06-18T12:00:00Z",
      "completed_at": null
    }
  ]
}
```

## Flow

1. **Orchestrator** — parse subcommand (default `add` when the first token is not a known verb).
2. **Run CLI:**
   ```bash
   python3 $KON_ROOT/scripts/kon_todo.py add --text "<description>"
   python3 $KON_ROOT/scripts/kon_todo.py list [--status open|done|all]
   python3 $KON_ROOT/scripts/kon_todo.py done --id <id>
   python3 $KON_ROOT/scripts/kon_todo.py open --id <id>
   python3 $KON_ROOT/scripts/kon_todo.py delete --id <id>
   ```
3. **Orchestrator** — print result (new id on add; table on list). Mention dashboard **Todos** tab for UI management.

## Dashboard

```bash
python3 $KON_ROOT/scripts/dashboard.py --open
```

Open the **Todos** tab — mark done (✓), reopen (↩), delete (🗑). Refreshes every 3 seconds.

With `--project /path/to/repo`, only that project's todos are shown.

## Orchestrator rules

- **No session JSON required** — todos are not agent pipeline runs.
- **Skip teammate-flow** — no agents, no quality checks.
- **Do not run `git commit` or `git push`**
- During `/kon:begin`, plain-text like "remind me to …" → run `kon_todo.py add` on the active project (same as `/kon:todo`).

## Comparison

| Item | `/kon:todo` | `/kon:go` |
|------|-------------|-----------|
| Writes code | ❌ | ✅ |
| Artifact | `.kon/todos.json` | plan + code |
| Agents | ❌ | full team |
| Dashboard UI | ✅ Todos tab | ✅ Sessions tab |
