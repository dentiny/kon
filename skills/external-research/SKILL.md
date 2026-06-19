---
name: external-research
description: When to spawn 📚 Jun for external lookup — WebSearch/docs/APIs — vs 🎸 Azusa for codebase exploration. Used by /kon:research, /kon:go, /kon:team, and /kon:design.
---

# External Research

**Owner**: orchestrator
**Consumers**: [`/kon:research`](../commands/research.md), [`/kon:team`](../commands/team.md),
[`/kon:team`](../commands/team.md), [`/kon:design`](../commands/design.md)

## Azusa vs Jun

| Question type | Agent | Artifact |
|---------------|-------|----------|
| Where is X in our repo? How does our code work? | 🎸 Azusa | exploration notes (no file, or plan context) |
| What does library Y's API say? What's the migration path? | 📚 Jun | `.kon/research.md` |
| Compare our hook format to Cursor docs | **Both** (parallel) | research + exploration |

**Rule:** repo-first for "our code"; web-first for "their docs".

## When to spawn Jun in `/kon:team` / `/kon:design`

Spawn Jun **in parallel with Azusa** when the task mentions any of:

- External API, SDK, SaaS, webhook, OAuth provider
- Library/framework version upgrade or migration
- "According to docs…", official spec, RFC, Cursor/Anthropic/OpenAI docs
- Error message clearly from a dependency (not our code)
- User explicitly asks to look something up

**Skip Jun** when:

- Pure internal refactor with no new external surface
- `.kon/research.md` already exists for this topic and is still valid (orchestrator reads + confirms reuse)
- User says codebase-only

## `/kon:research` standalone

Read [`commands/research.md`](../commands/research.md). Jun only — no Azusa/Mugi/Yui.

Use when the user asks a lookup question without intending to implement yet.

## Handoff to Mugi

When both ran: Mugi reads `.kon/research.md` (if present) alongside Azusa's exploration
before writing the plan file (`.kon/plan-<session-id>.md`). Add a `## External context` section in the plan summarizing
Jun's recommendations — do not paste raw URLs; link to `.kon/research.md`.

## Orchestrator rules

- Spawn Jun via Task tool with `agents/Jun.md` + this skill
- Jun may **Write** only `.kon/research.md`
- After Jun completes, run quality check with `teammate_role: Jun`
- Do not substitute web search yourself — Jun owns citations and `.kon/research.md`
