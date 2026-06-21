---
description: Holistic GitHub PR review — code diff, PR description, existing review comments, and linked issues. Mio only, read-only.
---

# /kon:review-pr

Review a **whole PR** — not just the diff. 📝 Mio evaluates code changes, the PR description,
existing review comments, and any linked GitHub issues.

For **local uncommitted diff only** (no open PR), Mio still reviews the diff; orchestrator tries
`gh pr view` for the current branch when available.

**Unclear which PR?** Ask — follow [`skills/ask-dont-guess`](../skills/ask-dont-guess/SKILL.md).

## Usage

```
/kon:review-pr                         # local diff HEAD; + current-branch PR via gh if exists
/kon:review-pr --staged                # git diff --cached only
/kon:review-pr 42                      # GitHub PR #42 in this repo
/kon:review-pr https://github.com/o/r/pull/42
```

## Scope boundary

- **Review only** — verdict + must-fix + optional suggested title/body updates. No code edits.
- **One agent** — Mio in review-pr mode ([`skills/review-pr`](../skills/review-pr/SKILL.md)).
- Full report saved to **`sessions/<SESSION_ID>/pr-review.md`** (subagentStop hook when installed).
- Requires **`gh`** for PR/issue context when using PR numbers or URLs.

## Flow

1. **Orchestrator** — create session: `command: "/kon:review-pr"`, `steps_pending: ["Mio"]`.
2. **Orchestrator** — gather context per skill (`gh pr view`, `gh pr diff`, linked `gh issue view`, or local diff).
3. **📝 Mio** — `MODE: review-pr`; follow `agents/Mio.md` + `skills/review-pr`.
4. **Orchestrator** — quality check (`teammate_role: Mio`), `complete-agent` → `completed`, present verdict + link to `pr-review.md`.
5. No Nodoka unless `/kon:summarize`.

## Orchestrator rules

- **Do not review yourself** — spawn Mio via Task tool
- **Do not pass `model`** when spawning Mio
- **Narration:** 🌸 Ui per [`skills/narration`](../skills/narration/SKILL.md)
- **No `git commit`, `git push`, `gh pr merge`**
- Skip [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md)

## Comparison

| Item | `/kon:review-pr` | `/kon:review` | `/kon:describe-issue` |
|------|------------------|---------------|-------------------------|
| Agent | 📝 Mio | 📝 Mio | 📚 Jun |
| Scope | PR + comments + issues | local diff | issue + comments |
| Output | `pr-review.md` | `review.md` | `issue-summary.md` |
