# kon Multi-Agent Workflow

## Plugin root (`KON_ROOT`)

Resolve **once** at the start of every kon command:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Resolution order: `KON_ROOT` env → `~/.kon/config.json` → kon clone → `~/Desktop/kon`.
Override: `export KON_ROOT=/path/to/kon`. Refresh config: run `install_cursor_hooks.sh` from your clone.

All paths below use `$KON_ROOT/...`.

## Trigger

When the user invokes a **slash command**:

- `/kon:begin [goal]`
- `/kon:team <task>`, `/kon:design <task>`, `/kon:quick <task>`, `/kon:debug <bug>`
- `/kon:research <question>`
- `/kon:review`
- `/kon:todo <task>`
- `/kon:ask <question>`
- `/kon:gc` or `/kon:gc <target>`
- `/kon:finish`, `/kon:summarize`

YOLO: `/kon:team --yolo <task>`.

## How to orchestrate

### Interactive mode (`/kon:begin`)

For `/kon:begin`: read `commands/begin.md` + `skills/interactive-session/SKILL.md`.
Create one session; reuse its id for all plain-text follow-ups — **never `init` again** until `/kon:finish`.
Run `kon_session.py active` to get the session id.

### `/kon:ask` — read-only repo, session tracked

For `/kon:ask`: create session JSON first (step 1), then read `commands/ask.md`. Spawn Azusa read-only — no code edits, no plan file, no mutating shell. Update session after Azusa. Skip teammate-flow / Mio–Ritsu validation.

### `/kon:research` / `/kon:review` — skip teammate-flow

For `/kon:research`: read `commands/research.md`, spawn Jun only.
For `/kon:review`: read `commands/review.md`, spawn Mio only (optional Mugi first with `--rubric`).

For `/kon:todo`: read `commands/todo.md`, run `scripts/kon_todo.py` directly — no agents, no session JSON.

### All commands

1. **Session file (do this first)** — `python3 $KON_ROOT/scripts/kon_session.py init --command "/kon:team" --task "…"`. For ask: `--command "/kon:ask"`. See `adapters/cursor/kon.mdc` or `skills/session-tracking/SKILL.md`.

2. Read the matching command file:
   - `/kon:begin` → `$KON_ROOT/commands/begin.md` + `$KON_ROOT/skills/interactive-session/SKILL.md`
   - `/kon:team` → `$KON_ROOT/commands/team.md`
   - `/kon:design` → `$KON_ROOT/commands/design.md` + `$KON_ROOT/skills/design-debate/SKILL.md`
   - `/kon:quick` → `$KON_ROOT/commands/quick.md`
   - `/kon:debug` → `$KON_ROOT/commands/debug.md`
   - `/kon:research` → `$KON_ROOT/commands/research.md`
   - `/kon:review` → `$KON_ROOT/commands/review.md`
   - `/kon:todo` → `$KON_ROOT/commands/todo.md`
   - `/kon:ask` → `$KON_ROOT/commands/ask.md`
   - `/kon:gc` → `$KON_ROOT/commands/gc.md`

3. Read `$KON_ROOT/skills/teammate-flow/SKILL.md` — **skip for `/kon:ask`, `/kon:research`, and `/kon:review`**. For `/kon:debug`, follow `commands/debug.md` (no Mugi; Mio only). For `/kon:design`, also read design-debate. For team/design external lookup, read `skills/external-research/SKILL.md`.

4. For each agent step, spawn a subagent. Include the agent file as the subagent's
   system context in the prompt:

   | Step | Agent file |
   |------|-----------|
   | Explorer | `$KON_ROOT/agents/Azusa.md` |
   | Researcher | `$KON_ROOT/agents/Jun.md` + `$KON_ROOT/skills/external-research/SKILL.md` |
   | Design challenger | `$KON_ROOT/agents/Azusa-challenge.md` |
   | Planner | `$KON_ROOT/agents/Mugi.md` |
   | Implementer | `$KON_ROOT/agents/Yui.md` |
   | Reviewer | `$KON_ROOT/agents/Mio.md` + `$KON_ROOT/skills/strict-review/SKILL.md` |
   | Cleaner | `$KON_ROOT/agents/Sawako.md` |
   | Summarizer | `$KON_ROOT/agents/Nodoka.md` |

5. **Quality checks** — Cursor `subagentStop` auto-validates Task subagent output via `on_subagent_stop.py`. Manual backstop (pipe each agent's full output):

   | Agent | `teammate_role` |
   |-------|-----------------|
   | Azusa | `Azusa` |
   | Jun | `Jun` |
   | Mugi | `Mugi` |
   | Yui | `Yui` |
   | Mio | `Mio` |
   | Sawako | `Sawako` |
   | Nodoka | `Nodoka` |
   | Design challenge | `Azusa-challenge` |
   | Design revise | `Mugi-revise` |

   ```bash
   echo '{"teammate_role":"Mio","teammate_output":"<output>"}' \
     | python3 $KON_ROOT/hooks/teammate_quality_check.py
   ```

6. After Mio approves, spawn **Nodoka** — follow `commands/summarize.md`. Testing is manual.

7. Failure handling: `$KON_ROOT/skills/failure-handling/SKILL.md`.

8. Narration (🌸 Ui): `$KON_ROOT/skills/narration/SKILL.md`.

## Hard rule

**Never run `git commit` or `git push`.** Always present the commit message draft and wait for the user to run it.
