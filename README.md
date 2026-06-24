# kon

K-On! Ho-kago Tea Time driven multi-agent dev workflow.
HTT band members plus extended roles — explore, research, plan, implement, cleanup, review, summarize.

Each agent owns one step of the software development cycle:

| SDLC Step | Agent | Role |
|-----------|-------|------|
| 1. Understand & investigate | 🎸 Azusa | Reads the codebase, finds relevant files and conventions |
| 1b. External lookup (optional) | 📚 Jun | Searches docs/web, writes `.kon/research.md` |
| 2. Planning | 🍰 Mugi | Writes a step-by-step plan with acceptance criteria and milestones |
| 3. Implementation | 🎶 Yui | Executes the plan milestone-by-milestone, drives forward |
| 4. Cleanup (per milestone) | 🧹 Sawako | Removes dead code, unused vars/imports, redundant comments after each milestone |
| 5. Code review (per milestone) | 📝 Mio | Strict 7-item golden checklist per milestone, default BLOCKED |
| 6. Manual testing | User | Runs tests after all milestones approved |
| 7. Session debrief | 📋 Nodoka | Writes a complete session summary — what changed, decisions made, next steps |

Narrated by 🌸 Ui.

> **Note on milestone-based workflow:** After plan approval, for each milestone:
> Yui implements → Sawako cleans up dead code/redundant comments → Mio reviews.
> This keeps code clean and reviews manageable with faster feedback.

---

## Dashboard

Run a live dashboard to see agent sessions and project todos:

```bash
python3 $KON_ROOT/scripts/dashboard.py --open   # http://localhost:9090
python3 $KON_ROOT/scripts/dashboard.py --project /path/to/repo --open  # one project only
```

**Auto-start:** With Cursor hooks installed, `start_dashboard.py` runs on **`sessionStart`**, tries to start the dashboard on port **9090**, and **silently continues** if that port is already in use (no crash, no duplicate tab). Disable with `KON_DASHBOARD_AUTO_START=0` or `"dashboard_auto_start": false` in `~/.kon/config.json`.

**Sessions** tab — active/past agent runs. **Todos** tab — open items from `.kon/todos.json` (mark done, reopen, delete). Add todos with `/kon:todo <task>`.

Project working files (plans, reviews, debug notes) and session metadata live together under
`~/.kon/projects/<repo-name>/sessions/<session-id>/` (override root with `KON_DATA_DIR`).
Project-local `.kon/todos.json` stays in the repo.

### Path configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `KON_ROOT` | Plugin clone (agents, commands, hooks, scripts) | `~/.kon/config.json` → clone path → `~/Desktop/kon` |
| `KON_DATA_DIR` | User data root (sessions, config) | `~/.kon` |

### New machine setup (Cursor)

On each machine you use Cursor on, run **once** from your kon clone:

```bash
git clone <your-kon-repo-url> ~/kon    # or any path you prefer
bash ~/kon/scripts/setup_cursor.sh
```

This single script:

1. Copies `adapters/cursor/kon.mdc` → `~/.cursor/rules/kon.mdc` (global rule — teaches `/kon:*` commands)
2. Merges kon hooks into `~/.cursor/hooks.json` (session tracking, git guard, subagent quality check)
3. Writes `~/.kon/config.json` with `kon_root` pointing at this clone

Optional — rule for one project only (instead of or in addition to global):

```bash
bash ~/kon/scripts/setup_cursor.sh --project /path/to/your/repo
```

**Requirements:** Python 3.10+, Cursor with hooks support.

**After moving or re-cloning kon**, re-run `setup_cursor.sh` — hook entries store absolute paths to this clone.

### Updating kon (pull + re-run setup)

kon splits into **live clone content** (agents, skills, hook `.py` logic) and **machine install** (Cursor rule + `hooks.json` entries). After `git pull`:

| What changed | Action |
|--------------|--------|
| Agent / skill / command markdown | `git pull` only — read from `$KON_ROOT` at runtime |
| Hook **script logic** (same filename) | `git pull` only — `hooks.json` already points at the file |
| **New or removed** Cursor hook | `git pull` then `bash ~/kon/scripts/setup_cursor.sh` |
| `adapters/cursor/kon.mdc` (commands, agent table) | `git pull` then `bash ~/kon/scripts/setup_cursor.sh` |
| Moved kon clone to a new path | `bash ~/kon/scripts/setup_cursor.sh` |

`setup_cursor.sh` is **safe to re-run** — it refreshes `kon.mdc`, rewrites `~/.kon/config.json`, replaces kon hook entries in `~/.cursor/hooks.json`, and removes deprecated kon hooks (e.g. old `verify_completion.py`, `repo_detect.py`).

**Typical upgrade on any machine:**

```bash
cd ~/kon && git pull
bash scripts/setup_cursor.sh
```

Codex-only users: `git pull` + re-append or merge `adapters/codex/AGENTS.md` into `~/.codex/AGENTS.md` if that file changed.

**What does not sync across machines automatically:**

