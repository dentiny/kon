---
description: Mark the current session as completed. Called explicitly by the user when they are satisfied with the work done. Equivalent to clicking ✓ in the dashboard.
---

# /kon:finish

Mark the current session as done.

Agents finishing their work does not close a session — the session stays in `waiting`
state until the user explicitly closes it. This gives time to review changes, run
extra commands, or ask for more work before declaring the task complete.

## Usage

```
/kon:finish
```

## Flow

1. **Orchestrator** — find the most recent `in_progress` or `waiting` session in `.kon/sessions/`:
   ```bash
   python3 -c "
   import json, pathlib, datetime
   sessions = sorted(pathlib.Path('.kon/sessions').glob('*.json'),
                     key=lambda p: p.stat().st_mtime, reverse=True)
   for p in sessions:
       d = json.loads(p.read_text())
       if d.get('status') in ('in_progress', 'waiting'):
           d['status'] = 'completed'
           d['log'].append({'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'agent': 'User', 'summary': 'Session closed by user.'})
           p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
           print('Closed:', d['id'])
           break
   else:
       print('No open session found.')
   "
   ```

2. **Orchestrator** — confirm to the user: "Session closed. Changes are uncommitted — review with `git diff` and commit when ready."

## Orchestrator rules

- **Do not run `git commit`** — closing a session never triggers a commit
- If no open session exists, print a friendly message and exit
