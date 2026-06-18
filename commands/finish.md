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

1. **Orchestrator** — find the most recent `in_progress` or `waiting` session for this project in `~/.kon/projects/<repo-name>/sessions/` (also checks legacy paths):
   ```bash
   python3 -c "
   import json, pathlib, datetime, os, sys
   root = pathlib.Path(os.environ.get('KON_ROOT', pathlib.Path.home() / 'Desktop/kon')).expanduser()
   sys.path.insert(0, str(root / 'hooks'))
   from _kon_paths import iter_sessions_dirs, legacy_sessions_dir, resolve_project_path
   project = str(resolve_project_path())
   seen = set()
   for d in iter_sessions_dirs('.'):
       for p in sorted(d.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
           d_data = json.loads(p.read_text())
           sid = d_data.get('id', p.stem)
           if sid in seen:
               continue
           seen.add(sid)
           if d != legacy_sessions_dir() and d_data.get('project_path', project) != project:
               continue
           if d_data.get('status') in ('in_progress', 'waiting'):
               d_data['status'] = 'completed'
               d_data['log'].append({'ts': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                     'agent': 'User', 'summary': 'Session closed by user.'})
               p.write_text(json.dumps(d_data, indent=2, ensure_ascii=False))
               print('Closed:', d_data['id'])
               break
       else:
           continue
       break
   else:
       print('No open session found.')
   "
   ```

2. **Orchestrator** — confirm to the user: "Session closed. Changes are uncommitted — review with `git diff` and commit when ready."

## Orchestrator rules

- **Do not run `git commit`** — closing a session never triggers a commit
- If no open session exists, print a friendly message and exit
