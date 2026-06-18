---
name: session-tracking
description: This skill should be used by the kon orchestrator at the start of every command and after every agent step, to write a JSON session file to ~/.kon/projects/<repo-name>/sessions/ that the dashboard reads.
---

# Session Tracking

**Owner**: orchestrator
**Consumers**: all `/kon:*` commands (including `/kon:ask`)

The orchestrator writes and updates a session file so `scripts/dashboard.py`
can display live status and a clickable log of every run.

## Session file location

`~/.kon/projects/<repo-name>/sessions/<session-id>.json` (override root with `KON_DATA_DIR`)

`<repo-name>` is the git repo root directory name (e.g. `kon` for `~/Desktop/kon`).
Created automatically on Cursor session start via `ensure_project_dir` hook.

Session history lives **outside the project repo**. Project working files
(`plan.md`, rubrics, retry logs) still go in `<project>/.kon/`.

**Session ID format**: `YYYYMMDD-HHMMSS-<task-slug>`
where task-slug = first 4 words of the task, lowercased, spaces → hyphens.

Example: `20260617-203042-add-email-validation`

## Schema

```json
{
  "id": "20260617-203042-add-email-validation",
  "task": "add email validation to auth.py",
  "command": "kon go",
  "project_path": "/Users/you/projects/myapp",
  "started_at": "2026-06-17T20:30:42Z",
  "status": "in_progress",
  "current_agent": "Yui",
  "steps_completed": ["Azusa", "Mugi"],
  "steps_pending": ["Mio", "Ritsu"],
  "log": [
    {"ts": "2026-06-17T20:30:43Z", "agent": "Azusa", "summary": "Found 3 relevant files in auth/"},
    {"ts": "2026-06-17T20:31:10Z", "agent": "Mugi",  "summary": "Plan written, 4 steps, 0 decisions needed"},
    {"ts": "2026-06-17T20:32:05Z", "agent": "Yui",   "summary": "Step 2/4 in progress — editing auth.py"}
  ]
}
```

## Session lifecycle

```
in_progress  →  waiting  →  completed
                    ↓
                 blocked
```

- `in_progress` — agents are actively running
- `waiting` — agents finished OR plan approval required — session stays open until user acts
- `completed` — user explicitly finished via `kon finish` or dashboard ✓ button
- `blocked` — retry limit hit, something needs human intervention

**Never auto-set `completed`.** When all agents finish, set `status=waiting`.

## Schema (full)

```json
{
  "id": "...",
  "task": "...",
  "command": "kon go",
  "project_path": "/absolute/path/to/project",
  "started_at": "...",
  "status": "in_progress | waiting | completed | blocked",
  "current_agent": "Yui | null",
  "steps_completed": ["Azusa", "Mugi"],
  "steps_pending":   ["Mio", "Ritsu", "Nodoka"],
  "steps_failed":    [],
  "steps_waiting":   [],
  "log": [...]
}
```

`steps_failed` — agents that hit an unresolvable error.
`steps_waiting` — agents paused waiting for human input (e.g., plan approval).

## When to write

| Event | Action |
|-------|--------|
| Command starts | Create file: `status=in_progress`, all agents in `steps_pending` |
| Before spawning an agent | Move agent to `current_agent`, remove from `steps_pending` |
| Agent completes normally | Move agent to `steps_completed`, add log entry |
| Agent needs human input | Move agent to `steps_waiting`, set `status=waiting` |
| Human responds, agent resumes | Move agent back to `current_agent`, set `status=in_progress` |
| Agent blocked / retry limit | Move agent to `steps_failed`, set `status=blocked` |
| All agents finished | Set `status=waiting`, `current_agent=null` — **do not set `completed`** |
| `kon finish` or dashboard ✓ | Set `status=completed` |

### `/kon:ask` variant

Ask is read-only for the repo but still tracks a session:

- On create: `command: "kon ask"`, `steps_pending: ["Azusa"]`, other agent lists empty
- After Azusa answers: `steps_completed: ["Azusa"]`, `status=waiting`, log entry with one-sentence summary of the answer topic
- Do **not** auto-set `completed` — same lifecycle as other commands

Write the file with `scripts/kon_session.py` (preferred) or a single `python3 -c` call:

```bash
# Create (all commands including ask)
python3 ~/Desktop/kon/scripts/kon_session.py init --command "kon ask" --task "<question>"

# After each agent completes
python3 ~/Desktop/kon/scripts/kon_session.py complete-agent --id <sid> --agent Azusa --summary "<one sentence>"
```

Inline fallback if the script is unavailable:

```bash
python3 -c "
import json, pathlib, datetime, os, sys
root = pathlib.Path(os.environ.get('KON_ROOT', pathlib.Path.home() / 'Desktop/kon')).expanduser()
sys.path.insert(0, str(root / 'hooks'))
from _kon_paths import ensure_sessions_dir
p = ensure_sessions_dir() / '<id>.json'
p.write_text(json.dumps(<data>, ensure_ascii=False, indent=2))
"
```

On create, always set `project_path` to the absolute cwd. Path helper: `hooks/_kon_paths.py`.

## Log entry summary rules

One sentence, past tense, specific — the user reads this at a glance:

- "Found 3 relevant files; convention divergence at auth.py:42"
- "Plan written to .kon/plan.md — 4 steps, defaults accepted for 2 decisions"
- "Step 3/4 done — edited auth.py, validators.py; acceptance ✅"
- "Answered: session paths use ~/.kon/projects/<repo-name>/sessions/"
- "BLOCKED: edge case `empty input` unresolved (round 2)"
