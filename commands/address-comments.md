---
description: Fetch review comments on the current branch's PR, triage with the user, route each item to /kon:quick or /kon:team, implement one work item at a time. Blocks if no PR.
---

# /kon:address-comments

Work through **existing** GitHub review comments on the PR for your **current branch** —
fetch → user picks which to handle → routing plan → implement via `/kon:quick` or `/kon:team`.

**Orchestrator runs steps 1–4 directly (no agents). Step 5 delegates each work item to
[`/kon:quick`](quick.md) or [`/kon:team`](team.md).**

**Unclear which comments matter?** Ask — follow [`skills/ask-dont-guess`](../skills/ask-dont-guess/SKILL.md).

## Usage

```
/kon:address-comments
```

No arguments — always targets the **current branch's** open PR. No PR → hard stop (step 1).

## Scope boundary

- **Implements code** — unlike `/kon:review-pr` (read-only).
- **No GitHub writes** — no replies, no resolve thread, no push, no merge.
- **No auto-commit** — draft commit messages per work item; user runs `git commit` (kon hard rule).
- **Artefact:** `.kon/pr-comments.md` (triage + progress).
- Requires **`gh`** CLI authenticated.

## Flow

Orchestrator runs steps 1–4; step 5 spawns agents per routed work item.

### 1. Pre-flight gate — no PR → stop

Check in order; **any failure → print error and stop** (do not continue):

| Check | Command | On failure |
|-------|---------|------------|
| Inside git repo | `git rev-parse --is-inside-work-tree` | Not in a git repo — need a branch with a PR. |
| `gh` available + logged in | `gh auth status` | `gh` not installed or not logged in — run `gh auth login`. |
| Current branch has a PR | `gh pr view --json number,title,url,state,headRefName,baseRefName,isDraft` | Current branch has no PR — open one first. |

`gh pr view` with no args resolves the current branch's PR. Non-zero exit or
"no pull requests found" → **no PR**, stop.

On success, record `number`, `title`, `url`, `headRefName`, `baseRefName`.
If PR is `MERGED` / `CLOSED`, do not block — flag status when listing comments.

### 2. Fetch GitHub comments

Orchestrator runs `gh` directly. Collect all three sources; mark `n/a` if a source is empty
(do not abort on a single empty source).

**Inline review threads** (diff line comments, including resolved/outdated) — GraphQL for `isResolved`:

```bash
gh api graphql -f query='
query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$number){
      reviewThreads(first:100){ nodes{
        isResolved isOutdated
        comments(first:50){ nodes{ author{login} body path line url } }
      }}
    }
  }
}' -F owner=<owner> -F repo=<repo> -F number=<number>
```

`<owner>` / `<repo>`: `gh repo view --json owner,name -q '.owner.login+" "+.name'`.

**Review summaries** (APPROVE / REQUEST_CHANGES / COMMENT + body):

```bash
gh pr view --json reviews
```

`--json reviews` omits `url` — supplement with GraphQL:

```bash
gh api graphql -f query='
query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$number){
      reviews(first:100){ nodes{ id state body url author{login} submittedAt } }
    }
  }
}' -F owner=<owner> -F repo=<repo> -F number=<number>
```

**Conversation comments** (PR timeline, not on diff lines):

```bash
gh pr view --json comments
```

Record **`url`** for every comment (inline, review, conversation) for triage and finale reply drafts.

**If all sources combined have zero comments** → print
"PR #`<number>` has no review comments to address." and **exit normally** — not an error.

### 3. List comments — user picks which to handle

Number each comment. **Collapse resolved/outdated threads** by default (one line:
"N resolved/outdated threads skipped — say `include resolved` to expand"). List the rest:

```
C1  [inline · unresolved]  src/auth.py:42  @reviewer
    "None check missing here — IndexError on empty input."
C2  [review · REQUEST_CHANGES]  @reviewer
    "Overall OK but error path needs tests."
C3  [conversation]  @reviewer
    "Why not use a dataclass here?"
```

Ask the user **which to address**:

- ≤ 4 comments → list each as a selectable option in your question.
- \> 4 comments → ask for ids (`C1 C3`) or `all unresolved`.

Not every comment needs a code change (C3 may be reply-only). User picks; orchestrator does not
auto-select all or none. Zero selected → print "No comments selected." and exit normally.

### 4. Write triage + routing plan — user confirms

Write selected comments to `.kon/pr-comments.md` (`mkdir -p .kon` if needed) and propose work items:

```markdown
# PR comments: <PR title> (#<number>)

- **PR**: <url>
- **Branch**: <head> → <base>
- **Fetched at**: <ISO8601 UTC, `date -u +%Y-%m-%dT%H:%M:%SZ`>

## Selected comments
- **C1** — inline src/auth.py:42 @reviewer — "<truncated body>" — <url>
- **C2** — review REQUEST_CHANGES @reviewer — "<truncated body>" — <url>

## Work items
### W1 — Add None guard in src/auth.py
- **Comments**: C1
- **Route**: /kon:quick  ← single file, mechanical fix
- **Status**: pending

### W2 — Add error-path tests
- **Comments**: C2
- **Route**: /kon:team  ← cross-file, needs explore + plan
- **Status**: pending
```

