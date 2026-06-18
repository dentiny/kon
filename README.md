# kon

K-On! Ho-kago Tea Time driven multi-agent dev workflow.
HTT band members plus extended roles — explore, research, plan, implement, review, verify, cleanup, summarize.

Each agent owns one step of the software development cycle:

| SDLC Step | Agent | Role |
|-----------|-------|------|
| 1. Understand & investigate | 🎸 Azusa | Reads the codebase, finds relevant files and conventions |
| 1b. External lookup (optional) | 📚 Jun | Searches docs/web, writes `.kon/research.md` |
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

Run a live dashboard to see agent sessions and project todos:

```bash
python3 ~/Desktop/kon/scripts/dashboard.py --open   # http://localhost:9090
python3 ~/Desktop/kon/scripts/dashboard.py --project /path/to/repo --open  # one project only
```

**Sessions** tab — active/past agent runs. **Todos** tab — open items from `.kon/todos.json` (mark done, reopen, delete). Add todos with `/kon:todo <task>`.

Session history lives in `~/.kon/projects/<repo-name>/sessions/` (override with `KON_DATA_DIR`). Project working files
(`plan.md`, rubrics) stay in `<project>/.kon/`.

Install kon Cursor hooks once (session dir + git guard + subagent quality check + stop test backstop):

```bash
bash ~/Desktop/kon/scripts/install_cursor_hooks.sh
```

This merges into `~/.cursor/hooks.json`:

| Hook event | Script | Purpose |
|------------|--------|---------|
| `sessionStart` | `ensure_project_dir.py` | create `~/.kon/projects/<repo>/` |
| `beforeShellExecution` | `no_git_write.py` | block `git commit` / `git push` |
| `subagentStop` | `on_subagent_stop.py` | validate Task subagent output (Mio/Yui/…) |
| `stop` | `verify_completion.py` | run tests when there are uncommitted changes |

Each session card shows: status badge, task, project name (when viewing all), agent pipeline dots (🟢 done / 🔵 running / 🟡 waiting / 🔴 failed / ⚫ pending), timestamp, and current agent.
**Click** to expand the step-by-step log. **✓** to close a session. **🗑** to delete it.
Auto-refreshes every 3 seconds. Filter by **All / Active / Past** tabs.

---

## YOLO mode

Append `--yolo` to any command to run fully autonomously:

```
/kon:go --yolo add email validation to auth.py
/kon:team --yolo refactor the payment module
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
  cursor/kon.mdc          ← Cursor integration
  codex/AGENTS.md         ← Codex CLI integration
```

Each harness needs only a thin adapter that defines:
1. How the user invokes a workflow (**slash commands**: `/kon:go`, `/kon:ask`, …)
2. How to pass agent file content to subagents
3. How to invoke the hook scripts (optional)

> **Command syntax:** `/kon:<name>` extension system commands. Session JSON stores the same form.

---

## Usage

### Cursor

Install the adapter as a global rule (applies to all your projects):

```bash
mkdir -p ~/.cursor/rules
cp ~/Desktop/kon/adapters/cursor/kon.mdc ~/.cursor/rules/kon.mdc
bash ~/Desktop/kon/scripts/install_cursor_hooks.sh   # creates ~/.kon/projects/<repo>/ on open
```

Or as a project rule (applies only to one project):

```bash
mkdir -p /path/to/your/project/.cursor/rules
cp ~/Desktop/kon/adapters/cursor/kon.mdc /path/to/your/project/.cursor/rules/kon.mdc
```

Then in Cursor chat (slash commands):

```
/kon:begin
/kon:go add email validation to auth.py
/kon:quick fix the typo in README line 42
/kon:ask how does session tracking work?
/kon:research what Cursor hook events support followup_message?
/kon:review
/kon:todo add rate limiting to the API
/kon:team refactor the payment module
/kon:design add rate limiting to the API
```

> If you installed kon somewhere other than `~/Desktop/kon`, edit the path in `kon.mdc`.

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
/kon:begin
/kon:go add email validation to auth.py
/kon:quick fix the typo in README line 42
/kon:ask how does session tracking work?
/kon:research what Cursor hook events support followup_message?
/kon:review
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
| `/kon:begin [goal]` | Interactive session — plain chat routed by intent; `/kon:finish` to close |
| `/kon:go <task>` | Full sequential pipeline: explore → plan → implement → review → verify → summarize |
| `/kon:team <task>` | Same pipeline, review + verify run in parallel (~30% faster) |
| `/kon:design <task>` | Design-only: explore → plan → Azusa↔Mugi debate → user confirms (no code) |
| `/kon:quick <task>` | Skip explore/plan, lightweight 4-item review |
| `/kon:research <question>` | External lookup — 📚 Jun searches docs/web, writes `.kon/research.md` |
| `/kon:review` | Code review only — 📝 Mio strict-review on uncommitted/staged diff |
| `/kon:todo <task>` | Add a project todo — stored in `.kon/todos.json`; manage in dashboard **Todos** tab |
| `/kon:ask <question>` | Read-only Q&A — 🎸 Azusa explores the repo, **no repo writes**; session tracked in `~/.kon/projects/` |
| `/kon:gc` | Garbage collect — remove dead code, simplify comments/docs |
| `/kon:summarize` | Write a session summary (auto-runs at end of every command) |
| `/kon:finish` | Mark the current session as completed |

### YOLO mode

Append `--yolo` to any command to run fully autonomously:

```
/kon:go --yolo <task>
```

Auto-accepts plan defaults, silently retries failures. Only stops for: retry limit hit,
a decision with no default, or scope expansion required.

### Session lifecycle

Pipeline commands (`/kon:go`, `/kon:team`, …) stay **open** after agents finish — they move to `waiting` (yellow) until you close them with **✓** or `/kon:finish`.

**Interactive mode:** `/kon:begin` opens one session; follow-up messages need no `/kon:` prefix — the orchestrator routes by intent. Close with `/kon:finish`.

One-shot commands (`/kon:ask`, `/kon:research`, `/kon:review`) auto-complete when done. Starting a new `/kon:begin` or pipeline command supersedes other open sessions.

```
in_progress (blue) → waiting (yellow) → completed (green)
                          ↓
                       blocked (red)
```

Close a session by clicking **✓** in the dashboard, or by running `/kon:finish`.

---

## Cross-project memory (optional)

kon agents can load preferences from `~/.config/kon/memory/` at startup (see `skills/memory-loading`).

Bootstrap once:

```bash
bash ~/Desktop/kon/scripts/bootstrap_memory.sh
```

This creates `~/.config/kon/memory/MEMORY.md`. Add lines like `- [Title](slug.md) — description`
and create matching `.md` files with frontmatter. Agents propose new entries during review via
`skills/memory-propose-confirm` — the orchestrator asks before writing.

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

`pre-commit` and `pre-push` run `ruff format` (autofix) automatically.
Pre-commit re-stages fixed files. Pre-push autofixes then blocks only if formatting
still fails or auto-fixed changes were not committed.
