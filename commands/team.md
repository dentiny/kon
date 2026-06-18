---
description: Same flow as /kon:go, but Mio + Ritsu run in parallel. Saves ~30% wall-clock time. Fall back with --force-sequential.
---

# /kon:team

Same workflow as `/kon:go`, but the final review + verify stages run **in parallel**.
Mio reads the diff; Ritsu runs commands — they don't depend on each other, so they can go simultaneously.

## Usage

```
/kon:team <task description>
/kon:team --force-sequential <task description>    # fall back to /kon:go sequential order
```

## Flow

Sequential segment (🎸 Azusa → 🍰 Mugi → user confirm → 🎶 Yui) follows
[`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md).

## Plan reuse (after `/kon:design`)

Same rules as [`/kon:go`](https://github.com/dentiny/kon/blob/main/commands/go.md#plan-reuse-after-kondesign):
if `.kon/plan.md` exists, ask once to reuse or re-plan; skip Azusa + Mugi on reuse.

**Parallel (trigger both Tasks in one message):**

5a. **📝 Mio** — review the changes (follow `skills/strict-review`).
5b. **🥁 Ritsu** — run tests / lint / type check.

6. **Merge** — when both return, handle together.

Orchestrator parallel rules:
- **Actually parallel:** fire both 📝 Mio and 🥁 Ritsu in a single message with two Task calls
- **Not fake-parallel** (finishing Mio then calling Ritsu doesn't count)
- Present both outputs **separately** to the user — don't merge them into one block

## Trade-off

| Mode | Wall clock | Wasted work risk |
|------|-----------|-----------------|
| `/kon:go` sequential | 100% | 0 (Mio blocks → Ritsu never runs) |
| `/kon:team` parallel | ~60-70% | Medium (Mio blocks → Ritsu already ran) |

Net value is usually positive — most changes pass review, so the saved time outweighs occasional wasted test runs.
For high-risk changes (large refactors, unclear scope), prefer `/kon:go`.

## Merge logic

| Mio | Ritsu | Action |
|-----|-------|--------|
| APPROVED | PASS | Done. Give user summary. |
| APPROVED | FAIL | Send failure back to Yui to fix (no re-review needed). |
| NEEDS_CHANGES / BLOCKED | PASS | Send must-fix to Yui. **After fix, re-run both Mio + Ritsu** (can't assume tests will still pass). |
| NEEDS_CHANGES / BLOCKED | FAIL | Send both to Yui. Re-run both after fix. |

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md) — same 2-consecutive-same-issue limit applies.

## `--force-sequential`

Use when the user explicitly wants sequential order. Equivalent to changing steps 5a/5b back to 5 → 6 (Mio first, then Ritsu).

When to use:
- High-risk change, don't want wasted test runs
- Debugging the parallel flow itself
