---
description: Lightweight task entry point. Orchestrator calls Yui directly for small changes, skips Azusa / Mugi, Yui finishes and runs lightweight Mio (3-item checklist subset).
---

# /kon:quick

For "just tweak this one thing" level tasks.
Skip the Azusa exploration / Mugi plan overhead — orchestrator calls Yui directly,
Yui makes the change, then Mio does a lightweight review (7 items → 3 items).

**Unclear task?** Ask before implementing — follow [`skills/ask-dont-guess`](../skills/ask-dont-guess/SKILL.md).

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

Use **Task resume** for the Yui → Mio loop (and Sawako on team): spawn each role once with full agent file (+ `strict-review` for Mio on first review only); on must-fix / re-review, **`resume`** the same Task id — delta prompt only. Store ids with `kon_session.py set-task-agent`. See [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md) **Implementation loop — Task resume**.

1. **🎶 Yui** — implement directly (no Azusa explore, no Mugi plan).
   - Yui reads 1-2 surrounding files to pick up conventions, no broad exploration.
   - No plan file written.
2. **📝 Mio** — lightweight review, 3-item subset only.
3. **Manual testing** — user runs tests themselves after Mio approves (no compile/build during the Yui → Mio loop).
4. **Orchestrator** — draft a commit message from the diff
   following [`skills/commit-message`](https://github.com/dentiny/kon/blob/main/skills/commit-message/SKILL.md) and attach to final summary.
   **Do not run `git commit` automatically.**

## Mio's lightweight checklist (7 items → 3 items)

| Item | Run? |
|------|------|
| 1. simplest correct implementation | ❌ skip |
| 2. requirement coverage | ✅ |
| 3. correctness proven | ✅ |
| 4. edge cases handled | ❌ skip |
| 5. no regression | ❌ skip |
| 6. no performance issue | ❌ skip |
| 7. consistent, safe, and tested | ✅ |

Items run: 2 / 3 / 7.

Orchestrator must explicitly pass `mode=quick` and the subset to Mio when launching.
In Mio's checklist output, items in the subset use `[x]` / `[ ]` normally;
items outside the subset use `[—]` with reason `skipped by mode=quick`.

**Note on item 3 (correctness proven):** Required in quick mode for basic correctness verification via diff + static analysis. No compile/build during the loop. User runs full validation manually after Mio approves.

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
- **Cannot shrink Mio's 3-item subset further** — these 3 are the hard floor
- **Cannot relax must-fix standards because "user said quick-fix"** — the subset items are still full strict-review
- **Do not self-implement / do not self-review** — call Yui and Mio via Task tool

## Session close (default)

After Mio approves:

1. **📋 Nodoka** — `/kon:summarize`
2. **Retro** — [`skills/session-retro`](../skills/session-retro/SKILL.md)
3. `/kon:finish` or dashboard ✓ (user may say **skip retro**)

## Comparison

| Item | `/kon:quick` | `/kon:team` |
|------|------------|-------------|
| Azusa explore | ❌ skip | ✅ |
| Mugi plan | ❌ skip | ✅ |
| Yui implement | ✅ | ✅ per milestone |
| Sawako cleanup | ❌ skip | ✅ per milestone |
| Mio review | ✅ lightweight (3 items) | ✅ full (7 items) per milestone |
| Testing | Manual | Manual |
