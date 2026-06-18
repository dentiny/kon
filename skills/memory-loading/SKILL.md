---
name: memory-loading
description: This skill should be used by all kon agents at startup, before beginning work, to load relevant cross-project memory entries with relevance-based ordering and a 10-entry cap. Consumers: Azusa, Mugi, Mio, and any future agent that reads ~/.config/kon/memory/.
---

# Memory Loading

**Owner**: all agents
**Consumers**: [`agents/Azusa.md`](https://github.com/dentiny/kon/blob/main/agents/Azusa.md), [`agents/Mugi.md`](https://github.com/dentiny/kon/blob/main/agents/Mugi.md), [`agents/Mio.md`](https://github.com/dentiny/kon/blob/main/agents/Mio.md)

## Why this skill exists

Three agents run the same "read memory → schema check → fallback" flow at startup,
but each used to duplicate the logic in their own prompt.
This skill is the single source of truth for that shared behavior.

## Standard 5-step flow

Before starting work, load cross-project memory:

1. **`cat ~/.config/kon/memory/MEMORY.md`** — read the index
2. **Read each index line** `- [Title](file.md) — description`, identify which descriptions overlap with the current task's keywords / topic
3. **Sort by relevance**: rank matched entries by how closely they match the current task
4. **Load top 10**: if too many entries match, read only the top 10 by relevance
5. **Print `## Loaded memory entries`** at the start of output, listing which entries were used

## Schema check (lazy)

For each loaded entry's frontmatter, check for:

- Missing `name` / `description` / `type` field
- `type` value not in `{user, feedback, project, reference}`

On a problem: **do not abort**, continue using the entry (lenient), but append `[schema warn: <what's missing or invalid>]` to the entry's line in `## Loaded memory entries`.

## Fallback rules (no errors, no complaints, keep working)

- `~/.config/kon/memory/` doesn't exist → treat as "no memory"
- `MEMORY.md` doesn't exist or is empty → treat as "no memory"
- No relevant entries in the index → treat as "no memory"

Do not ask the user to create the memory directory or index.
To enable memory, run once: `bash ~/Desktop/kon/scripts/bootstrap_memory.sh` (creates the index).

## Output format example

```
## Loaded memory entries
- [Integration test preference](integration-test-preference.md) — loaded
- [Some entry](some-entry.md) — loaded [schema warn: missing type]
(if no relevant entries: "(no relevant entries)")
```

## Agent-specific extensions

Each agent can add extensions on top of this base after loading:

- **🍰 Mugi (Planner):** If there are relevant `project` or `user` entries, add `## Honoured memory` at the top of the plan showing how each preference affects the step arrangement — so 🎶 Yui can absorb the user's preferences from the plan alone. See `agents/Mugi.md`.
- **📝 Mio (Reviewer):** For `type: project` entries, collect the `triggers` field and append any found skill files as checklist items 10+. See `agents/Mio.md`.
- Other agents with additional needs: document them in the agent's own file, not here.
