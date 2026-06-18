# kon Multi-Agent Workflow

**Plugin root**: `~/Desktop/kon` — update this path if you installed kon elsewhere.

## Trigger

When the user writes `kon go: <task>`, `kon team: <task>`, `kon quick: <task>`,
or `kon gc` / `kon gc: <target>`, activate the kon multi-agent workflow.

## How to orchestrate

1. Read the matching command file for the full workflow spec:
   - `kon go` → `~/Desktop/kon/commands/go.md`
   - `kon team` → `~/Desktop/kon/commands/team.md`
   - `kon quick` → `~/Desktop/kon/commands/quick.md`
   - `kon gc` → `~/Desktop/kon/commands/gc.md`

2. Read `~/Desktop/kon/skills/teammate-flow/SKILL.md` for orchestration rules.

3. For each agent step, spawn a subagent. Include the agent file as the subagent's
   system context in the prompt:

   | Step | Agent file |
   |------|-----------|
   | Explorer | `~/Desktop/kon/agents/Azusa.md` |
   | Planner | `~/Desktop/kon/agents/Mugi.md` |
   | Implementer | `~/Desktop/kon/agents/Yui.md` |
   | Reviewer | `~/Desktop/kon/agents/Mio.md` + `~/Desktop/kon/skills/strict-review/SKILL.md` |
   | Verifier | `~/Desktop/kon/agents/Ritsu.md` |
   | Cleaner | `~/Desktop/kon/agents/Sawako.md` |

4. After Mio and Ritsu complete, validate their output:
   ```bash
   echo '{"teammate_role":"Mio","teammate_output":"<output>"}' \
     | python3 ~/Desktop/kon/hooks/teammate_quality_check.py
   ```

5. Failure handling: `~/Desktop/kon/skills/failure-handling/SKILL.md`.

6. Narration (🌸 Ui): `~/Desktop/kon/skills/narration/SKILL.md`.

## Hard rule

**Never run `git commit` or `git push`.** Always present the commit message draft and wait for the user to run it.
