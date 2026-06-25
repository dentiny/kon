---
description: Read-only bug hunt — Azusa analyzes bugs from source code and suggests best-effort repro SQL/tests. No fixes, no repo writes.
---

# /kon:hunt

Analyze a **bug from source code** without changing anything. 🎸 Azusa traces
the failure path, states a likely root cause with confidence, and drafts
**best-effort** repro SQL and test commands for you to run.

**Read-only.** No patches, no plan files, no `.kon/` artifacts in the repo.

For **fixes** after analysis, use [`/kon:debug`](debug.md). For general Q&A use
[`/kon:ask`](ask.md).

## Usage

```
/kon:hunt <bug description>
```

Examples:

```
/kon:hunt checkout total wrong when coupon applied twice
/kon:hunt race in session init when two tabs open same project
/kon:hunt N+1 query in dashboard session list for large repos
```

## Bug report template

Copy [`templates/bug-report.md`](../templates/bug-report.md) when filing a bug — fill everything **above** the Azusa divider before running hunt, or paste the filled sections into your `/kon:hunt` prompt.

Artifact output is written to `sessions/<session-id>/hunt.md` using the same structure (hook or orchestrator).

```markdown
# Bug report: <one-line title>

## Summary / Expected / Actual / Steps to reproduce / Observed evidence / Scope
(user intake — see templates/bug-report.md)

## Code trace
## Likely root cause (confidence: …)
## Contributing factors
## Best-effort repro (SQL + tests/commands — user runs them)
## Fix direction (optional)
## Next steps → /kon:debug | /kon:quick
```

## Scope boundary

- **Analysis + repro suggestions only** — do not implement or run mutating tests
- If the user wants a **fix**, finish the hunt and offer `/kon:debug` or `/kon:quick`
- External API/docs gaps → note limits; optional [`/kon:research`](research.md)

## Flow

1. **Orchestrator** — create session: `command: "/kon:hunt"`, `steps_pending: ["Azusa"]`.
   Follow [`skills/session-tracking`](../skills/session-tracking/SKILL.md).
2. **🎸 Azusa** — read [`agents/Azusa.md`](../agents/Azusa.md) +
   [`skills/bug-hunt`](../skills/bug-hunt/SKILL.md).
   - Read-only tools only (same hard floor as `/kon:ask`)
   - Pass `SESSION_DIR` and `HUNT_FILE: hunt.md` (from `artifact-path --name hunt.md`)
3. **Orchestrator** — quality check (optional pipe to `teammate_quality_check.py` with role `Azusa`), `complete-agent` → `status=completed`.
4. **Orchestrator** — present summary + path to `sessions/<id>/hunt.md` (hook writes it when installed).

No Nodoka, no retro, no Mio. User may `/kon:finish` or dashboard ✓.

## Orchestrator rules

- **Narration:** 🌸 Ui opening/closing per [`skills/narration`](../skills/narration/SKILL.md)
- **Do not spawn Mugi, Yui, Mio, Sawako**
- **Do not self-analyze** — spawn Azusa via Task
- **`--yolo` has no effect**
- **Skip** [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md)

## Comparison

| Item | `/kon:hunt` | `/kon:ask` | `/kon:debug` |
|------|-------------|------------|--------------|
| Purpose | Bug analysis from code | Q&A | Fix pipeline |
| Azusa | ✅ hunt mode | ✅ ask mode | ✅ investigate |
| Repro | Best-effort SQL/tests (text) | N/A | Mandatory runtime repro |
| Fixes code | ❌ | ❌ | ✅ |
| Repo writes | ❌ | ❌ | ✅ |
| Session artifact | `hunt.md` | (none) | `debug.md` |
| Auto-complete session | ✅ | ✅ | ❌ (pipeline) |
