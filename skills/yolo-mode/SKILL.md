---
name: yolo-mode
description: This skill should be used when the user passes --yolo to any kon command. The orchestrator proceeds autonomously through all confirmation checkpoints, accepting defaults and auto-retrying failures. Stops only when genuine human judgment is required.
---

# YOLO Mode

**Owner**: orchestrator
**Consumers**: any `/kon:*` command when the `--yolo` flag is present

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — YOLO does not waive first principles or simplicity; it only skips confirmation checkpoints.

The user set the task and stepped away. Run it. Don't interrupt them for anything
that has a reasonable default or can be retried automatically.

## What changes in YOLO mode

| Normal checkpoint | YOLO behavior |
|-------------------|---------------|
| Wait for user to confirm Mugi's plan | **Still required** — `wait-for-user --after plan` |
| Wait after each milestone Mio-approved | **Still required** — `wait-for-user --after milestone --milestone N` |
| Auto-accept decisions within the plan | Auto-accept all `[**default**]` decisions in Mugi's `## Decisions needed` |
| Ask user when a plan step is ambiguous | If plan has `[**default**]`, use it; otherwise **STOP and ask** — never invent |
| Notify user when Mio blocks | Auto-send must-fix list back to Yui; retry silently |
| Per-agent step summary to user | Suppress — only report at the end (or when stopping) |

Auto-accepted decisions and auto-retries are recorded in the session log
(see `skills/session-tracking`) so the user can review what happened.

YOLO auto-accepts **plan defaults** and retries failures — it does **not** permit guessing unclear requirements. See [`skills/ask-dont-guess`](ask-dont-guess/SKILL.md).

## When to STOP and ask the user — always, even in YOLO mode

1. **Plan confirmation** — After Mugi finishes, always `wait-for-user --after plan` before Yui. YOLO only auto-accepts decisions *within* the approved plan.

2. **Each milestone approved** — After Mio approves each milestone, always `wait-for-user --after milestone --milestone N` before the next milestone or summarize. YOLO does not skip this.

3. **Retry limit reached** (2 consecutive same must-fix) — the loop
   protection has fired; something structural needs human judgment. Stop, explain,
   ask for direction.

4. **No default exists** for a required decision in Mugi's `## Decisions needed` —
   if there is no `[**default**]` and the choice genuinely changes scope or behavior,
   stop and ask. Do not invent a default.

5. **Sawako GC inventory confirmation** — `/kon:gc` always requires the user to
   review the cleanup inventory before files are removed. Never skip this.

6. **Scope expansion beyond the original task** — if implementing correctly would
   require touching files or systems well outside what the user asked about,
   stop and describe the expansion. Do not silently widen scope.

## Final summary (YOLO mode)

When the run completes, give the user a clear summary:

```markdown
## YOLO run complete

**Task**: <task>
**Result**: PASS / BLOCKED

### What happened
- Azusa: <one line>
- Mugi: <one line> (N decisions auto-accepted: <list defaults used>)
- Yui: <one line>
- Sawako: <one line>
- Mio: <one line> (N must-fix items; resolved in M rounds)

### Auto-accepted decisions
1. <decision> → accepted default: <value>

### Anything that needed attention
<only if there were stops or surprises>
```
