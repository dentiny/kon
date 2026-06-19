---
name: teammate-flow
description: This skill should be used when orchestrating the full kon teammate flow — Azusa explores, Mugi plans, Yui implements, Sawako cleans, Mio reviews. Applies to /kon:team.
---

# Teammate Flow

**Consumers**: [`/kon:team`](https://github.com/dentiny/kon/blob/main/commands/team.md).

Teammate-flow defines the shared workflow skeleton for the five-person kon team —
from exploration to implementation to review.
Each agent owns their segment; the orchestrator strings them together.

## Shared flow (Full pipeline)

These steps are required in order for `/kon:team`:

0. **Plan reuse check** — if `.kon/plan-<SESSION_ID>.md` exists (or the most recent `.kon/plan-*.md`
   for cross-session reuse after `/kon:design`), read it and ask the user once: reuse or re-plan?
   Skip Azusa + Mugi on reuse (unless user chooses re-plan).
   See [`commands/team.md`](../commands/team.md#plan-reuse-after-kondesign).
1. **🎸 Azusa** + optional **📚 Jun** (parallel when task needs external docs) — see
   [`skills/external-research`](external-research/SKILL.md). Jun writes `.kon/research.md`.
2. **🍰 Mugi** — structure the work into `.kon/plan-<SESSION_ID>.md` (read `.kon/research.md` if present).
3. **User confirms plan (MANDATORY)** — After Mugi finishes:
   - Orchestrator presents the plan summary to the user
   - If `## Decisions needed` section exists, present each decision with its default
   - **STOP and wait for explicit user approval** — do NOT spawn Yui automatically
   - Only proceed to step 4 after user says "go", "approved", "proceed", or similar confirmation
   - **This applies even in `--yolo` mode** — plan approval is always required
   - Update session: set `steps_waiting: ["User"]`, `status=waiting` before waiting for input
4. **Milestone loop** — For each milestone in the plan (or all steps if no milestones):
   - **🎶 Yui** — implement this milestone only. "Working on Milestone X..."
     - Execute steps for current milestone
     - Stop after completing milestone (don't continue to next milestone)
   - **🧹 Sawako** — garbage collect the implementation
     - Remove dead code: unused functions, variables, imports
     - Remove redundant comments that just restate what code does
     - Simplify over-complex logic, remove duplicate logic
     - **Verify before removing** — use grep to confirm nothing is referenced
     - No behavior changes — tests should still pass
   - **📝 Mio** — review changes for this milestone only
     - Follow `skills/strict-review` on the diff from this milestone
     - If BLOCKED/NEEDS_CHANGES → Yui fixes → Sawako cleans → Mio re-reviews (repeat until approved)
     - If APPROVED → proceed to next milestone
   - Repeat loop until all milestones complete
5. **Manual testing** — After all milestones approved, user runs tests themselves.
   - User verifies the implementation works in their environment

After review passes, always call **📋 Nodoka** as the final step to write the session summary.
Follow [`/kon:summarize`](https://github.com/dentiny/kon/blob/main/commands/summarize.md).

### Quality checks

## Orchestrator rules

### Narration

When the orchestrator speaks to the user, use 🌸 Ui's narrator voice —
opening, closing, and stuck-point beats.
Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).

### Execution rules

- **The orchestrator does not implement.** Every agent is launched via the Task tool.
- **Model inheritance:** Do NOT pass `model` parameter when spawning subagents — let them inherit parent's model
- **CRITICAL: Never auto-proceed from Mugi to Yui** — after Mugi finishes, the orchestrator MUST:
  1. Present the plan to the user
  2. Set session `status=waiting` with `steps_waiting: ["User"]`
  3. STOP and wait for explicit user confirmation (even in `--yolo` mode)
  4. Only spawn Yui after user confirms
- **Milestone-based review loop:**
  1. If plan has milestones: implement and review ONE milestone at a time
  2. Yui implements milestone → Sawako cleans up → Mio reviews → if blocked, Yui fixes (then Sawako cleans again) → repeat until Mio approves
  3. Only after Mio approves current milestone, proceed to next milestone
  4. Do NOT implement all milestones then review — review incrementally
- After each agent finishes, give the user one-line summary (not a full paste).
- No skipping steps. Even for small tasks, every step runs.
- At the end, give a final summary: which files changed, any unresolved issues.
- **Pass `PLAN_FILE` to every agent that reads or writes the plan** (Mugi, Yui, Nodoka,
  Azusa-challenge). Include this line in the task prompt:
  `PLAN_FILE: .kon/plan-<SESSION_ID>.md`
  where `SESSION_ID` is the same ID used for session tracking.

### Commit message draft

After all milestones are approved, if there are uncommitted
changes from this session, draft a commit message from the diff following
[`skills/commit-message`](https://github.com/dentiny/kon/blob/main/skills/commit-message/SKILL.md).

**Do not run `git commit` automatically** — provide the text only, user decides.

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

- **Never skip 📝 Mio** — code review is mandatory for every milestone
- **Review per milestone, not all at once** — Mio reviews after each milestone implementation
- **Mio blocking is final** — if Mio blocks, send back to Yui for fixes
- **Standards don't relax on round 3** — the checklist is the same from round 1 to round N
- **No automated testing** — user runs tests manually after all milestones are approved
