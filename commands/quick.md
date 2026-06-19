---
description: Lightweight task entry point. Orchestrator calls Yui directly for small changes, skips Azusa / Mugi, Yui finishes and runs lightweight Mio (4-item checklist subset). Stop hook backstops tests automatically.
---

# /kon:quick

For "just tweak this one thing" level tasks.
Skip the Azusa exploration / Mugi plan overhead — orchestrator calls Yui directly,
Yui makes the change, then Mio does a lightweight review (9 items → 4 items).
Tests aren't explicitly called — the Stop hook backstops them automatically.

## Usage

```
/kon:quick <small task description>
```

Examples:

```
/kon:quick fix the typo "occured" → "occurred" in README paragraph 3
/kon:quick add type hint to auth.py:42
```

## Scope boundary (trust the user)

If the user says "this is a quick fix" — it's a quick fix.
The orchestrator doesn't auto-gate (no line-count detection, no file-count check).

If the description sounds like a large change (multi-file, cross-module, behavior change),
the orchestrator warns **once**: "This looks bigger than a quick fix — want to use `/kon:team` instead?"
If the user says no → run quick anyway. **Don't ask again.**

## Flow

1. **🎶 Yui** — implement directly (no Azusa explore, no Mugi plan).
   - Yui reads 1-2 surrounding files to pick up conventions, no broad exploration.
   - No plan file written.
2. **📝 Mio** — lightweight review, 4-item subset only.
3. **Manual testing** — user runs tests themselves after Mio approves.
4. **Orchestrator** — draft a commit message from the diff
   following [`skills/commit-message`](https://github.com/dentiny/kon/blob/main/skills/commit-message/SKILL.md) and attach to final summary.
   **Do not run `git commit` automatically.**

## Mio's lightweight checklist (9 items → 4 items)

| Item | Run? |
|------|------|
| 1. acceptance match | ✅ |
| 2. evidence per function | ❌ skip (Stop hook backstops with tests) |
| 3. edge case coverage | ❌ skip |
| 4. convention conformance | ✅ |
| 5. no unsafe pattern | ✅ |
| 6. no unexplained magic | ❌ skip |
| 7. no TODO evasion | ✅ |
| 8. no defensive bloat | ❌ skip |
| 9. no completeness theatre | ❌ skip |

Items run: 1 / 4 / 5 / 7.

Orchestrator must explicitly pass `mode=quick` and the subset to Mio when launching.
In Mio's checklist output, items in the subset use `[x]` / `[ ]` normally;
items outside the subset use `[—]` with reason `skipped by mode=quick`.

**Note on item 2 (evidence per function):** Skipped in quick mode because testing is manual.
User verifies implementation works after Mio approves.

## Failure handling

### Mio blocks (NEEDS_CHANGES / BLOCKED)

Same as `/kon:team` — send full must-fix list to Yui, fix, re-review. **2 consecutive same item → stop and ask user.**
See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md).

## Memory propose confirm flow

Follow [`skills/memory-propose-confirm`](https://github.com/dentiny/kon/blob/main/skills/memory-propose-confirm/SKILL.md).
Confirm flow completes, then the main flow continues — the quick step structure doesn't change.

## Session tracking

Write a session file at the start and update it after each step.
Follow [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md).

## Orchestrator rules

- **Narration:** use 🌸 Ui for opening, closing, stuck-point beats. Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
- **Model inheritance:** Do NOT pass `model` parameter when spawning subagents — let them inherit parent's model
- **Cannot skip Mio** — quick cuts stage count (no Azusa / Mugi / automated tests), not the review itself
- **Cannot shrink Mio's 4-item subset further** — these 4 are the hard floor
- **Cannot relax must-fix standards because "user said quick-fix"** — the subset items are still full strict-review
- **Do not self-implement / do not self-review** — call Yui and Mio via Task tool

## Comparison

| Item | `/kon:quick` | `/kon:go` | `/kon:team` |
|------|------------|-----------|-------------|
| Azusa explore | ❌ skip | ✅ | ✅ |
| Mugi plan | ❌ skip | ✅ | ✅ |
| Yui implement | ✅ | ✅ | ✅ |
| Mio review | ✅ lightweight (4 items) | ✅ full (9 items) | ✅ full (9 items) |
| Testing | Manual | Manual | Manual |
