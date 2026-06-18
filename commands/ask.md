---
description: Read-only Q&A about the codebase. Azusa investigates and answers — zero writes anywhere (no code, no session files, no .kon/ artifacts).
---

# /kon:ask

For questions about the codebase — how something works, where logic lives, what a pattern means.
Read-only exploration and a direct answer.

**Zero writes.** Ask mode must not create or modify any file — not code, not `.kon/sessions/`, not `.kon/plan.md`, not memory, not git state. Read and answer only.

## Usage

```
/kon:ask <question>
```

Examples:

```
/kon:ask how does session tracking write to .kon/sessions/?
/kon:ask where is the Mio review checklist defined?
/kon:ask what's the difference between kon go and kon team?
```

## Scope boundary

- **Questions only** — explain, locate, compare, trace. Do not implement.
- If the user asks to *change* something, answer what you can read-only, then offer:
  "Want me to make that change? Use `/kon:quick` for a small fix or `/kon:go` for the full pipeline."
- If the question is outside the repo (runtime state, secrets, external services), say what you cannot verify from the codebase alone.

## Flow

1. **🎸 Azusa** — investigate the question read-only.
   - Tools allowed: Read, Glob, Grep, Bash (read-only commands only — e.g. `git log`, `git diff`, `git show`, `ls`, `cat`; no writes).
   - **Forbidden tools:** Write, Edit, StrReplace, Delete, and any Bash that mutates disk or git state.
   - No `.kon/plan.md`, no session JSON, no other artifacts written.
2. **Orchestrator** — present Azusa's answer to the user with code citations where helpful.
   - Do not re-implement or expand beyond what Azusa found unless the user asks a follow-up.
   - **Orchestrator is also read-only** — do not write files, create sessions, or run mutating shell commands.

No session tracking. No Nodoka summarize. No `kon finish` — there is no session to close.

## Read-only hard floor (orchestrator + Azusa)

| Action | Allowed? |
|--------|----------|
| Read / Glob / Grep source files | ✅ |
| Read-only git (`log`, `diff`, `show`, `status`) | ✅ |
| Write / Edit / StrReplace / Delete any file | ❌ |
| Create or update `.kon/sessions/*.json` | ❌ |
| Write `.kon/plan.md` or memory files | ❌ |
| `git add`, `git commit`, `git push`, `git checkout`, `git reset` | ❌ |
| `mkdir`, `touch`, `rm`, `mv`, `cp`, `tee`, redirect-to-file | ❌ |
| `python3 -c` that writes to disk | ❌ |

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
- **Skip session tracking entirely** — do not read [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md) for this command; it does not apply.

## Comparison

| Item | `/kon:ask` | `/kon:quick` | `/kon:go` |
|------|------------|--------------|-----------|
| Purpose | Answer questions | Small code change | Full feature/fix |
| Azusa explore | ✅ (read-only) | ❌ skip | ✅ |
| Mugi plan | ❌ | ❌ | ✅ |
| Yui implement | ❌ | ✅ | ✅ |
| Mio review | ❌ | ✅ lightweight | ✅ full |
| Ritsu verify | ❌ | ❌ (Stop hook) | ✅ |
| File changes | ❌ none | ✅ | ✅ |
| Session tracking | ❌ none | ✅ | ✅ |
| Nodoka summarize | ❌ | ✅ | ✅ |
