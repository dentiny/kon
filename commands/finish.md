---
description: Mark the current session as completed. Called explicitly by the user when they are satisfied with the work done. Equivalent to clicking ✓ in the dashboard.
---

# /kon:finish

Mark the current session as done — especially **`/kon:begin` interactive sessions**, which stay open until you explicitly finish.

Pipeline commands also stay in `waiting` until closed; one-shot commands auto-complete and rarely need `/kon:finish`.

## Usage

```
/kon:finish
```

## Flow

1. **Orchestrator** — close the most recent open session for this project:

   ```bash
   python3 $KON_ROOT/scripts/kon_session.py finish --project .
   ```

   Optional: `--id <session-id>` to close a specific session; `--summary "…"` to customize the log line.

   Exits 0 and prints the session id on success. Exits non-zero with `no open session found` if nothing to close.

2. **Orchestrator** — confirm to the user: "Session closed. Changes are uncommitted — review with `git diff` and commit when ready."

## Orchestrator rules

- **Do not run `git commit`** — closing a session never triggers a commit
- If no open session exists, print a friendly message and exit
- Works with session directory layout (`sessions/<id>/session.json`)
