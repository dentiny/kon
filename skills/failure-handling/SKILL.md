---
name: failure-handling
description: This skill should be used when handling failures in pipeline command flows — Mio blocking with NEEDS_CHANGES / BLOCKED, and infinite-loop protection for repeated same must-fix. Applies to /kon:quick, /kon:team, /kon:debug.
---

# Failure Handling

**Consumers**: [`/kon:team`](https://github.com/dentiny/kon/blob/main/commands/team.md),
[`/kon:quick`](https://github.com/dentiny/kon/blob/main/commands/quick.md),
[`/kon:debug`](https://github.com/dentiny/kon/blob/main/commands/debug.md).

### Mio blocks (NEEDS_CHANGES / BLOCKED)

1. **Send Mio's full output to Yui** — must-fix list + pending evidence + specific改法
2. **Resume 🎶 Yui** (do not respawn with full `agents/Yui.md` if `get-task-agent` has an id) — fix with explicit references to must-fix numbers
3. **Resume 🧹 Sawako** when applicable — delta prompt only
4. **Resume 📝 Mio** (do not respawn with full `strict-review` if id exists) — re-review with delta prompt; verify each prior must-fix item-by-item

See [`skills/teammate-flow`](../teammate-flow/SKILL.md) **Implementation loop — Task resume**.

### Infinite-loop protection

- Mio blocks the **same must-fix 2 consecutive times** → stop, ask the user (the plan itself may be the problem)

**"Same must-fix" definition:** Mio's must-fix item points to the same file + same function/section + same category of problem. Yui changing the wording or the approach but leaving the root problem in place still counts as the same item.
