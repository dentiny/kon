---
name: review-pr
description: Holistic GitHub PR review — code diff, PR description, existing review comments, and linked issues. Used by /kon:review-pr (Mio). Read-only; no gh pr merge or code edits.
---

# Review PR (holistic)

**Owner**: 📝 Mio (review-pr mode)
**Consumers**: [`/kon:review-pr`](../commands/review-pr.md)

## Scope

Review the **whole PR package**, not just the diff:

| Input | Review |
|-------|--------|
| **Code diff** | Logic, correctness, edge cases (subset of strict-review — see below) |
| **PR title & body** | Accuracy vs diff, missing test plan, misleading claims |
| **Existing PR review comments** | What reviewers asked for; what's addressed vs still open |
| **Linked GitHub issue(s)** | Requirements from issue body/comments; whether PR satisfies them |

**Ask** if PR number/URL is missing when user clearly means an open GitHub PR — follow [`skills/ask-dont-guess`](../ask-dont-guess/SKILL.md).

## Orchestrator: gather context (before spawning Mio)

### GitHub PR (preferred when user gives number or URL)

```bash
gh pr view <N> --json title,body,author,comments,reviews,reviewDecision,files,closingIssuesReferences
gh pr diff <N>
```

Parse `Fixes #123` / `Closes #456` / `Relates to org/repo#789` from body if not in `closingIssuesReferences`. For each linked issue:

```bash
gh issue view <N> --json title,body,state,labels,comments
```

Include **all** review comments and inline review threads in the prompt (truncate only with a note listing omitted IDs).

### Local only (no PR number)

```bash
git diff HEAD          # default
git diff --cached      # when --staged
gh pr view --json title,body,comments,reviews,files,closingIssuesReferences 2>/dev/null || true
```

If `gh pr view` succeeds for the current branch, treat it like a GitHub PR and include body + comments + linked issues.

Pass gathered text to Mio as `PR_CONTEXT` in the task prompt. Set `MODE: review-pr`.

## Code review bar

Apply the **7-item golden checklist** from [`skills/strict-review`](../strict-review/SKILL.md) to the diff only — mark `[x]`/`[ ]` under `## Code review`. Default verdict starts **BLOCKED** until evidence supports otherwise.

PR description and linked-issue fit are **separate sections** — a perfect diff with a wrong/missing test plan in the body is still NEEDS_CHANGES.

## Required output sections

```
## Loaded memory entries
...

## Verdict
APPROVED | NEEDS_CHANGES | BLOCKED

## PR overview
<title, author, linked issue refs, 1–2 sentence intent>

## Code review
<checklist + must-fix for code; cite file:line>

## PR description review
<Does body match diff? Test plan adequate? Claims supported?>

## Existing review comments
<Bullet per thread: reviewer, ask, addressed? yes/no/partial + evidence>

## Linked issues
<Per issue: requirement summary, satisfied? gaps?>

## Must-fix
<numbered, or "(none)" if APPROVED>

## Suggested updates
<Optional improved title/body snippets — only if current ones are weak>
```

## Hard rules

- Read-only — no code edits, no `gh pr merge`, no `git push`
- **No invented CI results** — cite command output if claiming tests pass
- **Consider every review comment** — do not ignore bot or human threads; say if N/A to current diff
