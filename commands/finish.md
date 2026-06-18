---
description: Mark the current session as completed. Called explicitly by the user when they are satisfied with the work done. Equivalent to clicking ✓ in the dashboard.
---

# /kon:finish

Mark the current session as done.

Mark the current session as done — especially **`/kon:begin` interactive sessions**, which stay open until you explicitly finish.

Pipeline commands also stay in `waiting` until closed; one-shot commands auto-complete and rarely need `/kon:finish`.

## Usage

```
/kon:finish
```

## Flow

1. **Orchestrator** — find the most recent `in_progress` or `waiting` session for this project in `~/.kon/projects/<repo-name>/sessions/`:
   ```bash
   python3 -c "
   import json, pathlib, datetime, os, sys, subprocess
   bundled = pathlib.Path.home() / '.kon/lib/_kon_paths.py'
   if os.environ.get('KON_ROOT'):
       root = pathlib.Path(os.environ['KON_ROOT']).expanduser().resolve()
   elif bundled.is_file():
       root = pathlib.Path(subprocess.check_output(['python3', str(bundled), 'root'], text=True).strip())
   else:
       root = pathlib.Path.home() / 'Desktop/kon'
   sys.path.insert(0, str(root / 'hooks'))
   from _kon_paths import sessions_dir, resolve_project_path
   project = str(resolve_project_path())
   for p in sorted(sessions_dir('.').glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
       d = json.loads(p.read_text())
       if d.get('project_path', project) != project:
           continue
       if d.get('status') in ('in_progress', 'waiting'):
           d['status'] = 'completed'
           d['log'].append({'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
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