| Stays on each machine | Sync yourself if needed |
|-----------------------|-------------------------|
| `~/.cursor/hooks.json`, `~/.cursor/rules/kon.mdc` | Re-run `setup_cursor.sh` |
| `~/.kon/config.json` (kon_root path) | Re-run `setup_cursor.sh` |
| `~/.kon/projects/<repo>/sessions/` (dashboard history) | Copy `~/.kon/` or set same `KON_DATA_DIR` |
| `<project>/.kon/` (plans, todos, debug notes) | Normal git / project files |

Resolve the root in shell or scripts:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
# or, from inside the clone:
export KON_ROOT="$(bash ~/kon/scripts/resolve_kon_root.sh)"
```

Override for a non-default clone location: `export KON_ROOT=/path/to/kon` (shell, Cursor user env, or CI).

Low-level install (hooks + config only, no rule copy): `bash $KON_ROOT/scripts/install_cursor_hooks.sh`

This merges into `~/.cursor/hooks.json`:

| Hook event | Script | Purpose |
|------------|--------|---------|
| `sessionStart` | `ensure_project_dir.py` | create `~/.kon/projects/<repo>/`, record current workspace in `~/.kon/last_workspace.json` |
| `sessionStart` | `start_dashboard.py` | start dashboard at `http://localhost:9090` if not already running |
| `beforeSubmitPrompt` | `init_kon_session.py` | auto-create session JSON when you send `/kon:*` (debug log at `~/.kon/logs/init_kon_session.log`) |
| `beforeSubmitPrompt` | `log_begin_prompt.py` | auto-log each user message into an open `/kon:begin` session |
| `afterAgentResponse` | `log_begin_response.py` | auto-log orchestrator replies into an open `/kon:begin` session |
| `beforeShellExecution` | `no_git_write.py` | block `git commit` / `git push` |
| `subagentStop` | `on_subagent_stop.py` | validate Task subagent output; log step + **estimated token usage** per agent |

**Token usage (estimated):** After each Task subagent finishes (Azusa, Mugi, Yui, Sawako, Mio, Jun, Nodoka, …), `on_subagent_stop.py` writes a session log row with estimated tokens from the subagent transcript (fallback: output text length). Dashboard shows per-step badges and session Σ total. The orchestrator's later `complete-agent` call dedupes — it won't double-count. **Not tracked:** main orchestrator chat (only Task subagents).

Each session card shows: status badge, task, project name (when viewing all), agent pipeline dots (🟢 done / 🔵 running / 🟡 waiting / 🔴 failed / ⚫ pending), checkpoint text when waiting for your approval (plan / all milestones done), timestamp, and current agent.
**Click** to expand the step-by-step log. **✓** to close a session. **🗑** to delete it.
Auto-refreshes every 3 seconds. Filter by **All / Active / Past** tabs.

---

## YOLO mode

Append `--yolo` to any command to run fully autonomously:

```
/kon:team --yolo add email validation to auth.py
/kon:team --yolo refactor the payment module
```

The orchestrator auto-accepts plan defaults and silently retries failures.
Only stops to ask when the retry limit is hit, a decision has no default,
or scope expansion is required.

---

## Architecture

kon is split into two layers so it works across different AI harnesses without rewriting anything.

```
agents/*.md              ← agent personas (harness-agnostic markdown)
commands/*.md            ← workflow definitions (harness-agnostic markdown)
skills/<name>/SKILL.md   ← shared process knowledge (harness-agnostic markdown)
hooks/*.py               ← quality checks (pure Python, any harness can shell out)

adapters/
  cursor/kon.mdc          ← Cursor integration (run setup_cursor.sh — do not copy hooks.json raw)
  codex/AGENTS.md         ← Codex CLI integration
```

Each harness needs only a thin adapter that defines:
1. How the user invokes a workflow (**slash commands**: `/kon:team`, `/kon:ask`, …)
2. How to pass agent file content to subagents
3. How to invoke the hook scripts (optional)

> **Command syntax:** `/kon:<name>` extension system commands. Session JSON stores the same form.

---

## Usage

### Cursor

**New machine — one command:**

```bash
git clone <your-kon-repo-url> ~/kon
bash ~/kon/scripts/setup_cursor.sh
```

Or step by step:

Install the adapter as a global rule (applies to all your projects):

```bash
mkdir -p ~/.cursor/rules
cp $KON_ROOT/adapters/cursor/kon.mdc ~/.cursor/rules/kon.mdc
bash $KON_ROOT/scripts/install_cursor_hooks.sh   # writes ~/.kon/config.json + hooks
```

Or as a project rule (applies only to one project):

```bash
bash $KON_ROOT/scripts/setup_cursor.sh --project /path/to/your/project
```

Re-run `setup_cursor.sh` after moving your kon clone (hooks use absolute paths).

```
/kon:begin
/kon:team add email validation to auth.py
/kon:quick fix the typo in README line 42
/kon:debug dashboard renderSession shows undefined for session dots
/kon:ask how does session tracking work?
/kon:research what Cursor hook events support followup_message?
/kon:review
/kon:review-pr
/kon:address-comments
/kon:describe-issue 123
/kon:todo add rate limiting to the API
/kon:design add rate limiting to the API
```

