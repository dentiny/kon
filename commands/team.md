---
description: Full kon run — Azusa explores, Mugi writes a plan, Yui implements, Sawako cleans, Mio reviews. No automated testing.
---

# /kon:team

Hand the task to the full team. From first look to code review, each member handles their part.

## Usage

```
/kon:team <task description>
```

## Flow

Full flow follows [`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md) —
optional **📚 Jun** (external docs, parallel with Azusa) → 🎸 Azusa explores → 🍰 Mugi writes plan →
**WAIT for user confirmation** → **milestone loop**: 🎶 Yui implements milestone → 🧹 Sawako cleans up → 📝 Mio reviews → if blocked, fix and re-review → if approved, next milestone.

When the task needs web/docs lookup, spawn Jun per [`skills/external-research`](https://github.com/dentiny/kon/blob/main/skills/external-research/SKILL.md).

**Milestone-based review loop:**
- After plan approval, Yui implements ONE milestone at a time
- After each milestone implementation, Sawako removes dead code and redundant comments
- Then Mio reviews that milestone's changes only
- If Mio blocks: Yui fixes → Sawako cleans → Mio re-reviews the same milestone
- If Mio approves: proceed to next milestone
- Repeat until all milestones are complete
- **Testing is manual** — after all milestones approved, user runs tests themselves

## Orchestrator rules

- **Model inheritance:** Do NOT pass `model` parameter when spawning subagents — let them inherit parent's model
- **MANDATORY user confirmation:** After Mugi finishes, STOP and wait for user to approve the plan before spawning Yui (even in `--yolo` mode)
- **Milestone-based implementation and review:**
  - Yui implements ONE milestone at a time
  - Sawako cleans up dead code and redundant comments after implementation
  - Mio reviews each milestone's changes after cleanup
  - Loop continues until all milestones are approved
  - Do NOT implement all milestones before review
- Follow [`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md) for full execution rules
- All agents launched via Task tool with no model specification

## Plan reuse (after `/kon:design`)

If a plan file already exists when this command starts — check `.kon/plan-<SESSION_ID>.md` first,
then fall back to the most recent `.kon/plan-*.md` for cross-session reuse (e.g. after `/kon:design`):

1. Read the plan and show a one-line summary (goal + step count).
2. Ask the user: **reuse this plan, or re-run Azusa + Mugi?**
3. **Reuse**: skip Azusa and Mugi; resolve any open items in `## Decisions needed`, then **WAIT for user to confirm the plan** before starting Yui. Pass the existing plan path as `PLAN_FILE` to Yui.
4. **Re-plan**: run Azusa → Mugi as usual. Mugi writes a new `.kon/plan-<SESSION_ID>.md`.

Always confirm plan before implementation — no silent reuse even in `--yolo` mode.

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md).
