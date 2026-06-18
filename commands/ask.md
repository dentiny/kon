---
description: Read-only Q&A about the codebase. Azusa investigates and answers — zero repo writes (no code, no .kon/ artifacts); session JSON is tracked under ~/.kon/projects/.
---

# /kon:ask

For questions about the codebase — how something works, where logic lives, what a pattern means.
Read-only exploration and a direct answer.

**Zero repo writes.** Ask mode must not create or modify anything inside the project — not code, not `.kon/plan.md`, not memory, not git state. Read and answer only.

**Session tracking applies.** Create and update a session JSON under `~/.kon/projects/<repo-name>/sessions/` (see [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md)) so the dashboard records every ask run. Use `command: "/kon:ask"`, `steps_pending: ["Azusa"]` on create; set `status=waiting` when Azusa finishes.

## Usage

```
/kon:ask <question>
```

Examples:

```
/kon:ask how does session tracking write session files?
/kon:ask where is the Mio review checklist defined?
/kon:ask what's the difference between kon go and kon team?
```

## Scope boundary

- **Questions only** — explain, locate, compare, trace. Do not implement.
- If the user asks to *change* something, answer what you can read-only, then offer:
  "Want me to make that change? Use `/kon:quick` for a small fix or `/kon:go` for the full pipeline."
- If the question is outside the repo (runtime state, secrets, external services), say what you cannot verify from the codebase alone.

## Flow

1. **Orchestrator** — create session file (same snippet as other commands; `cmd = '/kon:ask'`). Follow [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md).
2. **🎸 Azusa** — investigate the question read-only.
   - Tools allowed: Read, Glob, Grep, Bash (read-only commands only — e.g. `git log`, `git diff`, `git show`, `ls`, `cat`; no writes).
   - **Forbidden tools:** Write, Edit, StrReplace, Delete, and any Bash that mutates disk or git state.
   - No `.kon/plan.md` or other project artifacts written.
3. **Orchestrator** — update session: move Azusa to `steps_completed`, add log entry, set `status=waiting`.
4. **Orchestrator** — present Azusa's answer to the user with code citations where helpful.
   - Do not re-implement or expand beyond what Azusa found unless the user asks a follow-up.
   - **Orchestrator is read-only for repo files** — do not write code or run mutating shell commands.

No Nodoka summarize. User may close the session with `kon finish` or the dashboard ✓ button.

## Read-only hard floor (orchestrator + Azusa)

| Action | Allowed? |
|--------|----------|
| Read / Glob / Grep source files | ✅ |
| Read-only git (`log`, `diff`, `show`, `status`) | ✅ |
| Write / Edit / StrReplace / Delete any **project** file | ❌ |
| Create or update session JSON (`~/.kon/projects/*/sessions/`) | ✅ |
| Write `.kon/plan.md` or memory files in the repo | ❌ |
| `git add`, `git commit`, `git push`, `git checkout`, `git reset` | ❌ |
| `mkdir`, `touch`, `rm`, `mv`, `cp`, `tee`, redirect-to-file **in the repo** | ❌ |
| `python3 -c` that writes **project or .kon/** files | ❌ |
| `python3 -c` that writes **session JSON** under `~/.kon/projects/` | ✅ |

If a write would help (e.g. saving notes), tell the user — do not write it yourself.

## Azusa output format (ask mode)

In addition to exploration notes, Azusa must end with a direct answer:

```
## Loaded memory entries
(follow memory-loading skill output format — read only, do not write memory)

## Investigation notes
- `path/to/file.py:42` — one-sentence relevance

## Answer
(Direct response to the user's question — complete sentences, cite paths/lines where useful)

## If you want to change this
(One line: suggest `/kon:quick` or `/kon:go` only when the question implies a change)
```

## Orchestrator rules

- **Narration:** use 🌸 Ui for opening and closing beats. Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
- **Do not spawn Yui, Mugi, Mio, Ritsu, or Sawako** — ask mode is Azusa + answer only.
- **Do not self-investigate instead of Azusa** — spawn Azusa via Task tool for the exploration pass.
- **Do not draft commit messages** — there are no code changes.
- **`--yolo` has no effect** — there are no confirmation checkpoints to skip.
- **Follow session-tracking** — create session at start, update after Azusa; see [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md).

## Comparison

| Item | `/kon:ask` | `/kon:quick` | `/kon:go` |
|------|------------|--------------|-----------|
| Purpose | Answer questions | Small code change | Full feature/fix |
| Azusa explore | ✅ (read-only) | ❌ skip | ✅ |
| Mugi plan | ❌ | ❌ | ✅ |
| Yui implement | ❌ | ✅ | ✅ |
| Mio review | ❌ | ✅ lightweight | ✅ full |
| Ritsu verify | ❌ | ❌ (Stop hook) | ✅ |
| File changes in repo | ❌ none | ✅ | ✅ |
| Session tracking | ✅ | ✅ | ✅ |
| Nodoka summarize | ❌ | ✅ | ✅ |
