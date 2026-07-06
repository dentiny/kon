---
description: Full kon run — Azusa explores, Mugi writes a plan, Yui implements, Sawako cleans, Mio reviews. No automated testing.
---

# /kon:team

Hand the task to the full team. From first look to code review, each member handles their part.

**Shared principle (design → impl → review):** follow [`skills/core-principles`](../skills/core-principles/SKILL.md) — first principles (don't hide the issue); simplest, most concise correct solution.

**Anything unclear at any stage?** Ask the user before proceeding — never guess. Follow [`skills/ask-dont-guess`](../skills/ask-dont-guess/SKILL.md).

## Usage

```
/kon:team <task description>
```

## Flow

Full flow follows [`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md) —
optional **📚 Jun** (parallel with Azusa) → 🎸 Azusa explores → **pre-plan gate** ([`skills/pre-plan-gate`](../skills/pre-plan-gate/SKILL.md)) → 🍰 Mugi writes plan →
**WAIT for user confirmation** → **milestone loop** (autonomous): 🎶 Yui → 🧹 Sawako → 📝 Mio per milestone → repeat until all complete → **WAIT for user** → summarize / close.

When the task needs web/docs lookup, spawn Jun per [`skills/external-research`](https://github.com/dentiny/kon/blob/main/skills/external-research/SKILL.md).

**Plans:** For non-trivial workflow or architecture, Mugi should add a `## Diagrams` section with mermaid charts (see `agents/Mugi.md`). Every plan must include **`## Current status`** (as-is state + work type + evidence).

**Milestone-based review loop:**
- After plan approval, Yui implements ONE milestone at a time
- Sawako cleans up, then Mio reviews — runs automatically for every milestone
- If Mio blocks: Yui fixes → Sawako cleans → Mio re-reviews until approved
- **After each Mio approval — STOP for user approval** before the next milestone or summarize (`wait-for-user --after milestone --milestone N`)
- Repeat until **all** milestones complete
- **Testing is manual** — after all milestones approved, user runs tests themselves
- **No build during the loop** — Yui/Mio do not run compile/build steps during the milestone loop; see [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md) **No build/compile during the loop**

## Orchestrator rules

- Follow [`skills/orchestrator-context`](../skills/orchestrator-context/SKILL.md) — route by artifact pointer; never paste subagent output in chat or spawn prompts.
- **Model inheritance:** Pass `model` on **every** Task spawn/resume — same slug as the orchestrator. Cursor defaults subagents to Composer otherwise. See [`skills/model-inheritance`](../skills/model-inheritance/SKILL.md); resolve slug via `get-orchestrator-model --id "$SID"`.
- **MANDATORY user confirmation:** After Mugi finishes, STOP before Yui (`wait-for-user --after plan`). After **each** milestone is Mio-approved, STOP before the next milestone or summarize (`wait-for-user --after milestone --milestone N`). The inner Yui → Sawako → Mio fix loop runs autonomously until Mio approves. See [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md).
- **Milestone-based implementation and review:**
  - Yui implements ONE milestone at a time
  - Sawako cleans up dead code and redundant comments after implementation
  - Mio reviews each milestone's changes after cleanup
  - Loop continues until all milestones are approved
  - Do NOT implement all milestones before review
- **Task resume in the impl loop:** Within each milestone, spawn Yui/Sawako/Mio once (full agent + skill), store Task ids in session JSON, **resume** on fix/re-review until Mio approves — then `clear-task-agents`. See [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md) **Implementation loop — Task resume**.
- Follow [`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md) for full execution rules
- All agents launched via Task tool with explicit `model=<orchestrator slug>`

## Plan reuse (after `/kon:design`)

If a plan file already exists when this command starts — check `.kon/plan-<SESSION_ID>.md` first,
then fall back to the most recent `.kon/plan-*.md` for cross-session reuse (e.g. after `/kon:design`):

1. Read the plan and show a one-line summary (goal + step count).
2. Ask the user: **reuse this plan, or re-run Azusa + Mugi?**
3. **Reuse**: skip Azusa, pre-plan gate, and Mugi; resolve any open items in `## Decisions needed`, then **WAIT for user to confirm the plan** before starting Yui. Pass the existing plan path as `PLAN_FILE` to Yui.
4. **Re-plan**: run Azusa → pre-plan gate → Mugi as usual. Mugi writes a new `.kon/plan-<SESSION_ID>.md`.

Always confirm plan before implementation — no silent reuse even in `--yolo` mode.

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md).

## Session close (default)

After all milestones are Mio-approved:

1. **📋 Nodoka** — `/kon:summarize` (see [`commands/summarize.md`](summarize.md))
2. **Retro** — orchestrator runs [`skills/session-retro`](../skills/session-retro/SKILL.md) (propose → user confirms public/repo saves)
3. User closes with `/kon:finish` or dashboard ✓

User may say **skip retro** to finish without memory proposals.
