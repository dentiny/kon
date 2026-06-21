---
description: Session retro — propose preferences and conventions from the current session for public or repo memory. Human confirms each save. Orchestrator only.
---

# /kon:retro

Capture what you learned this session before it disappears.
Orchestrator proposes candidates; you pick **public** (`~/.kon/public/memory/`) or **repo**
(`~/.kon/projects/<repo-name>/memory/`) for each save.

Also runs **by default** at the end of `/kon:team`, `/kon:quick`, `/kon:design`, `/kon:debug`,
`/kon:gc`, and `/kon:address-comments` (after `/kon:summarize`).

## Usage

```
/kon:retro
/kon:retro skip          # explicit no-op when chained after pipeline
```

## Flow

Follow [`skills/session-retro`](../skills/session-retro/SKILL.md).

1. **Orchestrator** — gather ≤ 5 candidates from conversation + session summary + plan/debug artefacts.
2. **Propose one at a time** — scope suggestion + confirm per [`skills/memory-propose-confirm`](../skills/memory-propose-confirm/SKILL.md).
3. **Summary** — what was saved (scope + name) or "nothing saved."

## Session tracking

```bash
python3 $KON_ROOT/scripts/kon_session.py init --command "/kon:retro" --task "session retro"
```

Or reuse the open pipeline session id — do not `init` a second session if one is already open.

## Orchestrator rules

- **No Task subagents** — orchestrator only
- **Narration:** 🌸 Ui per [`skills/narration`](../skills/narration/SKILL.md)
- **Never auto-write** — every entry needs explicit user approval
- **No secrets** in memory candidates

## Comparison

| Item | `/kon:retro` | `/kon:summarize` | `## Memory propose` (mid-session) |
|------|--------------|------------------|-------------------------------------|
| Output | Memory files | `summary.md` | Memory files (if confirmed) |
| Trigger | End of session / manual | End of pipeline | Mio/Yui during team/quick/debug |
| Scope pick | public vs repo | N/A | orchestrator asks scope on save |
