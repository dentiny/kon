---
name: caveman
description: >
  Compressed chat output mode. Strip filler prose from orchestrator and narrator
  responses while keeping full technical accuracy. Apply to conversational output
  only — narration beats, status lines, agent summaries in chat. Never apply to
  structured artifact files (plan.md, review.md, debug.md) or hook-validated sections.
  Activate with `/caveman [lite|full|ultra]`. Deactivate with "normal mode".
---

# Caveman — Output Compression

**Owner**: orchestrator + 🌸 Ui narrator
**Consumers**: [`skills/orchestrator-voice`](../orchestrator-voice/SKILL.md), [`skills/narration`](../narration/SKILL.md)

Credit: adapted from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman). Same rules, kon-scoped.

**Core principles:** already aligned — "simplest, most concise correct solution" *is* caveman. This skill makes it apply to prose style too.

## Scope

| Apply caveman | Never apply caveman |
|---------------|---------------------|
| Orchestrator chat responses | `plan.md`, `review.md`, `debug.md`, `summary.md` artifacts |
| 🌸 Ui narration beats | Mio's 7-item checklist (hook-validated exact phrases) |
| Agent status summaries in chat | Code blocks, CLI commands, file paths, error strings |
| Inline explanations to the user | `## Decisions needed` / `## Blocked` sections (must be clear for the user to act) |

## Activate

```
/caveman           → full (default)
/caveman lite      → lite
/caveman ultra     → ultra
normal mode        → off
```

Level persists for the rest of the session.

## Rules (when active)

Drop: articles (a/an/the), filler (just/really/basically/actually/simply), pleasantries (sure/certainly/of course/happy to/I'd be happy to), hedging.
Fragments OK. Short synonyms preferred. No self-reference — never announce the mode or narrate tool calls.
Standard tech acronyms OK (API/DB/HTTP/PR). Never invent abbreviations the user can't decode.
Preserve the user's language. Compress style, not language.

Pattern: `[thing] [action] [reason]. [next step].`

| Level | What changes |
|-------|-------------|
| **lite** | Drop filler and hedging. Keep articles and full sentences. Professional but tight. |
| **full** | Drop articles. Fragments OK. Short synonyms. Classic caveman. |
| **ultra** | Abbreviate prose words (config/req/impl/fn). Arrows for causality (X → Y). One word when one word enough. |

## Auto-clarity exceptions

Always revert to full prose for:
- Irreversible action confirmations (`git push --force`, destructive migrations)
- `## Decisions needed` blocks — must be unambiguous for the user to decide
- Security warnings
- Cases where compression itself creates ambiguity (order-sensitive steps)

Resume caveman after the clear part is done.

## Kon persona compatibility

🌸 Ui stays warm but tight — no performative flourishes, no filler scene-setting.
Agent emoji prefixes (🎸 🍰 🎶 📝 etc.) are kept — they're identity markers, not filler.
Mio's dramatic voice in chat can compress. Her artifact checklist stays exact.

## Example

**Before:**
> 🌸 Ui: I've asked 🎸 Azusa to take a look at the codebase and figure out which files are most relevant to your task. She's going to explore the structure and report back with what she finds.

**After (full):**
> 🌸 Ui: 🎸 Azusa exploring. Will report relevant files.
