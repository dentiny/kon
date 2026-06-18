---
name: teammate-flow
description: This skill should be used when orchestrating the full kon teammate flow — Azusa explores, Mugi plans, Yui implements, Mio reviews, Ritsu validates. Applies to /kon:go and /kon:team (both sequential and parallel variants).
---

# Teammate Flow

**Consumers**: [`/kon:go`](https://github.com/dentiny/kon/blob/main/commands/go.md), [`/kon:team`](https://github.com/dentiny/kon/blob/main/commands/team.md).

Teammate-flow defines the shared workflow skeleton for the five-person kon team —
from exploration to implementation to review to verification.
Each agent owns their segment; the orchestrator strings them together.

## Shared flow (Sequential segment)

These four steps are required in order for both `/kon:go` and `/kon:team`:

0. **Plan reuse check** — if `.kon/plan.md` exists, read it and ask the user once: reuse or re-plan?
   Skip Azusa + Mugi on reuse (unless user chooses re-plan). With `--yolo`, auto-reuse when the plan
   matches the current task. See [`commands/go.md`](../commands/go.md#plan-reuse-after-kondesign).
1. **🎸 Azusa** + optional **📚 Jun** (parallel when task needs external docs) — see
   [`skills/external-research`](external-research/SKILL.md). Jun writes `.kon/research.md`.
2. **🍰 Mugi** — structure the work into `.kon/plan.md` (read `.kon/research.md` if present).
3. **User confirms plan** (if there are open questions, resolve them before continuing)
4. **🎶 Yui** — execute the plan steps. "Okay! Starting Step 1."

Step 5 onward is command-specific — `/kon:go` is sequential (📝 Mio then 🥁 Ritsu),
`/kon:team` is parallel (📝 Mio and 🥁 Ritsu simultaneously).

After Ritsu passes, always call **📋 Nodoka** as the final step to write the session summary.
Follow [`/kon:summarize`](https://github.com/dentiny/kon/blob/main/commands/summarize.md).

### Quality checks

Cursor `subagentStop` runs `on_subagent_stop.py` after each Task subagent. For manual backstop,
pipe output to `hooks/teammate_quality_check.py` with the matching `teammate_role`
(Azusa, Jun, Mugi, Yui, Mio, Ritsu, Sawako, Nodoka, Azusa-challenge, Mugi-revise).
Block on failure; retry the agent per [`skills/failure-handling`](failure-handling/SKILL.md).

## Orchestrator rules

### Narration

When the orchestrator speaks to the user, use 🌸 Ui's narrator voice —
opening, closing, and stuck-point beats.
Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).

### Execution rules

- **The orchestrator does not implement.** Every agent is launched via the Task tool.
- After each agent finishes, give the user one-line summary (not a full paste).
- No skipping steps. Even for small tasks, every step runs.
- At the end, give a final summary: which files changed, test result, any unresolved issues.

### Commit message draft

After Ritsu passes (or `/kon:team` merges APPROVED + PASS), if there are uncommitted
changes from this session, draft a commit message from the diff following
[`skills/commit-message`](https://github.com/dentiny/kon/blob/main/skills/commit-message/SKILL.md).

**Do not run `git commit` automatically** — provide the text only, user decides.

### `/kon:go` vs `/kon:team` — which to use

Both have identical review strictness (🔵 Mio full 9 items + 🥁 Ritsu).
The difference is only in step 5+:
`/kon:go` is sequential (Mio first, then Ritsu); `/kon:team` is parallel (~30% wall-clock saving).

**Prefer `/kon:team`** when:
- Scope is clear (boundary defined, no need to discover-while-implementing)
- Existing test coverage exists

**Prefer `/kon:go`** when:
- Scope is uncertain, need to discover-while-implementing
- Impact surface is hard to define upfront (cross-subsystem, complex dependency graph)

When in doubt, don't automatically fall back to go out of "caution" —
team's parallelism does not sacrifice strictness.

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md).

## Session tracking

At the start of every run and after every agent step, write a session state file.
Follow [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md).
This feeds the live dashboard (`python3 scripts/dashboard.py`).

## YOLO mode (`--yolo` flag)

When the user appends `--yolo` to any command, activate autonomous mode.
Follow [`skills/yolo-mode`](https://github.com/dentiny/kon/blob/main/skills/yolo-mode/SKILL.md).

## Memory propose confirm flow

Detection (including fence tracking) and the 6-step confirm flow follow
[`skills/memory-propose-confirm`](https://github.com/dentiny/kon/blob/main/skills/memory-propose-confirm/SKILL.md).
Confirm flow completes, then the main flow continues — the command step structure does not change.

## Hard rules

- **Never skip 📝 Mio** and hand directly to 🥁 Ritsu
- **Never treat "tests passed" as equivalent to "review passed"** — Mio blocking is Mio blocking regardless of test results
- **Standards don't relax on round 3** — the checklist is the same from round 1 to round N
