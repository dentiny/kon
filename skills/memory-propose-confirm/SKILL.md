---
name: memory-propose-confirm
description: This skill should be used by the kon orchestrator whenever a Mio or Yui output contains a ## Memory propose section. Handles the 6-step confirm flow and fence-tracking rules. Applies to /kon:quick, /kon:team, /kon:debug.
---

# Memory Propose Confirm Flow

**Owner**: orchestrator
**Consumers**: [`/kon:team`](https://github.com/dentiny/kon/blob/main/commands/team.md), [`/kon:quick`](https://github.com/dentiny/kon/blob/main/commands/quick.md), [`/kon:debug`](https://github.com/dentiny/kon/blob/main/commands/debug.md)

## Trigger condition

When 📝 Mio or 🎶 Yui output ends with a `## Memory propose` section,
the orchestrator runs the confirm flow immediately after that agent completes —
before continuing to the next step.

## 6-step confirm flow

1. **Format check**: verify the propose section has all 6 required fields:
   `name` / `slug` / `description` / `body` / `type` / `rationale`.
   Missing any field → skip silently with one line: "Memory propose detected but format incomplete — skipped."

2. **Show current memory index**: display `~/.config/kon/memory/MEMORY.md` if it exists.

3. **Print propose summary**: type / name / description / rationale.

4. **AskUserQuestion**: options `Save` / `Edit` / `Skip`.

5. On **Save** or **Edit**:
   - `mkdir -p ~/.config/kon/memory/`
   - Write `~/.config/kon/memory/<slug>.md` with frontmatter + body
   - Append `- [<name>](<slug>.md) — <description>` to `~/.config/kon/memory/MEMORY.md`
   - On Edit: step 4 lets the user modify fields first

6. On **Skip**: continue main flow, write nothing.

Confirm flow completes, then main flow resumes — command step structure does not change.

## Fence-tracking rule

Only detect `## Memory propose` **outside** code fences.
Track triple-backtick count from the start of the output; when inside a fence (odd count), ignore any `## Memory propose` heading.

## Memory types

| Type | When to use |
|------|-------------|
| `user` | Personal preferences, language preferences, identity facts |
| `project` | Repo-specific conventions, tool choices, patterns |
| `feedback` | Past session feedback ("Mio's review was too long") |
| `reference` | External URLs, docs, specs |
