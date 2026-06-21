---
description: Summarize a GitHub issue and all discussion comments. Jun only, read-only. Writes sessions/<id>/issue-summary.md.
---

# /kon:describe-issue

Summarize a **GitHub issue** and **every comment** in the thread. 📚 Jun fetches via `gh`,
writes **`sessions/<SESSION_ID>/issue-summary.md`**, and gives a short chat summary.

**Not for PRs** — use [`/kon:review-pr`](review-pr.md) for pull requests.

## Usage

```
/kon:describe-issue 123
/kon:describe-issue https://github.com/org/repo/issues/123
```

## Scope boundary

- **Summarize only** — no code changes, no posting comments, no closing issues.
- **One agent** — Jun in describe-issue mode ([`skills/github-issue-summary`](../skills/github-issue-summary/SKILL.md)).
- Requires **`gh`** authenticated for the repo.

## Flow

1. **Orchestrator** — create session: `command: "/kon:describe-issue"`, `steps_pending: ["Jun"]`.
2. **Orchestrator** — `gh issue view <N> --json title,body,state,labels,comments,...` (see skill).
   Pass `ISSUE_FILE: sessions/<SESSION_ID>/issue-summary.md` in the task prompt.
3. **📚 Jun** — `MODE: describe-issue`; write artifact + chat summary.
4. **Orchestrator** — quality check (`teammate_role: Jun`), `complete-agent` → `completed`.
5. Open `issue-summary.md` locally in your browser/editor.

## Orchestrator rules

- **Do not summarize yourself** — spawn Jun via Task tool
- **No `gh issue comment` / `gh issue close`**
- Skip [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md)

## After Jun

Point user at:

```bash
python3 $KON_ROOT/scripts/kon_session.py artifact-path --id <sid> --name issue-summary.md
```
