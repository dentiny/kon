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
Created automatically on Cursor session start via `ensure_project_dir` hook (creates the directory only).

**Auto-init:** when you send a `/kon:*` slash command, `beforeSubmitPrompt` → `init_kon_session.py` writes the session JSON under `~/.kon/projects/<repo>/sessions/` before the agent runs. Orchestrators should still call `init` if the hook is not installed; duplicate `init` is safe (supersedes prior open sessions).

Session history lives **outside the project repo**. Project working files
(`plan-<session-id>.md`, rubrics, retry logs) still go in `<project>/.kon/`.

**Session ID format**: `YYYYMMDD-HHMMSS-<task-slug>`
where task-slug = first 4 words of the task, lowercased, spaces → hyphens.

Example: `20260617-203042-add-email-validation`

## Schema

```json
{
  "id": "20260617-203042-add-email-validation",
  "task": "add email validation to auth.py",
  "command": "/kon:go",
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
- `waiting` — pipeline commands finished (`/kon:go`, `/kon:team`, …) — stays open until user acts
- `completed` — user ran `/kon:finish` / dashboard ✓, **or** one-shot command finished (`/kon:ask`, `/kon:research`, `/kon:review`), **or** superseded by a newer session
- `blocked` — retry limit hit, something needs human intervention

**Never auto-set `completed` for pipeline commands** (`/kon:go`, `/kon:team`, `/kon:quick`, `/kon:gc`, `/kon:design`). When their agents finish, set `status=waiting`.

**Auto-complete one-shot commands** when the sole agent finishes: `/kon:ask`, `/kon:research`, `/kon:review` → set `status=completed` (via `complete-agent`).

**Supersede on new run:** when `init` creates a session, any other `in_progress` or `waiting` session for the same `project_path` is auto-closed as `completed` with log `Superseded by new session <id>.` — at most one open pipeline session per project.

## Schema (full)

```json
{
  "id": "...",
  "task": "...",
  "command": "/kon:go",
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
| All agents finished (pipeline command) | Set `status=waiting`, `current_agent=null` |
| All agents finished (`/kon:ask`, `/kon:research`, `/kon:review`) | Set `status=completed` |
| `init` creates a new session | Supersede other open sessions for same project → `completed` |
| `kon finish` or dashboard ✓ | Set `status=completed` |

### `/kon:begin` variant

Interactive session — stays open until `/kon:finish`:

- On create: `command: "/kon:begin"`, `mode: "interactive"`, `steps_pending: []`, `status=in_progress`
- Sub-turns: **never** call `init` — use `log-turn` and `complete-agent` on the same id
- After each agent: `status` stays `in_progress` (begin never auto-completes)
- Close: `/kon:finish` or dashboard ✓

Check active begin session: `python3 scripts/kon_session.py active`

### `/kon:research` variant

Research is read-only for source code but writes `.kon/research.md`:

- On create: `command: "/kon:research"`, `steps_pending: ["Jun"]`
- After Jun answers: `steps_completed: ["Jun"]`, `status=completed` (via `complete-agent`), log one-sentence summary

### `/kon:review` variant

Review is read-only — no code changes:

- On create: `command: "/kon:review"`, `steps_pending: ["Mio"]` (prepend `"Mugi"` when `--rubric`)
- After Mio verdict: `steps_completed: ["Mio"]`, `status=completed` (via `complete-agent`), log verdict one-liner

### `/kon:ask` variant

Ask is read-only for the repo but still tracks a session:

- On create: `command: "/kon:ask"`, `steps_pending: ["Azusa"]`, other agent lists empty
- After Azusa answers: `steps_completed: ["Azusa"]`, `status=completed` (via `complete-agent`), log entry with one-sentence summary of the answer topic

### `/kon:design` variant

Design runs explore → plan → debate rounds → user confirm (no Yui/Mio/Ritsu):

- On create: `command: "/kon:design"`, `steps_pending: ["Azusa", "Mugi", "User"]`
- Log **each** agent spawn including repeat Azusa/Mugi debate passes (same agent name is OK — log carries round detail)
- After Mugi revise: `steps_waiting: ["User"]`, `status=waiting`
- Do **not** auto-set `completed` until user runs `/kon:finish` or approves and closes

Write the file with `scripts/kon_session.py` (preferred) or a single `python3 -c` call:

```bash
# Create (all commands including ask)
python3 $KON_ROOT/scripts/kon_session.py init --command "/kon:ask" --task "<question>"

# After each agent completes
python3 $KON_ROOT/scripts/kon_session.py complete-agent --id <sid> --agent Azusa --summary "<one sentence>"
```

Inline fallback if the script is unavailable:

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
from _kon_paths import ensure_sessions_dir
p = ensure_sessions_dir() / '<id>.json'
p.write_text(json.dumps(<data>, ensure_ascii=False, indent=2))
"
```

On create, always set `project_path` to the absolute cwd. Path helper: `hooks/_kon_paths.py`.

## Log entry summary rules

One sentence, past tense, specific — the user reads this at a glance:

- "Found 3 relevant files; convention divergence at auth.py:42"
- "Plan written to .kon/plan-20260617-203042-add-email-validation.md — 4 steps, defaults accepted for 2 decisions"
- "Step 3/4 done — edited auth.py, validators.py; acceptance ✅"
- "Answered: session paths use ~/.kon/projects/<repo-name>/sessions/"
- "BLOCKED: edge case `empty input` unresolved (round 2)"
