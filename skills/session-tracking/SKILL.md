---
name: session-tracking
description: This skill should be used by the kon orchestrator at the start of every command and after every agent step, to write a JSON session file to `.kon/sessions/` that the dashboard reads.
---

# Session Tracking

**Owner**: orchestrator
**Consumers**: all `/kon:*` commands

The orchestrator writes and updates a session file so `scripts/dashboard.py`
can display live status and a clickable log of every run.

## Session file location

`.kon/sessions/<session-id>.json`

**Session ID format**: `YYYYMMDD-HHMMSS-<task-slug>`
where task-slug = first 4 words of the task, lowercased, spaces → hyphens.

Example: `20260617-203042-add-email-validation`

## Schema

```json
{
  "id": "20260617-203042-add-email-validation",
  "task": "add email validation to auth.py",
  "command": "kon go",
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

## When to write

| Event | What to do |
|-------|-----------|
| Command starts | `mkdir -p .kon/sessions` then write file: `status=in_progress`, empty `steps_completed`, all agents in `steps_pending` |
| About to spawn an agent | Update: move agent to `current_agent`, remove from `steps_pending`, add log entry `"starting..."` |
| Agent completes | Update: move agent from `current_agent` → `steps_completed`, add log entry with one-line summary |
| All agents done | Update: `status=completed`, `current_agent=null` |
| Retry limit hit / blocked | Update: `status=blocked`, add log entry explaining what's stuck |

Write the file with a single `Bash` call using `python3 -c` or `tee`:

```bash
python3 -c "
import json, pathlib, datetime
p = pathlib.Path('.kon/sessions/<id>.json')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(<data>, ensure_ascii=False, indent=2))
"
```

## Log entry summary rules

One sentence, past tense, specific — the user reads this at a glance:

- "Found 3 relevant files; convention divergence at auth.py:42"
- "Plan written to .kon/plan.md — 4 steps, defaults accepted for 2 decisions"
- "Step 3/4 done — edited auth.py, validators.py; acceptance ✅"
- "BLOCKED: edge case `empty input` unresolved (round 2)"
