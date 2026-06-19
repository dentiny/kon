---
description: External lookup — Jun searches docs and the web, writes .kon/research.md. Read-only for source code; session tracked.
---

# /kon:research

For questions **outside the repo** — API docs, library behavior, migration guides, upstream specs.
Jun searches, cites sources, and writes `.kon/research.md`.

**Not for codebase questions** — use [`/kon:ask`](ask.md) (🎸 Azusa reads the repo).

## Usage

```
/kon:research <question>
```

Examples:

```
/kon:research what Cursor hook events support followup_message?
/kon:research pytest exit code conventions for CI
/kon:research OAuth2 PKCE flow — official RFC summary
```

## Scope boundary

- **Lookup only** — find, cite, summarize. Do not implement.
- If the answer requires reading **our** code, say so and suggest `/kon:ask` or `/kon:team`.
- If the user wants to **build** from the findings, offer `/kon:team` after Jun finishes.

## Flow

1. **Orchestrator** — create session: `command: "/kon:research"`, `steps_pending: ["Jun"]`.
2. **📚 Jun** — follow [`agents/Jun.md`](../agents/Jun.md) + [`skills/external-research`](../skills/external-research/SKILL.md).
   - Tools: WebSearch, WebFetch, Read, Write (`.kon/research.md` only).
3. **Orchestrator** — quality check, update session (`complete-agent` → `completed`), present summary + link to `.kon/research.md`.
4. No Nodoka unless user runs `/kon:summarize`.

## Read-only hard floor (source code)

| Action | Allowed? |
|--------|----------|
| WebSearch / WebFetch | ✅ |
| Write `.kon/research.md` | ✅ |
| Write / edit application source | ❌ |
| Write plan files | ❌ |
| `git commit` / `git push` | ❌ |

## Comparison

| Item | `/kon:research` | `/kon:ask` | `/kon:team` |
|------|-----------------|------------|-----------|
| Agent | 📚 Jun | 🎸 Azusa | full team |
| Primary source | web / docs | repo | repo + optional Jun |
| Artifact | `.kon/research.md` | none | plan + code |
| Implements | ❌ | ❌ | ✅ |

## After research

To implement from findings:

```
/kon:go <task>    # orchestrator may reuse .kon/research.md; Jun skipped if still valid
```
