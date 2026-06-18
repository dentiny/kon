# kon Multi-Agent Workflow

**Plugin root**: `~/Desktop/kon` — update this path if you installed kon elsewhere.

## Trigger

When the user invokes a **slash command**:

- `/kon:go <task>`, `/kon:team <task>`, `/kon:design <task>`, `/kon:quick <task>`
- `/kon:ask <question>`
- `/kon:gc` or `/kon:gc <target>`
- `/kon:finish`, `/kon:summarize`

YOLO: `/kon:go --yolo <task>`.

## How to orchestrate

### `/kon:ask` — read-only repo, session tracked

For `/kon:ask`: create session JSON first (step 1), then read `commands/ask.md`. Spawn Azusa read-only — no code edits, no `.kon/plan.md`, no mutating shell. Update session after Azusa. Skip teammate-flow / Mio–Ritsu validation.

### All commands

1. **Session file (do this first)** — `python3 ~/Desktop/kon/scripts/kon_session.py init --command "/kon:go" --task "…"`. For ask: `--command "/kon:ask"`. See `adapters/cursor/kon.mdc` or `skills/session-tracking/SKILL.md`.

2. Read the matching command file:
   - `/kon:go` → `~/Desktop/kon/commands/go.md`
   - `/kon:team` → `~/Desktop/kon/commands/team.md`
   - `/kon:design` → `~/Desktop/kon/commands/design.md` + `~/Desktop/kon/skills/design-debate/SKILL.md`
   - `/kon:quick` → `~/Desktop/kon/commands/quick.md`
   - `/kon:ask` → `~/Desktop/kon/commands/ask.md`
   - `/kon:gc` → `~/Desktop/kon/commands/gc.md`

3. Read `~/Desktop/kon/skills/teammate-flow/SKILL.md` — **skip for `/kon:ask`**. For `/kon:design`, also read `~/Desktop/kon/skills/design-debate/SKILL.md`.

4. For each agent step, spawn a subagent. Include the agent file as the subagent's
   system context in the prompt:

   | Step | Agent file |
   |------|-----------|
   | Explorer | `~/Desktop/kon/agents/Azusa.md` |
   | Design challenger | `~/Desktop/kon/agents/Azusa-challenge.md` |
   | Planner | `~/Desktop/kon/agents/Mugi.md` |
   | Implementer | `~/Desktop/kon/agents/Yui.md` |
   | Reviewer | `~/Desktop/kon/agents/Mio.md` + `~/Desktop/kon/skills/strict-review/SKILL.md` |
   | Verifier | `~/Desktop/kon/agents/Ritsu.md` |
   | Cleaner | `~/Desktop/kon/agents/Sawako.md` |

5. After Mio and Ritsu complete, validate their output:
   ```bash
   echo '{"teammate_role":"Mio","teammate_output":"<output>"}' \
     | python3 ~/Desktop/kon/hooks/teammate_quality_check.py
   ```

6. Failure handling: `~/Desktop/kon/skills/failure-handling/SKILL.md`.

7. Narration (🌸 Ui): `~/Desktop/kon/skills/narration/SKILL.md`.

## Hard rule

**Never run `git commit` or `git push`.** Always present the commit message draft and wait for the user to run it.
