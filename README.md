# kon

K-On! Ho-kago Tea Time driven multi-agent dev workflow.
Five band members, five dev roles — explore, plan, implement, review, verify.

Each agent owns one step of the software development cycle:

| SDLC Step | Agent | Role |
|-----------|-------|------|
| 1. Understand & investigate | 🎸 Azusa | Reads the codebase, finds relevant files and conventions |
| 2. Planning | 🍰 Mugi | Writes a step-by-step plan with acceptance criteria |
| 3. Implementation | 🎶 Yui | Executes the plan, drives forward |
| 4. Code review | 📝 Mio | Strict 9-item checklist, default BLOCKED |
| 5. Testing | 🥁 Ritsu | Runs real tests, reports exit codes, no hedging |
| 6. Cleanup | 🧹 Sawako | Removes dead code, simplifies comments and docs, no behavior changes |
| 7. Session debrief | 📋 Nodoka | Writes a complete session summary — what changed, decisions made, next steps |

Narrated by 🌸 Ui.

> **Note on ordering:** Review (Mio) runs before Testing (Ritsu) so structural problems
> are caught before wasting a full test run. Use `/kon:team` to run them in parallel.

---

## Dashboard

Run a live session dashboard to see all active and past agent runs:

```bash
cd /path/to/your-project
python3 ~/Desktop/kon/scripts/dashboard.py --open   # http://localhost:9090
python3 ~/Desktop/kon/scripts/dashboard.py --dir /other/project --open
```

Each session card shows: status badge, task, agent pipeline dots (🟢 done / 🔵 running / 🟡 waiting / 🔴 failed / ⚫ pending), timestamp, and current agent.
**Click** to expand the step-by-step log. **✓** to close a session. **🗑** to delete it.
Auto-refreshes every 3 seconds. Filter by **All / Active / Past** tabs.

---

## YOLO mode

Append `--yolo` to any command to run fully autonomously:

```
kon go --yolo: add email validation to auth.py
kon team --yolo: refactor the payment module
```

The orchestrator auto-accepts plan defaults and silently retries failures.
Only stops to ask when the retry limit is hit, a decision has no default,
or scope expansion is required.

---

## Architecture

kon is split into two layers so it works across different AI harnesses without rewriting anything.

```
agents/*.md      ← agent personas (harness-agnostic markdown)
commands/*.md    ← workflow definitions (harness-agnostic markdown)
skills/*.md      ← shared process knowledge (harness-agnostic markdown)
hooks/*.py       ← quality checks (pure Python, any harness can shell out)

adapters/
  cursor/kon.mdc          ← Cursor integration (~30 lines)
  claude-code/            ← Claude Code plugin manifest + hook config
```

The content layer (agents / commands / skills) never changes per harness.
Each harness needs only a thin adapter that defines:
1. How the user triggers a workflow
2. How to pass agent file content to subagents
3. How to invoke the hook scripts (optional)

---

## Usage

### Cursor

Install the adapter as a global rule (applies to all your projects):

```bash
mkdir -p ~/.cursor/rules
cp ~/Desktop/kon/adapters/cursor/kon.mdc ~/.cursor/rules/kon.mdc
```

Or as a project rule (applies only to one project):

```bash
mkdir -p /path/to/your/project/.cursor/rules
cp ~/Desktop/kon/adapters/cursor/kon.mdc /path/to/your/project/.cursor/rules/kon.mdc
```

Then in Cursor chat:

```
kon go: add email validation to auth.py
kon quick: fix the typo in README line 42
kon ask: how does session tracking work?
kon team: refactor the payment module
```

> If you installed kon somewhere other than `~/Desktop/kon`, edit the path in `kon.mdc`.

### Claude Code

```bash
cd /path/to/your/project
claude --plugin-dir ~/Desktop/kon
```

Then use `/kon:go`, `/kon:team`, `/kon:quick`, `/kon:ask`.

### Codex CLI

Install as a global instruction (applies to all your projects):

```bash
cat ~/Desktop/kon/adapters/codex/AGENTS.md >> ~/.codex/AGENTS.md
```

Or as a project instruction (copy into your project's `AGENTS.md`):

```bash
cat ~/Desktop/kon/adapters/codex/AGENTS.md >> /path/to/your/project/AGENTS.md
```

Then in any Codex session:

```
kon go: add email validation to auth.py
kon quick: fix the typo in README line 42
kon ask: how does session tracking work?
```

> `AGENTS.md` is a universal standard — the same file format also works in Cursor,
> Amp, Jules (Google), and Gemini CLI.

### Other harnesses (future)

1. Create `adapters/<harness>/` with one config file using that harness's format.
2. The file needs three things:
   - A trigger (how the user invokes the workflow)
   - Which `agents/<name>.md` to pass as context for each step
   - Optional: shell out to `hooks/teammate_quality_check.py` for validation
3. No changes to `agents/`, `commands/`, `skills/`, or `hooks/`.

---

## Commands

| Command | What it does |
|---------|-------------|
| `kon go: <task>` | Full sequential pipeline: explore → plan → implement → review → verify → summarize |
| `kon team: <task>` | Same pipeline, review + verify run in parallel (~30% faster) |
| `kon quick: <task>` | Skip explore/plan, lightweight 4-item review |
| `kon ask: <question>` | Read-only Q&A — Azusa explores, **zero writes** (no code, no session files) |
| `kon gc` | Garbage collect — remove dead code, simplify comments/docs |
| `kon summarize` | Write a session summary (auto-runs at end of every command) |
| `kon finish` | Mark the current session as completed |

### YOLO mode

Append `--yolo` to any command to run fully autonomously:

```
kon go --yolo: <task>
```

Auto-accepts plan defaults, silently retries failures. Only stops for: retry limit hit,
a decision with no default, or scope expansion required.

### Session lifecycle

Sessions stay **open** after agents finish — they move to `waiting` (yellow) until you
explicitly close them. This gives you time to review changes before declaring done.

```
in_progress (blue) → waiting (yellow) → completed (green)
                          ↓
                       blocked (red)
```

Close a session by clicking **✓** in the dashboard, or by running `kon finish`.

---

## Requirements

- Python 3.10+ (for hooks)
- `git` (for repo detection and diff)
- `gh` CLI (optional, for PR workflows)

---

## Development setup

```bash
bash scripts/install_hooks.sh   # creates .venv, installs ruff, sets git hooks (one-time)
```

The pre-push hook runs `ruff format --check` using the project venv.
If any file would be reformatted, the push is blocked — run `ruff format .` to fix.
