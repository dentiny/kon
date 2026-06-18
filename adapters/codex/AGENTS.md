# kon Multi-Agent Workflow

**Plugin root**: `~/Desktop/kon` — update this path if you installed kon elsewhere.

## Trigger

When the user invokes a **slash command**:

- `/kon:begin [goal]`
- `/kon:go <task>`, `/kon:team <task>`, `/kon:design <task>`, `/kon:quick <task>`
- `/kon:research <question>`
- `/kon:review`
- `/kon:todo <task>`
- `/kon:ask <question>`
- `/kon:gc` or `/kon:gc <target>`
- `/kon:finish`, `/kon:summarize`

YOLO: `/kon:go --yolo <task>`.

## How to orchestrate

### Interactive mode (`/kon:begin`)

For `/kon:begin`: read `commands/begin.md` + `skills/interactive-session/SKILL.md`.
Create one session; reuse its id for all plain-text follow-ups — **never `init` again** until `/kon:finish`.
Run `kon_session.py active` to get the session id.

### `/kon:ask` — read-only repo, session tracked

For `/kon:ask`: create session JSON first (step 1), then read `commands/ask.md`. Spawn Azusa read-only — no code edits, no `.kon/plan.md`, no mutating shell. Update session after Azusa. Skip teammate-flow / Mio–Ritsu validation.

### `/kon:research` / `/kon:review` — skip teammate-flow

For `/kon:research`: read `commands/research.md`, spawn Jun only.
For `/kon:review`: read `commands/review.md`, spawn Mio only (optional Mugi first with `--rubric`).

For `/kon:todo`: read `commands/todo.md`, run `scripts/kon_todo.py` directly — no agents, no session JSON.

### All commands

1. **Session file (do this first)** — `python3 ~/Desktop/kon/scripts/kon_session.py init --command "/kon:go" --task "…"`. For ask: `--command "/kon:ask"`. See `adapters/cursor/kon.mdc` or `skills/session-tracking/SKILL.md`.

2. Read the matching command file:
   - `/kon:begin` → `~/Desktop/kon/commands/begin.md` + `~/Desktop/kon/skills/interactive-session/SKILL.md`
   - `/kon:go` → `~/Desktop/kon/commands/go.md`
   - `/kon:team` → `~/Desktop/kon/commands/team.md`
   - `/kon:design` → `~/Desktop/kon/commands/design.md` + `~/Desktop/kon/skills/design-debate/SKILL.md`
   - `/kon:quick` → `~/Desktop/kon/commands/quick.md`
   - `/kon:research` → `~/Desktop/kon/commands/research.md`
   - `/kon:review` → `~/Desktop/kon/commands/review.md`
   - `/kon:todo` → `~/Desktop/kon/commands/todo.md`
   - `/kon:ask` → `~/Desktop/kon/commands/ask.md`
   - `/kon:gc` → `~/Desktop/kon/commands/gc.md`

3. Read `~/Desktop/kon/skills/teammate-flow/SKILL.md` — **skip for `/kon:ask`, `/kon:research`, and `/kon:review`**. For `/kon:design`, also read design-debate. For go/team/design external lookup, read `skills/external-research/SKILL.md`.

4. For each agent step, spawn a subagent. Include the agent file as the subagent's
   system context in the prompt:

   | Step | Agent file |
   |------|-----------|
   | Explorer | `~/Desktop/kon/agents/Azusa.md` |
   | Researcher | `~/Desktop/kon/agents/Jun.md` + `~/Desktop/kon/skills/external-research/SKILL.md` |
   | Design challenger | `~/Desktop/kon/agents/Azusa-challenge.md` |
   | Planner | `~/Desktop/kon/agents/Mugi.md` |
   | Implementer | `~/Desktop/kon/agents/Yui.md` |
   | Reviewer | `~/Desktop/kon/agents/Mio.md` + `~/Desktop/kon/skills/strict-review/SKILL.md` |
   | Verifier | `~/Desktop/kon/agents/Ritsu.md` |
   | Cleaner | `~/Desktop/kon/agents/Sawako.md` |
   | Summarizer | `~/Desktop/kon/agents/Nodoka.md` |

5. **Quality checks** — Cursor `subagentStop` auto-validates Task subagent output via `on_subagent_stop.py`. Manual backstop (pipe each agent's full output):

   | Agent | `teammate_role` |
   |-------|-----------------|
   | Azusa | `Azusa` |
   | Jun | `Jun` |
   | Mugi | `Mugi` |
   | Yui | `Yui` |
   | Mio | `Mio` |
   | Ritsu | `Ritsu` |
   | Sawako | `Sawako` |
   | Nodoka | `Nodoka` |
   | Design challenge | `Azusa-challenge` |
   | Design revise | `Mugi-revise` |

   ```bash
   echo '{"teammate_role":"Mio","teammate_output":"<output>"}' \
     | python3 ~/Desktop/kon/hooks/teammate_quality_check.py
   ```

6. After Ritsu passes, spawn **Nodoka** — follow `commands/summarize.md`.

7. Failure handling: `~/Desktop/kon/skills/failure-handling/SKILL.md`.

8. Narration (🌸 Ui): `~/Desktop/kon/skills/narration/SKILL.md`.

## Hard rule

**Never run `git commit` or `git push`.** Always present the commit message draft and wait for the user to run it.
