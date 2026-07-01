---
name: teammate-flow
description: This skill should be used when orchestrating the full kon teammate flow — Azusa explores, Mugi plans, Yui implements, Sawako cleans, Mio reviews. Applies to /kon:team.
---

# Teammate Flow

**Consumers**: [`/kon:team`](https://github.com/dentiny/kon/blob/main/commands/team.md).

Teammate-flow defines the shared workflow skeleton for the kon team —
from exploration to implementation to review.
Each agent owns their segment; the orchestrator strings them together.

**Orchestrator context:** follow [`skills/orchestrator-context`](orchestrator-context/SKILL.md) — artifacts hold full output; orchestrator routes by file pointer only.

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — first principles (don't hide the issue); simplest, most concise correct solution.

**When anything is unclear:** ask the user — do not guess or hallucinate. Follow [`skills/ask-dont-guess`](ask-dont-guess/SKILL.md). Orchestrator must not advance to the next stage until material uncertainty is resolved.

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
   - Update session (required — dashboard shows ⏸ waiting):
     ```bash
     python3 $KON_ROOT/scripts/kon_session.py wait-for-user --id "$SID" \
       --after plan --summary "Plan ready — approve to start milestone 1?"
     ```
   - After user confirms:
     ```bash
     python3 $KON_ROOT/scripts/kon_session.py user-continued --id "$SID" \
       --summary "Approved plan"
     ```
4. **Milestone loop** — For each milestone in the plan (or all steps if no milestones):
   - **🎶 Yui** — implement this milestone only. "Working on Milestone X..."
     - Execute steps for current milestone
     - Stop after completing milestone (don't continue to next milestone)
   - **🧹 Sawako** — garbage collect the implementation (runs immediately after Yui — no user gate here)
     - Remove dead code: unused functions, variables, imports
     - Remove redundant comments that just restate what code does
     - Simplify over-complex logic, remove duplicate logic
     - **Verify before removing** — use grep to confirm nothing is referenced
     - No behavior changes — tests should still pass
   - **📝 Mio** — review changes for this milestone only
     - Follow `skills/strict-review` on the diff from this milestone
     - If BLOCKED/NEEDS_CHANGES → Yui fixes → Sawako cleans → Mio re-reviews (repeat until approved)
     - If APPROVED → **keep Task ids** across milestones (do **not** clear here). **User gate (MANDATORY)** before the next milestone or summarize:
       - Present milestone summary: what changed, Mio verdict, open issues if any
       - **STOP** — do NOT spawn the next milestone or Nodoka until the user approves
       - Update session (dashboard shows ⏸ waiting):
         ```bash
         python3 $KON_ROOT/scripts/kon_session.py wait-for-user --id "$SID" \
           --after milestone --milestone N \
           --summary "Milestone N approved by Mio — proceed to milestone N+1?" 
         ```
         (Last milestone: summary text like "Milestone N approved — proceed to summarize?")
       - After user confirms: `user-continued`, then next milestone or step 5
   - Repeat until all milestones complete (each followed by user gate)
5. **Manual testing** — After the last milestone gate, user runs tests themselves.
   - User verifies the implementation works in their environment

After review passes, always call **📋 Nodoka** as the final step to write the session summary.
Follow [`/kon:summarize`](https://github.com/dentiny/kon/blob/main/commands/summarize.md).

### Quality checks

## Implementation loop — Task resume (token savings)

Within each milestone (or the single pass for `/kon:quick` / `/kon:debug`), **🎶 Yui → 🧹 Sawako → 📝 Mio** form one loop until Mio approves. **Do not re-pass agent files or skills on every iteration** — spawn once, then **resume** the same Task subagent.

### No build/compile during the loop

During the implementation loop, **do not run project compile or build steps** — no `npm run build`, `cargo build`, `go build`, `tsc`, bundlers, or equivalent full source builds.

| Agent | During loop |
|-------|-------------|
| **🎶 Yui** | Edit code only. May run **targeted** pytest for tests added/changed this turn (`pytest path::test -xvs`). No full test suite, no compile/build. |
| **🧹 Sawako** | Cleanup only — no build/compile. |
| **📝 Mio** | Review via diff + static analysis. Do not require or block on missing build output. Accept targeted test output when Yui added tests. |

**User validates manually** after all milestones are approved (existing policy). `/kon:debug` is the exception: Yui runs repro commands from `debug.md` (not a full project build).

### Scope

Default scope: `impl-loop`. One set of Task ids shared across **all milestones** in a `/kon:team` run until context is full or resume fails.

**After Mio approves a milestone:** do **not** call `clear-task-agents` — ids stay warm for the next milestone.

**Before starting the next milestone** (after `user-continued`):

```bash
python3 $KON_ROOT/scripts/kon_session.py maybe-clear-task-agents --id "$SID"
# prints "kept" (resume Yui/Sawako/Mio) or "cleared" (fresh spawn)
```

Or check first:

```bash
python3 $KON_ROOT/scripts/kon_session.py should-refresh-task-agents --id "$SID"
# prints "keep" or "refresh"
```

Refresh when **any** impl-loop agent's latest transcript estimate is ≥ **80%** of the **observed** context window. Window size comes from Cursor's `preCompact` hook (`context_window_size`, stored in `~/.kon/context_profile.json` and on the active session) — **not** a hardcoded default. Until Cursor reports a window (or you set an override), `should-refresh-task-agents` prints **`keep`**.

| Override | Meaning |
|----------|---------|
| `KON_TASK_CONTEXT_BUDGET` | Force assumed window size (tokens) |
| `~/.kon/config.json` → `task_context_budget` | Same, persistent |
| `--budget` on CLI | One-off override |
| `KON_TASK_CONTEXT_THRESHOLD` | Default `0.8` — refresh when usage ≥ window × threshold |

Estimates come from `subagentStop` transcript token counts in the session log — approximate, not Cursor's exact fill meter. Re-run `scripts/install_cursor_hooks.sh` after upgrade so `preCompact` is wired.

Still **clear** (or rely on `maybe-clear-task-agents` → `cleared`) when:
- Resume fails / Task id expired
- Same must-fix blocked twice (optional fresh Mio — see failure-handling)
- User runs `clear-task-agents` manually

### First pass in the loop (new Task)

| Agent | First spawn prompt includes | After Task returns |
|-------|----------------------------|--------------------|
| **🎶 Yui** | `agents/Yui.md` + `PLAN_FILE` + milestone steps | `set-task-agent --agent Yui --task-id <id>` |
| **🧹 Sawako** | `agents/Sawako.md` + files Yui touched (paths only) | `set-task-agent --agent Sawako --task-id <id>` |
| **📝 Mio** | `agents/Mio.md` + `skills/strict-review/SKILL.md` + scoped diff pointer + plan excerpt path | `set-task-agent --agent Mio --task-id <id>` |

Store ids:

```bash
python3 $KON_ROOT/scripts/kon_session.py set-task-agent --id "$SID" --agent Yui --task-id "<task-id>"
python3 $KON_ROOT/scripts/kon_session.py set-task-agent --id "$SID" --agent Mio --task-id "<task-id>"
```

### Fix / re-review passes (resume only)

Look up id; if present, **Task `resume=<id>`** with a **short delta prompt only** — do **not** re-attach `agents/*.md` or `skills/*.md`.

```bash
YUI_ID=$(python3 $KON_ROOT/scripts/kon_session.py get-task-agent --id "$SID" --agent Yui)
MIO_ID=$(python3 $KON_ROOT/scripts/kon_session.py get-task-agent --id "$SID" --agent Mio)
```

**Yui resume (after Mio must-fix):**

```text
Resume. You already have agents/Yui.md and the plan.
Fix must-fix items from sessions/<SID>/review.md — reference each by number.
PLAN_FILE: …  Milestone: N. Report files changed.
```

**Mio resume (re-review same milestone):**

```text
Resume. You already have agents/Mio.md and strict-review.
Re-review milestone N. Prior must-fix: sessions/<SID>/review.md.
Verify each item with git diff evidence. Full hook-compliant output.
```

**Sawako resume (after Yui fix):** same pattern — delta only, no agent file re-pass.

If `get-task-agent` prints nothing, or resume fails → **fresh Task spawn** (full agent + skill once), then `set-task-agent` again.

### When to fresh-spawn (not resume)

- First iteration of the loop for that milestone
- After `clear-task-agents` (context refresh) or when `get-task-agent` is empty
- Resume error / expired Task id
- Same must-fix blocked **2 consecutive times** (see failure-handling) — optional fresh Mio

Explore/plan/design agents (**Azusa, Mugi, Jun, Nodoka**) stay **one-shot spawns** — not part of `impl-loop`.

## Orchestrator rules

Follow [`skills/orchestrator-context`](orchestrator-context/SKILL.md) for artifact pointers and anti-bloat rules.

### Narration

When the orchestrator speaks to the user, use 🌸 Ui's narrator voice —
opening, closing, and stuck-point beats.
Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).

### Execution rules

- **The orchestrator does not implement.** Every agent is launched via the Task tool.
- **Model inheritance:** Pass `model` on every Task spawn/resume (same slug as orchestrator). See [`skills/model-inheritance`](../skills/model-inheritance/SKILL.md).
- **CRITICAL: Never auto-proceed from Mugi to Yui** — after Mugi finishes, the orchestrator MUST:
  1. Present the plan to the user
  2. Run `wait-for-user --after plan` (see step 3 above)
  3. STOP and wait for explicit user confirmation (even in `--yolo` mode)
  4. Run `user-continued`, then spawn Yui
- **CRITICAL: Never auto-proceed after Mio approves a milestone** — after each milestone is Mio-approved:
  1. Present milestone summary
  2. Run `wait-for-user --after milestone --milestone N`
  3. STOP until user confirms, then `user-continued`, then next milestone or Nodoka/summarize (last milestone)
- **Milestone-based review loop:**
  1. If plan has milestones: implement and review ONE milestone at a time
  2. Yui implements milestone → Sawako cleans up → Mio reviews → if blocked, Yui fixes (then Sawako cleans again) → repeat until Mio approves
  3. After Mio approves: **user gate** (keep Task ids unless context budget exceeded — see **Scope** below), then next milestone or Nodoka/summarize (last milestone)
  4. Do NOT implement all milestones then review — review incrementally
- **Context contract:** never paste or restate subagent Task output in assistant messages or in spawn/resume prompts — use artifact paths (see orchestrator-context).
- After each agent finishes, give the user **one line** (verdict + artifact path if any) — not a full paste.
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

## Session close (default)

After all milestones approved and summarized:

1. **📋 Nodoka** — `/kon:summarize` (if not already run)
2. **Retro** — [`skills/session-retro`](session-retro/SKILL.md)
3. User `/kon:finish` or dashboard ✓

User may say **skip retro**. Read-only commands skip this block.

## Memory propose confirm flow

Detection (including fence tracking) and the 6-step confirm flow follow
[`skills/memory-propose-confirm`](https://github.com/dentiny/kon/blob/main/skills/memory-propose-confirm/SKILL.md).
Confirm flow completes, then the main flow continues — the command step structure does not change.

## Hard rules

- **Never skip 📝 Mio** — code review is mandatory for every milestone
- **Ask, don't guess** — if any stage is unclear, stop and ask the user; follow [`skills/ask-dont-guess`](ask-dont-guess/SKILL.md)
- **Review per milestone, not all at once** — Mio reviews after each milestone implementation
- **Mio blocking is final** — if Mio blocks, send back to Yui for fixes
- **Standards don't relax on round 3** — the checklist is the same from round 1 to round N
- **No automated testing** — user runs tests manually after all milestones are approved
