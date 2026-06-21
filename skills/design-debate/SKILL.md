---
name: design-debate
description: Multi-agent design argument — Azusa challenges Mugi's plan, Mugi revises. Used by /kon:design after exploration and initial plan draft.
---

# Design Debate

**Consumer**: [`/kon:design`](https://github.com/dentiny/kon/blob/main/commands/design.md).

## Highest priority: first principles + simplicity

Design debate exists to stress-test plans **before** code is written. Both challenger and reviser optimize for:

1. **Think from first principles** — Restate the actual problem in plain language. Does the plan solve *that* problem with the minimum needed, or inherit assumptions / over-engineer?
2. **Simple, easy to understand, straightforward** — Is this the most direct design? Can Yui execute it without navigating unnecessary layers?

Azusa must challenge complexity that lacks first-principles justification. Mugi must revise toward simpler designs when challenges are valid.

**Do not invent risks or requirements** to fill a debate round — if the plan is sound but you lack evidence, say so and ask. Follow [`skills/ask-dont-guess`](../ask-dont-guess/SKILL.md).

Design debate is **real multi-agent argument**, not the orchestrator summarizing both sides.
Each round is a separate Task spawn with the agent file + this skill in context.

## Roles

| Phase | Agent | Mode | Writes |
|-------|-------|------|--------|
| Explore | 🎸 Azusa | default | nothing (report only) |
| Plan v1 | 🍰 Mugi | default | `.kon/plan-<session-id>.md` |
| Challenge | 🎸 Azusa | **challenge** | `.kon/design-debate-<session-id>.md` (challenges section) |
| Revise | 🍰 Mugi | **revise** | `.kon/plan-<session-id>.md` + `.kon/design-debate-<session-id>.md` (responses) |
| Confirm | user | — | — |

## Artifacts

### `.kon/design-debate-<session-id>.md`

Created on first challenge round. Threaded log of argument:

```markdown
# Design debate: <task name>

## Round 1 — Azusa challenges

### C1: <short title>
<why this is a gap, risk, or wrong assumption — cite files/lines>

### C2: ...

## Round 1 — Mugi responses

| ID | Verdict | Response | Plan change |
|----|---------|----------|-------------|
| C1 | accepted | ... | Step 2 split into 2a/2b |
| C2 | rejected | Plan already covers via Step 4 acceptance | none |

## Round 2 — Azusa challenges (only with --deep)
...
```

### `.kon/plan-<session-id>.md`

Mugi writes v1 before debate. After each revise pass, update in place.
Add `## Debate revisions` at the bottom listing what changed and why (one line per accepted challenge).
The plan path is passed as `PLAN_FILE` in the agent task prompt.

## Round limits

| Flag | Debate rounds | When to stop |
|------|---------------|--------------|
| default | 1 | After Mugi revise v2 → user confirm |
| `--deep` | 2 | After second Mugi revise → user confirm |

**Hard cap: 2 rounds.** No round 3 — escalate remaining disagreements to `## Decisions needed` in the plan.

## Challenge rules (Azusa — challenge mode)

Spawn Azusa-challenge with:
- `agents/Azusa-challenge.md`
- this skill
- prompt: read the plan file (pass `PLAN_FILE: .kon/plan-<SESSION_ID>.md`) + exploration notes; **do not** rewrite the plan

Azusa MUST:
- Find **3–7 concrete challenges** (not nitpicks): missing edge cases, convention mismatches, scope creep, untestable steps, hidden dependencies
- Cite codebase evidence for each (`path:line` or observed convention)
- Assign stable IDs: `C1`, `C2`, …
- Write challenges to `.kon/design-debate-<session-id>.md` under `## Round N — Azusa challenges`
- End with a one-line count: "N challenges raised."

Azusa MUST NOT:
- Edit the plan file (`PLAN_FILE`)
- Propose implementation code
- Play both sides ("Mugi might say…")

## Revise rules (Mugi — revise mode)

Spawn Mugi with:
- `agents/Mugi.md`
- this skill
- prompt: read the plan file (pass `PLAN_FILE: .kon/plan-<SESSION_ID>.md`) + `.kon/design-debate-<session-id>.md` latest challenges

Mugi MUST:
- Respond to **every** challenge ID in the response table
- Verdict per row: `accepted` | `rejected` | `deferred` (deferred → move to `## Decisions needed`)
- Update the plan file (`PLAN_FILE`) for all `accepted` items
- Append `## Debate revisions` summarizing accepted changes
- Write the response table under `## Round N — Mugi responses`

Mugi MUST NOT:
- Ignore challenges silently
- Delete the challenge section Azusa wrote

## Orchestrator rules

### Must spawn real agents

- **Never** simulate Azusa's challenges or Mugi's responses in orchestrator prose
- Fire Task subagent for explore, plan, each challenge, each revise
- Log each spawn via `kon_session.py complete-agent` (duplicate agent names OK — log captures rounds)

### Session steps

On init:

```bash
python3 $KON_ROOT/scripts/kon_session.py init \
  --command "/kon:design" --task "<task>" \
  --pending Azusa Mugi User
```

Log summaries distinguish rounds:
- `"Explored — 5 relevant files"`
- `"Plan v1 — 4 steps, 2 decisions"`
- `"Challenge R1 — 5 issues raised"`
- `"Plan v2 — 4/5 accepted, 1 deferred to user"`

After Mugi revise, move `User` to `steps_waiting`, set `status=waiting`.

### Quality checks

After each challenge and revise spawn:

```bash
echo '{"teammate_role":"Azusa-challenge","teammate_output":"<output>"}' \
  | python3 $KON_ROOT/hooks/teammate_quality_check.py

echo '{"teammate_role":"Mugi-revise","teammate_output":"<output>"}' \
  | python3 $KON_ROOT/hooks/teammate_quality_check.py
```

### User confirm

Same as teammate-flow plan gate:
- Present plan + debate summary (not full paste of both files)
- User says "go" to accept defaults in `## Decisions needed`, or answers open items
- **Design stops here** — no Yui/Mio unless user continues with `/kon:team`

### Handoff to implementation

When user wants to build after design:

```
/kon:team <same task>   # skip Azusa+Mugi if a .kon/plan-*.md exists and user confirms reuse
```

Orchestrator should read the existing plan file (`.kon/plan-<SESSION_ID>.md` or most recent `.kon/plan-*.md`) and ask once: "Reuse this plan?" before re-planning.

### YOLO (`--yolo`)

Follow [`skills/yolo-mode`](https://github.com/dentiny/kon/blob/main/skills/yolo-mode/SKILL.md):
- Auto-accept all `[**default**]` in `## Decisions needed` after debate
- Do not skip debate rounds — argument still runs

### Narration

🌸 Ui opening/closing beats per [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
