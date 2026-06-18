---
name: failure-handling
description: This skill should be used when handling failures in go-class command flows — Mio blocking with NEEDS_CHANGES / BLOCKED, Ritsu test failures, and infinite-loop protection for repeated same must-fix or same test ID. Applies to /kon:go, /kon:quick, /kon:team.
---

# Failure Handling

**Consumers**: [`/kon:go`](https://github.com/dentiny/kon/blob/main/commands/go.md),
[`/kon:quick`](https://github.com/dentiny/kon/blob/main/commands/quick.md),
[`/kon:team`](https://github.com/dentiny/kon/blob/main/commands/team.md).

### Mio blocks (NEEDS_CHANGES / BLOCKED)

1. **Send Mio's full output to Yui** — must-fix list + pending evidence + specific改法
2. Yui fixes and reports back with explicit diff/evidence for each must-fix number (not just "fixed them all")
3. Re-run Mio's review. Mio checks item-by-item — any uncleared item keeps it BLOCKED.

### Ritsu's tests fail

1. Send the full failure output to Yui (command + exit code + output)
2. Yui fixes, then Ritsu re-runs — **"I fixed it" from Yui is not a pass**
3. Keep going until all green.

### Infinite-loop protection

- Mio blocks the **same must-fix 2 consecutive times** → stop, ask the user (the plan itself may be the problem)
- Ritsu fails the **same test ID 2 consecutive times** → stop, ask the user (the test itself may need updating)

**"Same must-fix" definition:** Mio's must-fix item points to the same file + same function/section + same category of problem. Yui changing the wording or the approach but leaving the root problem in place still counts as the same item.

**"Same test ID" definition:** identical test runner ID (`path::TestClass::test_method[param]` for pytest, or equivalent). Different error message, same ID → same test.
