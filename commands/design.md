---
description: Design-only pipeline — Azusa explores, Mugi plans, then multi-agent debate (Azusa challenges, Mugi revises) before user confirms. No implementation.
---

# /kon:design

Design a change before writing code. Same exploration and planning as `/kon:team`,
but adds a structured **argument phase** where 🎸 Azusa stress-tests 🍰 Mugi's plan
and Mugi must respond point-by-point.

Stops after plan approval — hand off to `/kon:team` when ready to implement.

## Usage

```
/kon:design <task description>
/kon:design --deep <task description>    # two debate rounds instead of one
/kon:design --yolo <task description>    # suppress per-agent summaries, auto-retry failures
```

## Flow

```
optional 📚 Jun (external docs, parallel with Azusa — see skills/external-research)
  → 🎸 Azusa explore
  → 🍰 Mugi plan v1 (.kon/plan-<session-id>.md)
  → 🎸 Azusa challenge (.kon/design-debate-<session-id>.md)
  → 🍰 Mugi revise (plan v2 + response table)
  → [ --deep only: Azusa challenge R2 → Mugi revise R2 ]
  → STOP: orchestrator waits for user to approve plan
  → session status=waiting (user must run /kon:go or /kon:team to implement)
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
- **Model inheritance:** Do NOT pass `model` parameter when spawning subagents — let them inherit parent's model
- **No unit tests** — Ritsu (verifier) does not run in design phase. Tests are manual in `/kon:team`.
- **Design stops after debate** — After Mugi's final revision, present summary and STOP. Set `status=waiting`. Do NOT proceed to implementation. User must explicitly run `/kon:team` to implement.
- After Azusa challenge and Mugi revise, run `teammate_quality_check.py` with roles `Azusa-challenge` and `Mugi-revise`.
- Present the user a short summary: challenge count, accepted/rejected/deferred, open decisions.
- Do **not** run `git commit` or `git push`.

## Agent spawn table

| Step | Agent file | Extra context |
|------|-----------|---------------|
| Explore | `agents/Azusa.md` | — |
| Plan v1 | `agents/Mugi.md` | `PLAN_FILE: .kon/plan-<SESSION_ID>.md` |
| Challenge | `agents/Azusa-challenge.md` | `skills/design-debate/SKILL.md` + `PLAN_FILE` |
| Revise | `agents/Mugi.md` | `skills/design-debate/SKILL.md` — revise mode + `PLAN_FILE` |
| Challenge R2 | `agents/Azusa-challenge.md` | same (`--deep` only) + `PLAN_FILE` |
| Revise R2 | `agents/Mugi.md` | same (`--deep` only) + `PLAN_FILE` |

## Comparison

| Item | `/kon:design` | `/kon:team` | `/kon:ask` |
|------|-----------------|-----------|------------|
| Purpose | Design + debate | Full build | Q&A only |
| Azusa explore | ✅ | ✅ | ✅ read-only |
| Mugi plan | ✅ | ✅ | ❌ |
| Design debate | ✅ | ❌ | ❌ |
| Yui implement | ❌ | ✅ | ❌ |
| Mio review | ❌ | ✅ | ❌ |
| Testing | ❌ | Manual | ❌ |
| Artifacts | `.kon/plan-<sid>.md`, `.kon/design-debate-<session-id>.md` | `.kon/plan-<sid>.md` + code | none in repo |

## After design

When the user approves the plan:

```
/kon:team <task>       # full team workflow
/kon:go <task>         # alias for /kon:team
```

Orchestrator should offer to reuse the existing plan file (`.kon/plan-<session-id>.md`) instead of re-running Azusa + Mugi.
