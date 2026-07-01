---
name: github-issue-summary
description: Summarize a GitHub issue and all discussion comments. Used by /kon:describe-issue (Jun). Writes sessions/<id>/issue-summary.md.
---

# GitHub Issue Summary

**Owner**: 📚 Jun (describe-issue mode)
**Consumers**: [`/kon:describe-issue`](../commands/describe-issue.md)

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — first principles (don't hide the issue); simplest, most concise correct solution.

## Orchestrator: gather context

```bash
gh issue view <N> --json title,body,state,labels,assignees,author,createdAt,updatedAt,comments,milestone,projectItems
```

For URLs: `gh issue view https://github.com/owner/repo/issues/N --json ...`

Include **every comment** (issue + review discussion). Pass full thread to Jun as `ISSUE_CONTEXT`. Set `MODE: describe-issue` and `ISSUE_FILE: sessions/<SESSION_ID>/issue-summary.md`.

If `gh` fails (no auth, wrong repo), ask the user for issue text or paste — do not hallucinate comments.

## Write artifact

Jun **must** write structured markdown to `ISSUE_FILE` and reference that path in chat output.

## Required file & output sections

In **`issue-summary.md`** and echoed in chat:

```markdown
# Issue: <title>

**Number**: #N  
**State**: open | closed  
**Labels**: …  
**Author / created**: …

## Issue summary
<What the issue asks for, in plain language — 2–5 sentences>

## Discussion summary
<Chronological or thematic summary of **all** comments — who said what, decisions, disagreements>

## Consensus / decisions
<What participants agreed on, or "(none yet)">

## Open questions
<Unresolved asks, blockers, or "(none)">

## Suggested next steps
<Concrete actions for implementer or PM — optional if issue is informational only>
```

Chat output must include:

```
## Loaded memory entries
...

## Issue summary
<one-line pointer>

Written summary to `<ISSUE_FILE>`.
```

## Hard rules

- **Read-only** for application source — only write `issue-summary.md`
- **No `gh issue close` or comment posting**
- **Do not skip comments** — summarize the full thread; if truncated by length, list omitted comment IDs/timestamps
