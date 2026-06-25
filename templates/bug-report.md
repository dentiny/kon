# Bug report: <one-line title>

**Session**: `<session-id>` (filled by kon on `/kon:hunt`)  
**Command**: `/kon:hunt`  
**Reported**: `<YYYY-MM-DD>`  
**Severity**: `critical` | `high` | `medium` | `low`  
**Environment**: `<OS, runtime versions, branch/commit if known>`

---

## Summary

<What is broken in one or two sentences.>

## Expected behavior

<What should happen.>

## Actual behavior

<What happens instead — include error messages verbatim when possible.>

## Steps to reproduce

1. …
2. …
3. …

## Observed evidence

- **Error / log**: `…`
- **Failing command**: `pytest path::test_name` → exit code `…`
- **Screenshot / recording**: (link or path, if any)
- **Frequency**: always | intermittent | once

## Scope

- **Feature / area**: …
- **Suspected files** (optional): `path/to/file.py`
- **Started after** (optional): commit, deploy, config change

## Data context (optional)

Use when the bug involves DB, API payloads, or fixtures.

| Field | Value |
|-------|-------|
| Table / entity | … |
| Sample id / key | … |
| Related records | … |

---

<!-- Everything below is filled by 🎸 Azusa during /kon:hunt (read-only code analysis). -->

## Code trace

- `path/to/file.py:42` — …

## Likely root cause

**Confidence**: `high` | `medium` | `low` | `unknown`

<Explanation tied to evidence — no speculation stated as fact.>

## Contributing factors

- …

## Best-effort repro

> Verify table names, env vars, and commands against your setup. kon does not run these automatically in hunt mode.

### SQL

```sql
-- assumes: <schema.table(columns)>
SELECT …
```

Or **N/A**

### Tests / commands

```bash
pytest path/to/test.py::test_name -xvs
# expected: …
# actual: …
```

## Fix direction (optional)

- …

## Next steps

| Goal | Command |
|------|---------|
| Fix with repro + patch + review | `/kon:debug <symptom>` |
| Small targeted fix | `/kon:quick <task>` |
| More context only | `/kon:ask <question>` |
