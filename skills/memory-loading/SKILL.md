---
name: memory-loading
description: This skill should be used by all kon agents at startup, before beginning work, to load relevant memory from public and repo indexes with relevance-based ordering and a 10-entry cap. Consumers: Azusa, Mugi, Mio, Jun, and any future memory-reading agent.
---

# Memory Loading

**Owner**: all memory-reading agents
**Consumers**: [`agents/Azusa.md`](../agents/Azusa.md), [`agents/Mugi.md`](../agents/Mugi.md), [`agents/Mio.md`](../agents/Mio.md), [`agents/Jun.md`](../agents/Jun.md)

## Storage layout

| Scope | Path | Contents |
|-------|------|----------|
| **Public** (cross-project) | `~/.kon/public/memory/` | User prefs, habits, feedback across repos |
| **Repo** (per project) | `~/.kon/projects/<repo-name>/memory/` | Conventions specific to this checkout |

Each scope has a `MEMORY.md` index plus one file per entry (`<slug>.md`).

Resolve paths when documenting commands:

```bash
python3 $KON_ROOT/hooks/_kon_paths.py public-memory
python3 $KON_ROOT/hooks/_kon_paths.py project-memory
```

Override data root with `KON_DATA_DIR` (default `~/.kon`).

## Standard load flow

Before starting work:

1. **Read both indexes** (if they exist):
   - `~/.kon/public/memory/MEMORY.md`
   - `~/.kon/projects/<repo-name>/memory/MEMORY.md`
2. **Parse index lines** `- [Title](file.md) — description` from each; tag each row with scope `[public]` or `[repo:<name>]`.
3. **Rank by relevance** to the current task (keywords / topic overlap with description).
4. **Repo wins ties** — same topic in both indexes → prefer the repo entry.
5. **Load top 10** entry files total (not 10 per index).
6. **Print `## Loaded memory entries`** listing scope + title for each entry used.

## Schema check (lazy)

For each loaded entry's frontmatter:

- Missing `name` / `description` / `type`
- `type` not in `{user, feedback, project, reference}`

On problem: **do not abort**; append `[schema warn: …]` on that line in `## Loaded memory entries`.

## Fallback rules

- Either index missing or empty → skip that scope, continue
- No relevant entries after ranking → `(no relevant entries)`
- Never ask the user to create directories — `ensure_project_dir` / `bootstrap_memory.sh` handle that

Bootstrap once:

```bash
bash $KON_ROOT/scripts/bootstrap_memory.sh
```

## Output format example

```
## Loaded memory entries
- [public] Integration test preference — loaded
- [repo:kon] Hook path conventions — loaded
(no relevant entries)
```

## Agent-specific extensions

- **🍰 Mugi:** Relevant `project` or `user` entries → optional `## Honoured memory` at top of plan. See `agents/Mugi.md`.
- **📝 Mio:** `type: project` entries → collect `triggers` and append domain skills as checklist items 10+. See `agents/Mio.md`.

Other agents: document extensions in the agent file, not here.
