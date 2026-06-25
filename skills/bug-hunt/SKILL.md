---
name: bug-hunt
description: This skill should be used for /kon:hunt — read-only bug analysis from source code with best-effort repro SQL and test suggestions. Azusa only; no fixes, no repo writes.
---

# Bug Hunt

**Owner**: 🎸 Azusa
**Consumers**: [`/kon:hunt`](../commands/hunt.md)

Static bug analysis from the codebase. **Read-only** — no file edits, no fixes, no
mutating shell. Output includes **best-effort** repro SQL and test/command
suggestions the user can run themselves.

## When to use

| User wants | Command |
|------------|---------|
| Analyze a bug from code, suggest repro | `/kon:hunt` |
| How does X work? | `/kon:ask` |
| Fix a bug (repro + patch + review) | `/kon:debug` |

## Read-only hard floor

Same as [`/kon:ask`](../commands/ask.md) — **zero repo writes**.

| Action | Allowed? |
|--------|----------|
| Read / Glob / Grep source | ✅ |
| Read-only git (`log`, `diff`, `show`, `status`) | ✅ |
| Run **read-only** inspection commands (`cat`, `python3 -c` print-only) | ✅ |
| Run tests that mutate repo / create caches | ❌ (suggest command only) |
| Write / edit project files | ❌ |
| Write session artifact `hunt.md` under `~/.kon/` | ✅ (hook or orchestrator) |
| `git commit` / `git push` / checkout / reset | ❌ |

## Analysis rules

1. **Evidence first** — every claim cites `path:line` or command output you read
2. **Confidence labels** — root cause: `high` | `medium` | `low` | `unknown`
3. **Unknown stays unknown** — no invented behavior or file paths
4. **No fixes** — optional "fix direction" bullets only; no patches or edits
5. **Best-effort repro** — SQL/tests/commands are **hypotheses**; label assumptions

## Output artifact

Follow [`templates/bug-report.md`](../templates/bug-report.md) — user intake at top, analysis from **Code trace** down. Persist to `sessions/<session-id>/hunt.md`.

## Repro guidelines (best-effort)

### SQL

- Only when the bug involves queries, schema, or data shape
- Prefix with schema/table assumptions: `-- assumes: users(id), orders(user_id)`
- Prefer minimal `SELECT` / `EXPLAIN` that would expose the bug
- Mark: `**Best-effort repro SQL** — verify table/column names against your schema`

### Tests / shell

- Suggest `pytest path::test_name -xvs` or minimal repro script **as text**
- Do not run pytest unless the user explicitly asked and it is read-only safe
- Include expected vs actual when inferable from code

### When repro is unclear

Say what you'd need (sample row, env var, failing log line) — do not fabricate repro.

## Required output sections

```markdown
## Loaded memory entries
(follow memory-loading skill)

## Summary
(from user report — restate briefly)

## Expected behavior
## Actual behavior
## Steps to reproduce
## Observed evidence
## Scope

## Code trace
- `path:line` — what this code does in the failure path

## Likely root cause
(confidence: high|medium|low|unknown)
(plain-language explanation tied to evidence)

## Contributing factors
(optional — edge cases, missing guards, race windows)

## Best-effort repro
### SQL
(optional — or "N/A")

### Tests / commands
(suggested commands only — user runs them)

## Fix direction (optional)
(bullets only — no implementation)

## If you want this fixed
→ `/kon:debug` for repro + patch, or `/kon:quick` for a small fix
```

## Orchestrator handoff

```markdown
## Orchestrator handoff
- **Verdict**: done | blocked | needs direction
- **Artifact**: `sessions/<session-id>/hunt.md`
- **Next**: present analysis to user | ask user for missing context
- **Note**: one sentence
```

Artifact persisted by subagentStop hook when installed; orchestrator may also write
`hunt.md` via `kon_session.py artifact-path --name hunt.md`.