**Group** related comments (same file/area/same concern) into one work item.

**Routing** (one route + one-line rationale per work item):

| Signal | Route |
|--------|-------|
| Single file, local, mechanical (typo, rename, type hint, one guard) | `/kon:quick` |
| Cross-file, behavior change, needs explore or plan | `/kon:team` |

**Default toward `/kon:quick`** — most review feedback is local. When unsure → `/kon:team` (safer).

Present the work-item list + routes to the user. **Wait for explicit approval** before step 5.
User may adjust grouping or routes — reprint plan until confirmed. "Cancel" → stop (triage file may remain).

Also ask (same turn): after each work item, prefer **separate commits** (default) or **one commit at the end**?

### 5. Implement work items one at a time

After user confirms, run work items **in triage order**:

- **Route `/kon:quick`** → full flow in [`commands/quick.md`](quick.md)
- **Route `/kon:team`** → full flow in [`commands/team.md`](team.md)

Task description for each = comment text + triage context (file, line, what reviewer wants).

- Before start: set work item `Status` → `in-progress` in `.kon/pr-comments.md`
- After Mio approves: set `Status` → `done`; if stuck per failure-handling → `blocked`
- Failure handling, Mio blocks, 2× same must-fix → stop and ask user per
  [`skills/failure-handling`](../skills/failure-handling/SKILL.md)
- One work item blocked → mark `blocked`, **continue remaining items**, note in finale summary
- **Testing is manual** after each work item (user runs tests)

**Commit policy (kon override):** Never run `git commit` or `git push`. After each **done**
work item, draft a commit message per [`skills/commit-message`](../skills/commit-message/SKILL.md)
and present it. **Recommend** the user commit before the next work item so the next Yui/Mio cycle
sees a clean diff — but do not commit for them.

If user chose "one commit at the end", accumulate drafts and present a single combined message in finale.

### 6. Finale

After all work items:

1. **Mapping table** — each selected comment → work item → `done` / `blocked` + files changed.
2. **Reply drafts (do not post)** — for each **done** comment, give the original comment **url**
   and a **single fenced code block** with plain reply text (user copies into GitHub).
   If reply body may contain triple backticks, use a four-backtick outer fence.
   Do not use `>` blockquotes for the copyable body.
3. **Commit message drafts** — list draft message(s) per work item (or one combined if user chose).
   User runs `git add` / `git commit` themselves.

4. **Session close** — `/kon:summarize` → [`skills/session-retro`](../skills/session-retro/SKILL.md) → user `/kon:finish` (may **skip retro**).

## Session tracking

Create session at start:

```bash
python3 $KON_ROOT/scripts/kon_session.py init \
  --command "/kon:address-comments" --task "PR #<number>: <title>"
```

Steps 1–4: orchestrator-only (no `complete-agent` for agents). Step 5: `complete-agent` after
each Yui / Mio / Sawako step per inner route. Follow [`skills/session-tracking`](../skills/session-tracking/SKILL.md).

## Memory propose confirm flow

Steps 1–4 produce no Memory propose. Step 5 inner routes (`/kon:quick`, `/kon:team`) run their
own [`skills/memory-propose-confirm`](../skills/memory-propose-confirm/SKILL.md) as usual.

## Orchestrator rules

- **Narration:** 🌸 Ui per [`skills/narration`](../skills/narration/SKILL.md)
- **No PR → hard stop** — step 1 gate is non-negotiable
- **Steps 1–4 orchestrator only** — no Task subagents (multi-turn triage needs orchestrator context)
- **User picks comments** — do not auto-select
- **Routing must be confirmed** — no step 5 until user approves plan
- **Do not self-implement or self-review** — step 5 uses Yui / Mio via Task tool
- **No GitHub writes** — replies and resolves are drafts only
- **Only artefact file:** `.kon/pr-comments.md`
- **Never `git commit` or `git push`**

## Comparison

| Item | `/kon:address-comments` | `/kon:review-pr` | `/kon:review` |
|------|-------------------------|------------------|---------------|
| Input | Current branch PR | PR # / URL / local diff | Local uncommitted diff |
| Comment source | GitHub (existing) | GitHub + holistic review | N/A |
| Implements fixes | ✅ | ❌ | ❌ |
| Agents in triage | None (orchestrator) | 📝 Mio | 📝 Mio |
| Agents in fix loop | 🎶 Yui + 📝 Mio (+ 🧹 Sawako on team) | — | — |
| Output | Changes + reply drafts + commit drafts | `pr-review.md` | `review.md` |
