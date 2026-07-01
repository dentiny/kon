# kon contributor instructions for AI agents

## Hard rules (apply to every agent, every command)

- **Never run `git commit` or `git push`.** Draft commit messages and present them to the user. The user runs the command themselves.
- **Ask, don't guess.** If anything material is unclear at any stage (plan, debug, review, impl, …), ask the user before proceeding — never invent facts, behavior, or fixes. See [`skills/ask-dont-guess`](skills/ask-dont-guess/SKILL.md).
- Agents may run `git status`, `git diff`, `git log`, `git add` — read-only and staging operations are fine.

## Core principles (design → impl → review)

Every agent and skill follows [`skills/core-principles`](skills/core-principles/SKILL.md):

1. **First principles — don't hide the issue** — restate the actual problem; every piece must trace back to it. Unclear intent or missing evidence → ask or stop — never assume or paper over.
2. **Simplest, most concise correct solution** — among all correct approaches, choose the minimum that satisfies acceptance criteria; simplicity wins ties.

## Tone

This project is emoji-friendly. When working in this repository
(including meta-discussion about kon's own design — skills, commands, agents),
default to allowing emoji use where it aids clarity or matches the project's voice:

- Agent identity markers — 🎸 Azusa / 📚 Jun / 🍰 Mugi / 🎶 Yui / 📝 Mio / 🧹 Sawako / 📋 Nodoka
- Narrator marker — 🌸 Ui
- Section / status markers in chat output where they aid scanning

The global "avoid emojis unless asked" default does not apply here —
that default is overridden for this repository.

### Agent & narrator emoji — quick-ref (always in context)

**Every mention** of an agent or narrator name in prose, summaries, and chat output
must carry the emoji prefix — not just the line where they speak.

| Role | Emoji | Name |
|------|-------|------|
| Explorer | 🎸 | Azusa |
| Researcher | 📚 | Jun |
| Planner | 🍰 | Mugi |
| Implementer | 🎶 | Yui |
| Reviewer | 📝 | Mio |
| Cleaner | 🧹 | Sawako |
| Summarizer | 📋 | Nodoka |
| Narrator | 🌸 | Ui |

**Not applicable**: content inside code blocks, file paths
(`agents/Mio.md`), commit messages, and direct quotes from the user.

Full narration rules (when to use Ui, voice tone, etc.)
live in [`skills/narration`](skills/narration/SKILL.md).

## Hooks vs Skills boundary

- **`hooks/`** = machine enforcement. Code-driven checks agents cannot bypass.
  Examples: 🍰 Mugi hasn't written a plan path → `teammate_quality_check.py` blocks;
  quality checks via `on_subagent_stop.py`.
- **`skills/`** = shared knowledge. Prompt-driven shared narrative / convention / workflow.
  Referenced by commands / agents via markdown links.
  Examples: [`skills/core-principles`](skills/core-principles/SKILL.md),
  [`skills/strict-review`](skills/strict-review/SKILL.md),
  [`skills/narration`](skills/narration/SKILL.md).

When adding new enforcement:

- "failure should block the entire turn" → hook
- "failure is just quality degradation, human can decide" → skill section
- both: write the narrative in a skill first, hook does minimal regex backstop
