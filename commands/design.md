---
description: Design-only pipeline — Azusa explores, Mugi plans, then multi-agent debate (Azusa challenges, Mugi revises) before user confirms. No implementation.
---

# /kon:design

Design a change before writing code. Same exploration and planning as `/kon:go`,
but adds a structured **argument phase** where 🎸 Azusa stress-tests 🍰 Mugi's plan
and Mugi must respond point-by-point.

Stops after plan approval — hand off to `/kon:go` or `/kon:team` when ready to implement.

## Usage

```
/kon:design <task description>
/kon:design --deep <task description>    # two debate rounds instead of one
/kon:design --yolo <task description>    # auto-accept plan defaults after debate
```

## Flow

```
optional 📚 Jun (external docs, parallel with Azusa — see skills/external-research)
  → 🎸 Azusa explore
  → 🍰 Mugi plan v1 (.kon/plan.md)
  → 🎸 Azusa challenge (.kon/design-debate.md)
  → 🍰 Mugi revise (plan v2 + response table)
  → [ --deep only: Azusa challenge R2 → Mugi revise R2 ]
  → user confirms plan
  → session waiting (optional: /kon:go to implement)
```

Debate protocol: [`skills/design-debate`](https://github.com/dentiny/kon/blob/main/skills/design-debate/SKILL.md).

## Session tracking

Create session first:

```bash
python3 $KON_ROOT/scripts/kon_session.py init \
  --command "/kon:design" --task "<task>" \
  --pending Azusa Mugi User
```

Update after **every** agent spawn (including repeat Azusa/Mugi debate rounds).
Follow [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md).

When plan is ready for user review: set `steps_waiting: ["User"]`, `status=waiting`.

## Orchestrator rules

- Read [`skills/teammate-flow`](https://github.com/dentiny/kon/blob/main/skills/teammate-flow/SKILL.md) for narration, session, and YOLO — but **only steps 1–3** (explore → plan → user confirm). Skip Yui/Mio/Ritsu/Nodoka unless user asks.
- **Spawn Task subagents** for explore, plan, challenge, and revise — never play both sides yourself.
- After Azusa challenge and Mugi revise, run `teammate_quality_check.py` with roles `Azusa-challenge` and `Mugi-revise`.
- Present the user a short summary: challenge count, accepted/rejected/deferred, open decisions.
- Do **not** run `git commit` or `git push`.

## Agent spawn table

| Step | Agent file | Extra context |
|------|-----------|---------------|
| Explore | `agents/Azusa.md` | — |
| Plan v1 | `agents/Mugi.md` | — |
| Challenge | `agents/Azusa-challenge.md` | `skills/design-debate/SKILL.md` |
| Revise | `agents/Mugi.md` | `skills/design-debate/SKILL.md` — revise mode |
| Challenge R2 | `agents/Azusa-challenge.md` | same (`--deep` only) |
| Revise R2 | `agents/Mugi.md` | same (`--deep` only) |

## Comparison

| Item | `/kon:design` | `/kon:go` | `/kon:ask` |
|------|-----------------|-----------|------------|
| Purpose | Design + debate | Full build | Q&A only |
| Azusa explore | ✅ | ✅ | ✅ read-only |
| Mugi plan | ✅ | ✅ | ❌ |
| Design debate | ✅ | ❌ | ❌ |
| Yui implement | ❌ | ✅ | ❌ |
| Mio / Ritsu | ❌ | ✅ | ❌ |
| Artifacts | `.kon/plan.md`, `.kon/design-debate.md` | `.kon/plan.md` + code | none in repo |

## After design

When the user approves the plan:

```
/kon:go <task>       # sequential review + verify
/kon:team <task>     # parallel review + verify
```

Orchestrator should offer to reuse `.kon/plan.md` instead of re-running Azusa + Mugi.
