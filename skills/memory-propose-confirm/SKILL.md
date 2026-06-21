---
name: memory-propose-confirm
description: This skill should be used by the kon orchestrator when saving memory — from ## Memory propose (Mio/Yui) or session retro at pipeline close. Handles scope selection (public vs repo), confirm flow, and index updates.
---

# Memory Propose Confirm Flow

**Owner**: orchestrator
**Consumers**: pipeline commands that end with retro (see [`skills/session-retro`](session-retro/SKILL.md)) plus mid-session propose from [`/kon:team`](../commands/team.md), [`/kon:quick`](../commands/quick.md), [`/kon:debug`](../commands/debug.md).

Saving is **propose + retro only** (human confirm each write). Browse stored entries with `cat` on the two `MEMORY.md` indexes.

## Storage paths

| Scope | Directory | Index |
|-------|-----------|-------|
| **public** | `~/.kon/public/memory/` | `MEMORY.md` |
| **repo** | `~/.kon/projects/<repo-name>/memory/` | `MEMORY.md` |

Ensure dirs exist before write:

```bash
python3 $KON_ROOT/hooks/_kon_paths.py public-memory
python3 $KON_ROOT/hooks/_kon_paths.py project-memory
```

## Trigger: agent `## Memory propose`

When 📝 Mio or 🎶 Yui output contains `## Memory propose` (outside code fences — see fence rule below),
run confirm flow **before** the next pipeline step.

Required fields: `name` / `slug` / `description` / `body` / `type` / `rationale`.
Missing any → skip with one line: "Memory propose detected but format incomplete — skipped."

## Confirm flow

1. **Format check** (agent propose) or **build candidate** (session retro).
2. **Show both indexes** — print paths to public and repo `MEMORY.md` if they exist.
3. **Print summary** — type, name, description, rationale; suggest **scope**:
   - `public` — user prefs, cross-repo habits, language, feedback
   - `repo` — this repo's paths, tooling, local conventions
   User may override.
4. **Ask user** — `Save to public` / `Save to repo` / `Edit` / `Skip`.
5. On **Save** or **Edit** → **write entry** (step below).
6. On **Skip** → continue main flow, write nothing.

## Write entry

On confirmed save:

1. Resolve target dir from scope (`public` or `repo`).
2. If `<slug>.md` already exists → ask: **Overwrite** / **Rename slug** / **Cancel**.
3. Write `<slug>.md`:

```markdown
---
name: <name>
description: <description>
type: <user|feedback|project|reference>
---

<body>
```

4. Append to that scope's `MEMORY.md` (skip if an identical index line already present):

```markdown
- [<name>](<slug>.md) — <description>
```

5. Print: `Saved [public|repo] <name> → <path>`.

**Rollback on failure:** if index append fails after entry write, remove the new entry file and report error.

## Fence-tracking rule (agent propose only)

Only detect `## Memory propose` **outside** code fences.
Track triple-backtick count from output start; inside a fence (odd count), ignore the heading.

## Memory types

| Type | Typical scope | When to use |
|------|---------------|-------------|
| `user` | public | Personal preferences, language, identity |
| `project` | repo (sometimes public) | Repo conventions, tool choices, patterns |
| `feedback` | public | Process feedback ("reviews too long") |
| `reference` | either | URLs, docs, specs |

## Relationship to retro

**Two save paths only (both require human confirm):**

| When | Trigger |
|------|---------|
| Mid-session | Mio/Yui `## Memory propose` → this skill |
| End of pipeline | Session retro (after `/kon:summarize`) → this skill |

Do not re-propose entries the user already saved this session.

Automatic retro at session close is the primary catch-all; propose handles explicit mid-session signals.