The Cursor rule resolves `$KON_ROOT` automatically (see **Path configuration** above). Re-run `setup_cursor.sh` after moving your clone.

### Codex CLI

Install as a global instruction (applies to all your projects):

```bash
cat $KON_ROOT/adapters/codex/AGENTS.md >> ~/.codex/AGENTS.md
```

Or as a project instruction (copy into your project's `AGENTS.md`):

```bash
cat $KON_ROOT/adapters/codex/AGENTS.md >> /path/to/your/project/AGENTS.md
```

Then in any Codex session:

```
/kon:begin
/kon:team add email validation to auth.py
/kon:quick fix the typo in README line 42
/kon:debug dashboard renderSession shows undefined for session dots
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
| `/kon:team <task>` | Full pipeline: explore → plan → milestone impl → cleanup → review → summarize |
| `/kon:design <task>` | Design-only: explore → plan → Azusa↔Mugi debate → user confirms (no code) |
| `/kon:quick <task>` | Skip explore/plan, lightweight 3-item review |
| `/kon:debug <bug>` | Bug investigation — root cause, fix proposals, user approves, then minimal fix |
| `/kon:research <question>` | External lookup — 📚 Jun searches docs/web, writes `.kon/research.md` |
| `/kon:review` | Code review only — 📝 Mio strict-review on uncommitted/staged diff |
| `/kon:review-pr` | Holistic PR review — 📝 Mio on diff + PR body + review comments + linked issues |
| `/kon:address-comments` | Triage PR review comments on current branch → route to quick/team and implement |
| `/kon:describe-issue <#>` | Summarize GitHub issue + all comments — 📚 Jun writes `issue-summary.md` |
| `/kon:todo <task>` | Add a project todo — stored in `.kon/todos.json`; manage in dashboard **Todos** tab |
| `/kon:ask <question>` | Read-only Q&A — 🎸 Azusa explores the repo, **no repo writes**; session tracked in `~/.kon/projects/` |
| `/kon:gc` | Garbage collect — remove dead code, simplify comments/docs |
| `/kon:summarize` | Write a session summary (auto-runs at end of every command) |
| `/kon:retro` | Re-run session retro (optional — runs automatically after pipeline commands) |
| `/kon:finish` | Mark the current session as completed |

### YOLO mode

Append `--yolo` to any command to run fully autonomously:

```
/kon:team --yolo <task>
```

Auto-accepts plan defaults, silently retries failures. Only stops for: retry limit hit,
a decision with no default, or scope expansion required.

### Session lifecycle

Pipeline commands (`/kon:team`, `/kon:debug`, …) stay **open** after agents finish — they move to `waiting` (yellow) until you close them with **✓** or `/kon:finish`.

**Interactive mode:** `/kon:begin` opens one session; follow-up messages need no `/kon:` prefix — the orchestrator routes by intent. Close with `/kon:finish`.

One-shot commands (`/kon:ask`, `/kon:research`, `/kon:review`) auto-complete when done. Starting a new `/kon:begin` or pipeline command supersedes other open sessions.

```
in_progress (blue) → waiting (yellow) → completed (green)
                          ↓
                       blocked (red)
```

Close a session by clicking **✓** in the dashboard, or by running `/kon:finish`.

---

## Memory (optional)

kon agents load memory at startup from two scopes (see `skills/memory-loading`):

| Scope | Path |
|-------|------|
| **Public** (cross-project) | `~/.kon/public/memory/` |
| **Repo** (this checkout) | `~/.kon/projects/<repo-name>/memory/` |

Both use a `MEMORY.md` index plus one file per entry. Override data root with `KON_DATA_DIR`.

Bootstrap once:

```bash
bash $KON_ROOT/scripts/bootstrap_memory.sh
# optional: bootstrap repo index for cwd
bash $KON_ROOT/scripts/bootstrap_memory.sh /path/to/repo
```

Agents load entries via `skills/memory-loading`; saves only via propose + retro (human confirm each write).

Legacy `~/.config/kon/memory/` is merged into public memory on first `ensure_project_dir`.

**Saving:**

| When | How |
|------|-----|
| During team/quick/debug | Mio/Yui `## Memory propose` → confirm → [`skills/memory-propose-confirm`](skills/memory-propose-confirm/SKILL.md) |
| End of pipeline | Retro after summarize → confirm → [`skills/session-retro`](skills/session-retro/SKILL.md) |

Say **skip retro** to close without memory proposals. To re-run retro later: `/kon:retro`.

**Browse entries:** `cat ~/.kon/public/memory/MEMORY.md` and `~/.kon/projects/<repo-name>/memory/MEMORY.md`.

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

---

## Acknowledgments

kon's multi-agent workflow — role-based agents, commands, skills, hooks, and strict review gating — draws heavily from [Maigo](https://github.com/Lee-W/maigo), Lee-W's MyGO!!!!! themed multi-agent dev workflow. kon adapts that model for Cursor and Codex with a K-On! cast and harness-specific adapters.
