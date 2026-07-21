# Contributing to kon

Thanks for your interest in kon! This guide covers local setup, what to change where, and what we expect in pull requests.

## Getting started

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/dentiny/kon.git
   cd kon
   ```

2. Install Cursor integration (if you use Cursor):

   ```bash
   bash scripts/setup_cursor.sh
   ```

3. Install Claude Code integration (if you use Claude Code):

   ```bash
   bash scripts/setup_claude_code.sh
   ```

4. Set up the Python dev environment:

   ```bash
   bash scripts/install_hooks.sh          # creates .venv, installs ruff, sets git hooks
   # or:
   pip install -e ".[dev]"
   ```

5. Verify everything works:

   ```bash
   ruff check .
   ruff format --check .
   pytest -v
   ```

## Path configuration

kon resolves its plugin root (`KON_ROOT`) in this order:

1. `KON_ROOT` environment variable
2. `~/.kon/config.json` → `kon_root`
3. The kon clone containing `_kon_paths.py`
4. `~/Desktop/kon` (legacy dev fallback)

User data (sessions, config) lives under `KON_DATA_DIR` (default: `~/.kon`).

When contributing, prefer explicit `KON_ROOT` or `setup_cursor.sh` over relying on the legacy fallback.

## What lives where

| Directory | Purpose |
|-----------|---------|
| `agents/` | Agent personas (markdown) — harness-agnostic |
| `commands/` | Workflow definitions (`/kon:team`, etc.) |
| `skills/` | Shared process knowledge |
| `hooks/` | Machine enforcement (Python) — regressions here are costly |
| `scripts/` | CLI tools (dashboard, session tracking, setup) |
| `adapters/` | Harness-specific integration (Cursor, Codex, Claude Code) |
| `tests/` | pytest suite for hooks and scripts |

**Hooks vs skills:** enforcement that must block agent turns belongs in `hooks/`; narrative and convention belongs in `skills/`. See [`AGENTS.md`](AGENTS.md).

## Making changes

### Python (`hooks/`, `scripts/`)

- Match existing style; line length 100 (ruff).
- Add or update tests in `tests/` for behavior changes — especially hook logic (`tests/test_hooks.py`).
- Run `ruff check .`, `ruff format --check .`, and `pytest -v` before opening a PR.

### Markdown (`agents/`, `commands/`, `skills/`)

- Keep agent emoji prefixes consistent (see [`AGENTS.md`](AGENTS.md)).
- Link to skills with relative paths within the repo; use `https://github.com/dentiny/kon/blob/main/...` for stable external references.
- If you add a new hook event or command, update the matching adapter (`adapters/cursor/kon.mdc`, `adapters/claude-code/`, README) and run the relevant setup script where paths change.

### Cursor hooks

After adding or removing hook entries, contributors re-run:

```bash
bash scripts/setup_cursor.sh
```

Document any new hook in README under the hooks table.

### Claude Code plugin

After adding or removing hook entries or kon commands, regenerate stubs and refresh the install:

```bash
bash scripts/setup_claude_code.sh
```

## Pull requests

- **One logical change per PR** when possible — easier to review milestone-sized diffs.
- **Tests required** for Python behavior changes.
- **Describe user impact** in the PR title and body — what changes for someone running `/kon:*` commands or installing hooks.
- **Commit messages:** verb-first, user-impact subject (≤ 70 chars). See [`skills/commit-message/SKILL.md`](skills/commit-message/SKILL.md).

## AI agents in this repo

If you use kon (or another agent) while contributing:

- Agents must **not** run `git commit` or `git push` — humans commit after review.
- Agents may run read-only git commands and staging (`git add`).

## Questions

Open a [GitHub issue](https://github.com/dentiny/kon/issues/new/choose) for bugs or feature ideas — use the templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) when possible.
