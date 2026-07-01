---
name: commit-message
description: This skill should be used when drafting a git commit message from staged or proposed changes. Produces a user-impact subject and a concise body. Deliberately avoids motivation paragraphs (those belong in the PR description, not the commit log).
---

# Commit Message

**Consumers**: any task that drafts a commit message after a successful run.

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — subject states user impact concisely; no motivation paragraphs or padding.

## Subject rules

- **One line, ≤ 70 chars**, user-impact framing — what changes for the user, not which files were touched
- **Verb-first**: "Add", "Fix", "Allow", "Reject", "Block"
- **No file names in the subject**: "Refactor auth.py" is bad; "Reject empty emails at signup" is good
- **Match existing style**: if the repo uses Conventional Commits (`type(scope): subject`), keep that format; otherwise freeform
  - Detect Conventional Commits: `pyproject.toml` has `[tool.commitizen]`, or `.cz.toml` / `commitlint.config.js` exists

### Bad → Good

| Bad | Good |
|-----|------|
| `update auth.py and tests` | `Reject empty emails before hashing` |
| `fix bug` | `Stop retry storm on 5xx from upstream` |
| `address review comments` | `Enforce non-empty email at signup` |

## Body rules

The body is for the **future bisecting engineer**, not the current reviewer:

- **≤ 3 sentences** total, or equivalent compact bullets
- Cover only: what changed at the user-impact level, breaking-change pointers, irreplaceable invariants
- **Cut**: "why the problem existed", motivation paragraphs, "why we picked X over Y" — all of that belongs in the PR description
- If the subject is already complete and nothing durable remains to add, **omit the body**

## Output format

```
<subject — one line, ≤70 chars, user-impact>

<body — ≤3 sentences; omit entirely if nothing durable to add>
```

Provide raw text to the caller — **do not wrap in a code fence by default** (breaks piping to `git commit -F -`).
When presenting to the user as a readable deliverable, wrap in a single fenced code block.

## No `git commit` — ever

**Agents never run `git commit` or `git push`.** The skill produces text only.
Present the draft in a fenced code block so the user can copy it and run:

```bash
git commit -m "$(cat <<'EOF'
<paste subject here>

<paste body here>
EOF
)"
```

The user decides when and whether to commit.

## No `Co-Authored-By` trailer

kon-drafted commits do not include co-author attribution lines.
