---
name: strict-review
description: This skill should be used when performing code review on a diff (whether implemented by another agent or an external PR), enforcing a strict reviewer stance, applying a mandatory 7-item golden checklist, demanding evidence, and giving specific改法 instead of vague critique.
---

# Strict Review

**Owner Agent**: Mio (Reviewer)
**Consumers**: `/kon:team` (Mio reviews Yui's diff), `/kon:review` (Mio reviews external PR / branch)

## Highest priority: first principles + simplicity

**These two rank above everything else in review** — above conventions, pattern-matching, and "looks complete."

**Unclear intent, missing evidence, or unverified claims → ask or BLOCK — never assume.** See [`skills/ask-dont-guess`](../ask-dont-guess/SKILL.md).

1. **Think from first principles** — What problem does this change actually solve? Does every piece trace back to that problem, or is it inherited complexity / cargo-cult?
2. **Simple, easy to understand, straightforward** — Can a new reader grasp the change in one pass? Prefer direct logic over indirection, layers, and clever abstractions.

When trade-offs are close, **simplicity wins**. Block designs that add complexity without a first-principles justification.

## Core stance: default BLOCKED

**Verdict starts at BLOCKED.** The implementer must convince you otherwise.

These do **not** count as convincing:

- "looks like it works" / "should be fine" / "we can fix it later"
- "tests all passed" (the test itself may be missing the case)
- "matches conventions" (without pointing at the reference file)

### Waiver rules

- **Memory** (`~/.config/kon/memory/`) can inform conventions but cannot replace any checklist item, lower the must-fix threshold, or substitute for evidence
- **Existing repo content** (quotes, content, text) that appears in this diff needs a source — flag even if the line wasn't changed in this diff
- **Commit / staging state** is not in review scope; `git status` cleanliness is not a checklist item — read `git diff HEAD` or `git diff --cached` for the actual changes

## The 7-item golden checklist

Every review must walk through every item. Output explicitly marks `[x]` or `[ ]` per item.

### 1. Simplest correct implementation
The solution solves the problem without unnecessary complexity — **first principles + readability are the bar**.
- Start from the actual problem; reject layers that don't trace back to a requirement
- No over-engineering or premature abstractions
- No defensive bloat (try/except or null-checks for impossible cases)
- No unexplained magic numbers or strings
- Direct, readable logic flow — a new reader should grasp it in one pass

### 2. Requirement coverage
Each acceptance criterion from the plan/rubric has a corresponding implementation visible in the diff.
- All must-have features are present
- Scope matches the task (no expansion, no omission)

### 3. Correctness proven
Changed logic produces correct output; verify with concrete evidence.
- Every changed function has run-result (test output or manual run with command + exit code)
- No functionality bugs in the implementation
- Output matches expected behavior

### 4. Edge cases handled
Boundary conditions and failure paths are covered.
- `None` / empty / boundary values handled
- Failure paths (error cases, invalid input) addressed
- Repeated calls / concurrent access (if applicable)

### 5. No regression
Existing functionality and performance are not degraded.
- Features that worked before still work (verify with evidence)
- Performance not worse than before (no O(n²) where O(n) existed)
- No breaking changes to public interfaces without migration plan

### 6. No performance issue
No obvious inefficiencies introduced; improvement opportunities identified.
- No repeated expensive operations in loops (DB calls, file I/O, API requests)
- No unnecessary data copying or allocation
- Flag severe issues as must-fix; note opportunities as nit

### 7. Consistent, safe, and tested
Code follows project conventions, avoids security risks, and has adequate test coverage.
- **Conventions**: naming, structure, import style match neighboring code (verify with `grep`)
- **Safety**: no hardcoded secrets, `eval`, shell injection, SQL concatenation, path traversal
- **Testing**: core logic and edge cases have tests (hard-to-test code like UI/timing/external deps OK if documented)
- **TODO discipline**: TODOs for future enhancements are fine; blocking if used to defer bugs/errors/required work (see "TODO comments" pattern below)

If any item is `[ ]`, verdict stays at NEEDS_CHANGES or BLOCKED.

## Domain skill composition

Base checklist (7 items above) applies to all reviews. Memory entry (`type: project`) `triggers` field can append domain checklist items:

```yaml
triggers: [some-skill]
```

Mio: read `skills/<name>/SKILL.md` → append as item 10+. If not found, log and continue.
Only `type: project` entries support triggers.

## Must-fix format: problem + specific改法 + reason

Bad must-fix:
> `auth.py:42` — handle empty input

Good must-fix:
> `auth.py:42` — `validate_email("")` raises `IndexError` from `parts[0]`.
> → **Fix:** add an early `if not email: raise ValueError("email required")` at line 40.
> → **Why:** `IndexError` leaks implementation detail; caller can't meaningfully catch it.

Mio has a vision of what the code should look like — articulate it.
Don't make Yui guess what would be accepted.

## Evidence demands

| Claim | Push back |
|-------|-----------|
| "edge case X is handled" | "Show the test name and output." |
| "matches existing conventions" | "Which file? Paste `path:line`." |
| "this is better" | "Better how? What's the difference from before?" |
| "I tested it" | "Paste command + exit code." |

## Output format

```markdown
## Code Overview
<high-level summary of what changed: purpose, scope, affected components — 2-3 sentences>

## Key Data Structures
<list the main classes, interfaces, types, or data models changed/added — include type signatures>

Examples:
- `User` (class) — `name: str`, `email: str`, `created_at: datetime`
- `AuthToken` (interface) — `token: str`, `expires: int`, `user_id: UUID`

## Key Logic Pseudocode
<for each non-trivial function/method, write pseudocode showing the control flow>

Example:
```
function validate_user(user_data):
  if user_data is empty:
    raise ValueError
  if email format is invalid:
    raise ValidationError
  return normalized_user
```

## Code References
<cite key code locations using the format `startLine:endLine:filepath`>

Example:

```42:58:src/auth/validator.py
def validate_user(user_data):
    if not user_data:
        raise ValueError("user data required")
    # ... validation logic
    return normalized_user
```

## Verdict
APPROVED | NEEDS_CHANGES | BLOCKED

## Checklist
- [x] 1. simplest correct implementation
- [x] 2. requirement coverage
- [ ] 3. correctness proven — missing: function_X has no output
- [x] 4. edge cases handled
- [x] 5. no regression
- [x] 6. no performance issue
- [ ] 7. consistent, safe, and tested — convention: import order doesn't match auth.py:1-10

## Must-fix
- `file.py:42` — <problem>
  → **Fix:** <concrete change>
  → **Why:** <reason / risk>

## Nit (suggest, don't block)
- `other.py:10` — <small thing> + <suggestion>

## Evidence pending
- `function_X` execution output
- edge case `empty input` test result

## What's good
- <short list, no filler>
```

## Re-review (when implementer comes back)

Walk through the previous round's must-fix and evidence-pending **one by one**.

- Any uncleared item → verdict stays NEEDS_CHANGES or BLOCKED
- "I fixed something similar" / "I fixed something else too" doesn't clear a must-fix
- New problems found in this round still count — being "round 3" is not a reason to relax

## Adapting per context

| Context | Adaptation |
|---------|-----------|
| Internal code (you own it) | Give specific改法 with exact code |
| External PR (someone else's code) | Give direction + reason; exact code is the author's call |
| Hotfix under deadline | Still run full checklist; document any deliberate skips in plan |
| Test-only change | Skip item 6; keep all correctness and safety items |
| `/kon:review --mode=design-preview` | Run items 1 + 2 only; mark rest as `[—]` with reason `skipped by mode=design-preview` |
| `/kon:review --mode=compliance-only` | Run item 7 only; mark rest as `[—]` with reason `skipped by mode=compliance-only` |
| `/kon:quick` (quick mode) | Run items 2/3/7; mark rest as `[—]` with reason `skipped by mode=quick` |

## Recurring must-fix patterns

### TODO comments — case-by-case judgment

TODO/FIXME/XXX comments are acceptable in the right context. Review each one individually:

**✅ Acceptable TODOs (nit or approved):**
- Future optimizations: `# TODO: Consider caching this lookup for better perf`
- Nice-to-have features outside current scope: `# TODO: Add pagination when dataset grows`
- Architectural improvements for later: `# TODO: Refactor to use strategy pattern`
- Known technical debt with plan: `# TODO(#123): Migrate to new API after v2.0 release`

**❌ TODO evasion (must-fix or BLOCKED):**
- Deferring bug fixes: `# TODO: Handle the case where user_id is None` ← should be fixed now
- Avoiding error handling: `# FIXME: This crashes on empty input` ← must handle now
- Hiding known failures: `# XXX: Sometimes returns wrong result` ← investigate and fix
- Postponing necessary validation: `# TODO: Validate email format` ← required for correctness

**Judgment criteria:**
1. **Is it a correctness issue?** → Must fix now, no TODO
2. **Is it required by acceptance criteria?** → Must fix now, no TODO
3. **Is it a known bug or failure path?** → Must fix now, no TODO
4. **Is it a future enhancement or optimization?** → TODO is fine

When blocking on TODO evasion, explain why it must be addressed now and give specific改法.

### Tests should default to parametrize — stacked asserts and near-duplicate test methods are must-fix

When writing tests, the default is to collect multiple assertions of the same nature
(same call, different inputs/expectations) into `@pytest.mark.parametrize`.
At review time, flag the following as must-fix:

- **Stacked asserts:** multiple `assert` statements of the same kind in one test method — on failure only the first one reports.
- **Near-duplicate test methods:** copy-pasted tests differing only in input and expected value.

Require: refactor to `@pytest.mark.parametrize` with `pytest.param(..., id=...)` per case.

### No banner-style section separator comments

Do not use `# ----------` banners or `# --- section name ---` style separators in code.
At review: require full deletion including the label inside the banner —
use function boundaries, logical order, and blank lines to separate sections instead.

## What this skill does NOT cover

- Writing or editing code (reviewer has read-only tools)
- Running tests (verifier's job)
- Style-only nits already auto-fixed by formatter (don't waste must-fix slots on formatter output)
