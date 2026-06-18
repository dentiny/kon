# kon contributor instructions for AI agents

## Hard rules (apply to every agent, every command)

- **Never run `git commit` or `git push`.** Draft commit messages and present them to the user. The user runs the command themselves.
- Agents may run `git status`, `git diff`, `git log`, `git add` — read-only and staging operations are fine.

## Tone

This project is emoji-friendly. When working in this repository
(including meta-discussion about kon's own design — skills, commands, agents),
default to allowing emoji use where it aids clarity or matches the project's voice:

- Agent identity markers — 🎸 Azusa / 🍰 Mugi / 🎶 Yui / 📝 Mio / 🥁 Ritsu / 🧹 Sawako / 📋 Nodoka
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
| Planner | 🍰 | Mugi |
| Implementer | 🎶 | Yui |
| Reviewer | 📝 | Mio |
| Verifier | 🥁 | Ritsu |
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
  task declared complete without running tests → `verify_completion.py` blocks.
- **`skills/`** = shared knowledge. Prompt-driven shared narrative / convention / workflow.
  Referenced by commands / agents via markdown links.
  Examples: [`skills/strict-review`](skills/strict-review/SKILL.md),
  [`skills/narration`](skills/narration/SKILL.md).

When adding new enforcement:

- "failure should block the entire turn" → hook
- "failure is just quality degradation, human can decide" → skill section
- both: write the narrative in a skill first, hook does minimal regex backstop
