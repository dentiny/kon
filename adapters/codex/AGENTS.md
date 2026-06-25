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
- `/kon:team <task>`, `/kon:design <task>`, `/kon:quick <task>`, `/kon:debug <bug>`, `/kon:hunt <bug>`
- `/kon:research <question>`
- `/kon:review`
- `/kon:review-pr`
- `/kon:address-comments`
- `/kon:describe-issue <#>`
- `/kon:todo <task>`
- `/kon:ask <question>`
- `/kon:gc` or `/kon:gc <target>`
- `/kon:finish`, `/kon:summarize`, `/kon:retro`

YOLO: `/kon:team --yolo <task>`.

## How to orchestrate

### Interactive mode (`/kon:begin`)

For `/kon:begin`: read `commands/begin.md` + `skills/interactive-session/SKILL.md`.
Create one session; reuse its id for all plain-text follow-ups — **never `init` again** until `/kon:finish`.
Run `kon_session.py active` to get the session id.

### `/kon:ask` / `/kon:hunt` — read-only repo, session tracked

For `/kon:ask`: create session JSON first (step 1), then read `commands/ask.md`. Spawn Azusa read-only — no code edits, no plan file, no mutating shell. Update session after Azusa. Skip teammate-flow.

For `/kon:hunt`: read `commands/hunt.md` + `skills/bug-hunt/SKILL.md`. Azusa only — bug analysis + best-effort repro SQL/tests; artifact `hunt.md`. Skip teammate-flow.

### `/kon:research` / `/kon:review` — skip teammate-flow

For `/kon:research`: read `commands/research.md`, spawn Jun only.
For `/kon:review`: read `commands/review.md`, spawn Mio only (optional Mugi first with `--rubric`).
For `/kon:review-pr`: read `commands/review-pr.md`, spawn Mio only.
For `/kon:describe-issue`: read `commands/describe-issue.md`, spawn Jun only.
For `/kon:address-comments`: read `commands/address-comments.md` — orchestrator triage (steps 1–4); step 5 delegates to quick/team.
For `/kon:retro`: read `commands/retro.md` + `skills/session-retro/SKILL.md` — orchestrator only.

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
   - `/kon:review-pr` → `$KON_ROOT/commands/review-pr.md`
   - `/kon:address-comments` → `$KON_ROOT/commands/address-comments.md`
   - `/kon:retro` → `$KON_ROOT/commands/retro.md`
   - `/kon:describe-issue` → `$KON_ROOT/commands/describe-issue.md`
   - `/kon:todo` → `$KON_ROOT/commands/todo.md`
   - `/kon:ask` → `$KON_ROOT/commands/ask.md`
   - `/kon:hunt` → `$KON_ROOT/commands/hunt.md` + `$KON_ROOT/skills/bug-hunt/SKILL.md`
   - `/kon:gc` → `$KON_ROOT/commands/gc.md`

3. Read `$KON_ROOT/skills/teammate-flow/SKILL.md` — **skip for `/kon:ask`, `/kon:hunt`, `/kon:research`, `/kon:review`, `/kon:review-pr`, `/kon:address-comments` (triage only), `/kon:retro`, and `/kon:describe-issue`**. For `/kon:debug`, follow `commands/debug.md`. For `/kon:design`, also read design-debate. For team/design external lookup, read `skills/external-research/SKILL.md`.

4. For each agent step, spawn a subagent. **Implementation loop** (Yui → Sawako → Mio per milestone): spawn once, **resume** until Mio approves — then **`wait-for-user --after milestone --milestone N` / `user-continued`** before next milestone or summarize; **STOP the turn** at each milestone gate. Store Task ids with `kon_session.py set-task-agent`. See `$KON_ROOT/skills/teammate-flow/SKILL.md`. Explore/plan agents: new spawn each time.

   | Step | Agent file (first spawn only) |
   |------|-------------------------------|
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

6. After Mio approves, spawn **Nodoka** — follow `commands/summarize.md`, then **retro** per `skills/session-retro/SKILL.md`. Testing is manual.

7. Failure handling: `$KON_ROOT/skills/failure-handling/SKILL.md`.

8. Narration (🌸 Ui): `$KON_ROOT/skills/narration/SKILL.md`.

9. Orchestrator context (anti-bloat): `$KON_ROOT/skills/orchestrator-context/SKILL.md` — artifacts hold full output; route by file pointer only.

## Hard rule

**Never run `git commit` or `git push`.** Always present the commit message draft and wait for the user to run it.
