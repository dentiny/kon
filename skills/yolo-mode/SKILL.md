---
name: yolo-mode
description: This skill should be used when the user passes --yolo to any kon command. The orchestrator proceeds autonomously through all confirmation checkpoints, accepting defaults and auto-retrying failures. Stops only when genuine human judgment is required.
---

# YOLO Mode

**Owner**: orchestrator
**Consumers**: any `/kon:*` command when the `--yolo` flag is present

The user set the task and stepped away. Run it. Don't interrupt them for anything
that has a reasonable default or can be retried automatically.

## What changes in YOLO mode

| Normal checkpoint | YOLO behavior |
|-------------------|---------------|
| Wait for user to confirm Mugi's plan | Auto-accept all `[**default**]` decisions; proceed immediately |
| Ask user when a plan step is ambiguous | Take the more conservative interpretation; log the choice; proceed |
| Notify user when Mio blocks | Auto-send must-fix list back to Yui; retry silently |
| Notify user when Ritsu fails | Auto-send failure back to Yui; retry silently |
| Per-agent step summary to user | Suppress — only report at the end (or when stopping) |

Auto-accepted decisions and auto-retries are recorded in the session log
(see `skills/session-tracking`) so the user can review what happened.

## When to STOP and ask the user — always, even in YOLO mode

1. **Retry limit reached** (2 consecutive same must-fix or same test ID) — the loop
   protection has fired; something structural needs human judgment. Stop, explain,
   ask for direction.

2. **No default exists** for a required decision in Mugi's `## Decisions needed` —
   if there is no `[**default**]` and the choice genuinely changes scope or behavior,
   stop and ask. Do not invent a default.

3. **Sawako GC inventory confirmation** — `kon gc` always requires the user to
   review the cleanup inventory before files are removed. Never skip this.

4. **Scope expansion beyond the original task** — if implementing correctly would
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
- Mio: <one line> (N must-fix items; resolved in M rounds)
- Ritsu: <one line>

### Auto-accepted decisions
1. <decision> → accepted default: <value>

### Anything that needed attention
<only if there were stops or surprises>
```
