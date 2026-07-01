---
name: model-inheritance
description: Task subagents must use the orchestrator's model — Cursor defaults to Composer if model is omitted. Applies whenever spawning Task subagents in kon.
---

# Model Inheritance

**Owner**: orchestrator  
**Consumers**: all `/kon:*` commands that spawn Task subagents

## Problem

Cursor **does not** inherit the parent chat model on Task subagents. If you omit `model`, subagents often run on **Composer** while the orchestrator uses **Opus**, **Sonnet**, etc.

Per-agent `model:` lines in `agents/*.md` frontmatter are **not** applied to Task spawns — ignore them for model selection.

## Rule

**Every Task spawn and resume must pass `model=<orchestrator slug>`.**

Use the same slug on resume passes (fix/re-review loops).

## Resolve the slug

1. **Session (preferred)** — recorded automatically from Cursor on each prompt:

```bash
MODEL=$(python3 $KON_ROOT/scripts/kon_session.py get-orchestrator-model --id "$SID")
```

2. **Your runtime** — if the query above is empty, use the model slug from your Cursor session context (the model the user selected in the composer bar).

3. **Overrides** — `KON_ORCHESTRATOR_MODEL` env or `~/.kon/config.json` → `orchestrator_model`.

## Task spawn example

```text
Task(
  subagent_type="generalPurpose",
  model="<same slug as orchestrator>",
  prompt="Read agents/Azusa.md …",
  description="Azusa explore",
)
```

Do **not** rely on `subagent_type="explore"` alone — still pass `model`.

## Verify

After spawning, the subagent label in Cursor should match the orchestrator family (e.g. Opus 4.8 ↔ `claude-opus-4-8-thinking-high`), not Composer 2.5.
