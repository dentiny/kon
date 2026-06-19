---
description: Write a clean session summary. Called automatically at the end of every run, or on-demand to summarize a past session.
---

# /kon:summarize

Have Nodoka write a complete session report for the current (or specified) session.
Called automatically at the end of every `/kon:go`, `/kon:team`, `/kon:quick`, and `/kon:gc` run.
Can also be called manually to (re)summarize any session.

## Usage

```
/kon:summarize                  # summarize the most recent session
/kon:summarize <session-id>     # summarize a specific session
```

## Flow

1. **Orchestrator** — resolve the target session:
   - No argument → use the most recent session for this repo under `~/.kon/projects/<repo-name>/sessions/` (by mtime)
   - Session ID given → load from `~/.kon/projects/<repo-name>/sessions/<id>.json`
   - No sessions found → print "No sessions found for this project" and exit

2. **📋 Nodoka** — read session artifacts and write the summary:
   - Reads the session JSON (agent log)
   - Reads `.kon/plan-<session-id>.md` if it exists (fall back to `.kon/plan.md`)
   - Reads `git diff HEAD` for the actual diff
   - Writes summary alongside the session JSON in `~/.kon/projects/<repo-name>/sessions/<id>-summary.md`
   - Updates `summary_path` field in the session JSON

3. **Orchestrator** — print the summary to chat and update the dashboard entry.

## When called automatically

Every `kon go`, `kon team`, `kon quick`, and `kon gc` run calls `/kon:summarize`
as its final step, after Ritsu passes. No additional user action needed.

## Orchestrator rules

- **Narration**: use 🌸 Ui for opening/closing. Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
- **Do not summarize yourself** — spawn Nodoka via Task tool
- The summary is for the user's record; do not truncate it
