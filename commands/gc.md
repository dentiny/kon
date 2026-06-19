---
description: Garbage-collect the codebase — Sawako identifies dead code, redundant comments, and bloated docs, presents an inventory for user confirmation, then cleans up. Mio reviews.
---

# /kon:gc

Remove what no longer belongs. Dead code, obvious comments, bloated docs —
Sawako finds them, shows you the list, and cleans up after you confirm.
Behavior stays exactly the same after a gc pass.

## Usage

```
/kon:gc                        # review current working tree
/kon:gc <file or directory>    # target a specific area
```

## Flow

1. **🧹 Sawako** — analyze and produce a **cleanup inventory**:
   - Dead functions / classes / variables (verified via grep, no callers)
   - Unused imports
   - Comments that restate what the code says
   - Docs that duplicate information or describe removed behavior
   Sawako presents the inventory and **waits for user confirmation** before touching anything.

2. **User confirms** (or adjusts the list — user can strike specific items).

3. **🧹 Sawako** — execute the confirmed removals / simplifications.
   Every removal must be verified (no dynamic callers, no export references).

4. **📝 Mio** — lightweight review (`mode=quick`, 4-item subset).
   Focus: nothing behavioral changed, no unsafe patterns introduced.

5. **Manual testing** — User verifies tests still pass after cleanup.

## Invariant

**No behavior changes.** If tests fail after a gc pass, Sawako went too far.
The cleanup must be reverted to the last clean state and re-scoped.
User runs tests manually after Mio approves to verify nothing broke.

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md).

## Orchestrator rules

- **Narration:** use 🌸 Ui for opening/closing beats. Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
- **Always show the inventory first** — never let Sawako silently delete things
- **User confirmation is required** before Sawako executes (no auto-proceed)
- **Remind user to test** — a gc pass that silently breaks tests is worse than no gc at all
