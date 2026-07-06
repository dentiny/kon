---
name: pre-plan-gate
description: Mandatory understanding check after exploration and before any Mugi planning step. Orchestrator asks high-level and implementation questions; do not spawn Mugi until answers resolve material gaps. Applies to /kon:team, /kon:design, /kon:debug.
---

# Pre-Plan Gate

**Owner**: orchestrator
**Consumers**: [`/kon:team`](../commands/team.md), [`/kon:design`](../commands/design.md), [`/kon:debug`](../commands/debug.md), and `/kon:begin` routes that enter those pipelines

**Core principles:** follow [`skills/core-principles`](core-principles/SKILL.md) and [`skills/ask-dont-guess`](ask-dont-guess/SKILL.md). **Planning without sufficient understanding hides the issue** — do not let Mugi write steps that rest on guessed scope, behavior, or constraints.

## When this gate runs

| Command | After | Before |
|---------|-------|--------|
| `/kon:team` | 🎸 Azusa (+ optional 📚 Jun) | 🍰 Mugi plan |
| `/kon:design` | 🎸 Azusa (+ optional Jun) | 🍰 Mugi plan v1 |
| `/kon:debug` | 🎸 Azusa + orchestrator writes `debug.md` | 🍰 Mugi fix proposals |

**Skip only when:**

- **Plan reuse** on `/kon:team` — user chose to reuse an existing plan that already passed this gate (e.g. after `/kon:design`), and no re-plan.
- **Re-plan** after user explicitly chose re-run Azusa + Mugi — gate runs again.

**Never skip in `--yolo` mode.** YOLO skips checkpoints *inside* an approved plan; it does not skip understanding before planning.

## Orchestrator workflow

1. **Read inputs** (paths only — do not paste bodies into chat):
   - `sessions/<SID>/explore.md` (team/design)
   - `.kon/research.md` if present
   - User's original task / bug description
   - For debug: `sessions/<SID>/debug.md` after Azusa
2. **Summarize Azusa's unknown unknowns** — one line each from `## Unknown unknowns` (omit if section absent).
3. **Ask the user questions** — see **Question mix** below. Use prose or a short numbered list; use AskUserQuestion only when options are converged.
4. **Wait for answers.** Run:
   ```bash
   python3 $KON_ROOT/scripts/kon_session.py wait-for-user --id "$SID" \
     --after decision --summary "Pre-plan understanding — answer questions before Mugi?"
   ```
5. **Evaluate answers.** If material gaps remain → ask follow-ups (same gate; do **not** spawn Mugi). If user says "I don't know" on something that changes the plan → record as open in `understanding.md` and either ask again with narrower options or stop with "cannot plan until X is known."
6. **Write artifact** — `sessions/<SID>/understanding.md` (template below).
7. **Spawn Mugi** with pointer only:
   ```text
   UNDERSTANDING_FILE: sessions/<SID>/understanding.md
   EXPLORE_FILE: sessions/<SID>/explore.md
   PLAN_FILE: …
   Read UNDERSTANDING_FILE before planning. Do not replan without addressing every answered question.
   ```
8. After user answers and before Mugi: `user-continued --summary "Pre-plan understanding complete"`.

## Question mix (mandatory)

Ask **at least 4 questions total**, including **both** categories. Tailor to the task — do not ask generic filler.

### High-level (design / product / scope) — at least 2

Probe whether we understand **what** and **why**:

- Goal and **success criteria** — how will we know this is done?
- **Scope boundaries** — what is explicitly out of scope?
- **Users or callers** affected — who relies on current behavior?
- **Constraints** — time, compatibility, "must not break X", rollout
- **Trade-offs** — simplicity vs completeness, speed vs correctness
- For debug: **expected vs actual behavior**, severity, acceptable fix risk

### Implementation detail — at least 2

Probe whether we understand **how** in *this* codebase:

- Which **module or path** is authoritative for the change?
- **Behavior on edge cases** — empty input, errors, concurrency, backwards compatibility
- **Testing / verification** — what command or manual check proves success?
- **Integration points** — APIs, hooks, config, migrations
- For debug: **repro confirmation**, whether root cause analysis matches user's mental model, constraints on fix shape (minimal vs refactor)

### From exploration

- Turn Azusa **unknown unknowns** into concrete questions when they affect the plan.
- Ask the user: *"Anything else you already know you don't know that Mugi should account for?"* (user may say "none").

## When NOT to proceed to Mugi

Stop and keep asking (or escalate to user) when:

- Success criteria or scope is still ambiguous after one round of answers
- User's answers contradict exploration evidence — reconcile first
- Debug: root cause is **UNKNOWN** in `debug.md` — Mugi must not propose fixes (existing debug rule)
- A question is material and user answered "don't know" with no way to default safely

Put unresolved items in `understanding.md` under `## Blockers` with status **blocked**. Do not spawn Mugi until blockers are cleared or user explicitly accepts planning with documented open risks in `## Decisions needed` later.

## Artifact template (`understanding.md`)

Orchestrator writes this under `sessions/<SID>/understanding.md`:

```markdown
# Pre-plan understanding

**Session**: `<session-id>`
**Command**: /kon:team | /kon:design | /kon:debug
**Task**: <one line>

## Unknown unknowns (from Azusa)
- … or (none)

## Questions and answers

### High-level
1. **Q:** …
   **A:** …

### Implementation
1. **Q:** …
   **A:** …

## User-known gaps
- … or (none)

## Understanding check
- [x] Goal and success criteria — …
- [x] Scope boundaries — …
- [x] Implementation constraints — …

**Status**: ready | blocked
**Blockers**: (none) | …
```

## Mugi consumption

Mugi **must** read `UNDERSTANDING_FILE` and reflect answers in the plan:

- Resolved Q&A → steps or acceptance criteria
- User-known gaps → `## Known unknowns` section
- Azusa unknown unknowns → `## Unknown unknowns` section
- Anything still open → `## Decisions needed` with `[**default**]` only when Mugi can justify a safe default from evidence — never invent to avoid asking

## Voice (orchestrator)

> "Before Mugi plans — a few questions to make sure we're aligned on scope and how this fits the codebase."

> "I still don't have X — need that before planning."

## Related

- [`skills/teammate-flow`](teammate-flow/SKILL.md) — pipeline order
- [`skills/orchestrator-context`](orchestrator-context/SKILL.md) — pointer-only routing
- [`agents/Azusa.md`](../agents/Azusa.md) — `## Unknown unknowns` output
