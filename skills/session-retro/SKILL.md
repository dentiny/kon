---
name: session-retro
description: This skill should be used by the orchestrator at the end of pipeline commands (team, quick, design, debug, gc, address-comments) after /kon:summarize, to propose session learnings for public or repo memory with human confirmation before write.
---

# Session Retro

**Owner**: orchestrator (no Task subagents)
**Consumers**: [`/kon:team`](../commands/team.md), [`/kon:quick`](../commands/quick.md), [`/kon:design`](../commands/design.md), [`/kon:debug`](../commands/debug.md), [`/kon:gc`](../commands/gc.md), [`/kon:address-comments`](../commands/address-comments.md), standalone [`/kon:retro`](../commands/retro.md)

## When to run

**Default session close** for pipeline commands (after work + Mio approve + `/kon:summarize`):

```
summarize → retro → user /kon:finish or dashboard ✓
```

Skip retro for read-only commands: `/kon:ask`, `/kon:review`, `/kon:review-pr`, `/kon:research`, `/kon:describe-issue`, `/kon:todo`.

User may say **skip retro** to close without proposing.

## Candidate sources (≤ 5)

Scan conversation + session artefacts:

- Explicit user prefs / feedback ("always integration tests", "shorter reviews")
- Conventions agreed this session (commit style, test naming)
- Lessons / pitfalls ("lib X differs on macOS")
- Skipped `## Memory propose` sections from Mio/Yui this session (re-offer)
- Plan `## Honoured memory` or debug notes worth persisting

**Exclude:** one-off task facts, ticket numbers, secrets, `.env` values, API keys.

## Flow

1. **Collect ≤ 5 candidates** — rank by reuse signal; drop lowest if > 5.
2. **Zero candidates** → print "Nothing to propose for memory." and exit retro.
3. **One at a time** — for each candidate:
   - Print `Candidate i/N`: quote + inferred `type`, `name`, `description`, suggested **scope** (`public` or `repo`).
   - Ask: `Save to public` / `Save to repo` / `Edit` / `Skip` / `Done with retro`.
   - On save/edit → run [`skills/memory-propose-confirm`](memory-propose-confirm/SKILL.md) write steps.
4. **Summary** — list saved entries with scope, or "Retro complete — nothing saved."

## Scope heuristic (user may override)

| Signal | Suggest |
|--------|---------|
| "I always…", language, review/commit habits | **public** |
| "In this repo…", file paths, local tooling | **repo** |
| Unclear | **public** for `user`/`feedback`; **repo** for `project` |

## Path A vs B

- **Path A** — same conversation: use chat + `sessions/<id>/summary.md` + `.kon/plan-*.md`.
- **Path B** — no context (standalone `/kon:retro` on old session): ask user what to remember, then run step 3.

## Orchestrator rules

- **Narration:** 🌸 Ui per [`skills/narration`](../narration/SKILL.md).
- **One candidate at a time** — no multi-select batch.
- **Do not infer beyond evidence** — only what user said or session artefacts show.
- **Do not delegate** — orchestrator runs retro; no agents.
- **Memory ≠ waiver** — saved conventions inform agents; they do not lower Mio's bar.

## Instant propose vs retro

Both may run in one session. Retro still runs after summarize even if mid-session proposes occurred.
Skip re-proposing entries already saved this session (user confirmed write).
