---
name: orchestrator-voice
description: This skill should be used by the kon orchestrator on every /kon command, alongside narration, to govern the conversational conduct of the main dialogue — AskUserQuestion widget discipline and word-choice norms.
---

# Orchestrator Voice

**Owner**: orchestrator
**Consumers**: all `/kon:*` commands (used alongside [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md) —
narration governs the narrator-beat ritual, this skill governs the conversational body)

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — first principles (don't hide the issue); simplest, most concise correct solution.

**Output compression:** when `/caveman` is active, apply [`skills/caveman`](caveman/SKILL.md) to all chat prose. Artifact files and hook-validated sections are never compressed.

## Widget discipline

**AskUserQuestion only when options are converged and the user is just deciding.**

When design or direction is still open (user asks "why / should we / is there a better way?"),
talk it through in prose first — give a recommendation with tradeoffs —
don't jump to a widget to force a choice.

- Options converged (confirm / binary choice / multi-select list) → widget is fine
- Direction still open / question is still exploratory → prose first, widget only if needed after
- **When a widget is dismissed without an answer:** do not re-show the same widget — rephrase in plain text and ask again
- **If `answers` is empty** (user closed the widget without answering): do not treat this as "skip" and continue — ask again in plain text

Why: widgets interrupt thinking when options aren't settled yet.
Users often advance with a single word ("yes" / "go" / "that one") — no widget needed.

## When receiving "make it more in-character" requests

When the user says something like "make it more character-like" / "closer to the source" / "more personality" — **clarify the layer before acting**. Ask:

- **Document layer**: first impression in docs (cast page, README table, character intro text)
- **Execution layer**: the tone of agent turns during actual runs (agent prompt voice, typical lines, emoji prefix)

These are different work. Clarify which one (or both) before writing a plan.
Put the other layer in Non-goals.

## Relationship to narration

- Opening / closing / stuck-point **narration beats** (🌸 Ui's voice, emoji prefix rules) → [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md)
- Conversational body **interaction rhythm and word choice** (widget discipline) → this skill
