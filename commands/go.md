---
description: Full kon run — Azusa explores, Mugi writes a plan, Yui implements, Mio reviews, Ritsu verifies. Sequential review then verify.
---

# /kon:go

Hand the task to the full team. From first look to final green, each member handles their part.

## Usage

```
/kon:go <task description>
```

## Flow

Full flow follows [`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md) —
🎸 Azusa explores → 🍰 Mugi writes plan → user confirms → 🎶 Yui implements → 📝 Mio reviews → 🥁 Ritsu verifies.

Review and verification run **sequentially** (Mio must pass before Ritsu runs).

## Plan reuse (after `/kon:design`)

If `.kon/plan.md` already exists when this command starts:

1. Read the plan and show a one-line summary (goal + step count).
2. Ask the user: **reuse this plan, or re-run Azusa + Mugi?**
3. **Reuse** (or `--yolo` auto-accept): skip Azusa and Mugi; resolve any open items in `## Decisions needed`, then start Yui.
4. **Re-plan**: run Azusa → Mugi as usual (may overwrite `.kon/plan.md`).

Do not silently reuse — confirm once unless `--yolo` is active.

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md).
