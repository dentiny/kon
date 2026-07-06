---
name: kon
description: >
  Multi-agent software engineering workflow. Use this skill whenever the user
  types a /kon: command — including /kon:team, /kon:design, /kon:quick,
  /kon:debug, /kon:ask, /kon:review, /kon:review-pr, /kon:hunt, /kon:gc,
  /kon:research, /kon:describe-issue, /kon:begin, /kon:finish, /kon:summarize,
  /kon:retro, /kon:address-comments, /kon:todo, /kon:understand-codebase.
  Orchestrates specialized agents: Azusa (explorer), Jun (researcher),
  Mugi (planner), Yui (implementer), Mio (reviewer), Sawako (cleaner),
  Nodoka (summarizer).
---

# kon — Multi-Agent Workflow

## Plugin root (`KON_ROOT`)

Resolve **once** at the start of every kon command:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Resolution order: `KON_ROOT` env → `~/.kon/config.json` → kon clone → `~/Desktop/kon`.
All paths below use `$KON_ROOT/...`.

## Trigger

When the user invokes a **slash command** — `/kon:team`, `/kon:design`, `/kon:quick`, `/kon:debug`, `/kon:ask`, `/kon:review`, `/kon:review-pr`, `/kon:hunt`, `/kon:gc`, `/kon:research`, `/kon:describe-issue`, `/kon:begin`, `/kon:finish`, `/kon:summarize`, `/kon:retro`, `/kon:address-comments`, `/kon:todo`, `/kon:understand-codebase` — **stop answering directly and run the orchestration flow below**.

## Orchestration

### 1. Session file (do this first)

```bash
python3 $KON_ROOT/scripts/kon_session.py init --command "/kon:team" --task "…"
```

### 2. Read the matching command file

| Command | File |
|---------|------|
| `/kon:team` | `$KON_ROOT/commands/team.md` |
| `/kon:design` | `$KON_ROOT/commands/design.md` + `$KON_ROOT/skills/design-debate/SKILL.md` |
| `/kon:quick` | `$KON_ROOT/commands/quick.md` |
| `/kon:debug` | `$KON_ROOT/commands/debug.md` |
| `/kon:ask` | `$KON_ROOT/commands/ask.md` |
| `/kon:review` | `$KON_ROOT/commands/review.md` |
| `/kon:review-pr` | `$KON_ROOT/commands/review-pr.md` |
| `/kon:hunt` | `$KON_ROOT/commands/hunt.md` + `$KON_ROOT/skills/bug-hunt/SKILL.md` |
| `/kon:gc` | `$KON_ROOT/commands/gc.md` |
| `/kon:research` | `$KON_ROOT/commands/research.md` |
| `/kon:describe-issue` | `$KON_ROOT/commands/describe-issue.md` |
| `/kon:begin` | `$KON_ROOT/commands/begin.md` + `$KON_ROOT/skills/interactive-session/SKILL.md` |
| `/kon:finish` / `/kon:summarize` | `$KON_ROOT/commands/summarize.md` |
| `/kon:retro` | `$KON_ROOT/commands/retro.md` + `$KON_ROOT/skills/session-retro/SKILL.md` |
| `/kon:address-comments` | `$KON_ROOT/commands/address-comments.md` |
| `/kon:todo` | `$KON_ROOT/commands/todo.md` |
| `/kon:understand-codebase` | `$KON_ROOT/commands/understand-codebase.md` + `$KON_ROOT/skills/understand-codebase/SKILL.md` |

### 3. Read teammate flow (most commands)

`$KON_ROOT/skills/teammate-flow/SKILL.md` — skip for `/kon:ask`, `/kon:hunt`, `/kon:research`, `/kon:review`, `/kon:review-pr`, `/kon:retro`, `/kon:describe-issue`, `/kon:understand-codebase`.

### 4. Spawn agents

| Step | Agent file |
|------|-----------|
| Explorer | `$KON_ROOT/agents/Azusa.md` |
| Researcher | `$KON_ROOT/agents/Jun.md` + `$KON_ROOT/skills/external-research/SKILL.md` |
| Planner | `$KON_ROOT/agents/Mugi.md` |
| Design challenger | `$KON_ROOT/agents/Azusa-challenge.md` |
| Implementer | `$KON_ROOT/agents/Yui.md` |
| Reviewer | `$KON_ROOT/agents/Mio.md` + `$KON_ROOT/skills/strict-review/SKILL.md` |
| Cleaner | `$KON_ROOT/agents/Sawako.md` |
| Summarizer | `$KON_ROOT/agents/Nodoka.md` |

Implementation loop per milestone: Yui → Sawako → Mio. Resume Yui if Mio blocks. Pause at each milestone gate (`wait-for-user`) before proceeding.

### 5. Narration, failure handling, context

- Narration (🌸 Ui): `$KON_ROOT/skills/narration/SKILL.md`
- Failures: `$KON_ROOT/skills/failure-handling/SKILL.md`
- Anti-bloat: `$KON_ROOT/skills/orchestrator-context/SKILL.md`

## Hard rule

**Never run `git commit` or `git push`.** Draft the commit message; user runs it.
