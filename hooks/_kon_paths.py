"""Shared path helpers for kon session and project-local artifacts.

Session history lives under ``~/.kon/projects/<repo-name>/sessions/<session-id>/`` (outside any
git repo). Each session is one directory (`session.json`, `plan.md`, `review.md`, …).
Project-local todos stay in ``<project>/.kon/todos.json``.

Override paths with environment variables:

- ``KON_ROOT`` — kon plugin clone (agents, commands, hooks, scripts)
- ``KON_DATA_DIR`` — user data root (default ``~/.kon``)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

GIT_TIMEOUT_SEC = 3
_PROJECTS_SUBDIR = "projects"
_CONFIG_FILENAME = "config.json"
_LIB_SUBDIR = "lib"
_LIB_MODULE = "_kon_paths.py"
_DEFAULT_KON_ROOT = Path.home() / "Desktop" / "kon"
_LAST_WORKSPACE_FILENAME = "last_workspace.json"
_PUBLIC_SUBDIR = "public"
_MEMORY_SUBDIR = "memory"
_MEMORY_INDEX = "MEMORY.md"
_SKILLS_SUBDIR = "skills"
_SKILL_FILENAME = "SKILL.md"
_LOGS_SUBDIR = "logs"
_LEGACY_PUBLIC_MEMORY = Path.home() / ".config" / "kon" / "memory"


def kon_data_dir() -> Path:
    """User-level kon data directory (default ``~/.kon``)."""
    raw = os.environ.get("KON_DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".kon").resolve()


def kon_config_path() -> Path:
    return kon_data_dir() / _CONFIG_FILENAME


def bundled_paths_module() -> Path:
    """Installed copy of this module (written by ``install_cursor_hooks.sh``)."""
    return kon_data_dir() / _LIB_SUBDIR / _LIB_MODULE


def read_config_kon_root() -> Path | None:
    path = kon_config_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    raw = data.get("kon_root")
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def write_kon_config(kon_root: Path | str) -> Path:
    """Persist ``kon_root`` to ``~/.kon/config.json`` (merge with existing keys)."""
    root = Path(kon_root).expanduser().resolve()
    path = kon_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, str] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data.update({k: v for k, v in existing.items() if isinstance(v, str)})
        except (json.JSONDecodeError, OSError):
            pass
    data["kon_root"] = str(root)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _package_root_from_file() -> Path | None:
    """If this file lives inside a kon clone, return that clone root."""
    root = Path(__file__).resolve().parent.parent
    if (root / "agents").is_dir() and (root / "hooks").is_dir():
        return root
    return None


def kon_root() -> Path:
    """Resolve the kon plugin root directory.

    Order: ``KON_ROOT`` env → ``~/.kon/config.json`` → kon clone containing this
    file → ``~/Desktop/kon`` (legacy default).
    """
    raw = os.environ.get("KON_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    configured = read_config_kon_root()
    if configured is not None:
        return configured
    package = _package_root_from_file()
    if package is not None:
        return package
    return _DEFAULT_KON_ROOT.resolve()


def install_bundled_paths_module(source: Path | None = None) -> Path:
    """Copy ``_kon_paths.py`` to ``~/.kon/lib/`` for orchestrators without a clone path."""
    src = (source or Path(__file__).resolve()).expanduser().resolve()
    dest = bundled_paths_module()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def resolve_project_path(project_dir: Path | str | None = None) -> Path:
    """Absolute path to the project the orchestrator is running in."""
    return Path(project_dir).resolve() if project_dir else Path.cwd().resolve()


def _sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-")
    return cleaned or "project"


def git_repo_name(project_dir: Path | str | None = None) -> str:
    """Repo directory name from git toplevel, else cwd basename."""
    cwd = str(resolve_project_path(project_dir))
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            timeout=GIT_TIMEOUT_SEC,
            check=False,
        )
        if result.returncode == 0:
            root = Path(result.stdout.decode("utf-8", errors="replace").strip())
            if root.name:
                return _sanitize_name(root.name)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return _sanitize_name(resolve_project_path(project_dir).name)


def project_data_dir(project_dir: Path | str | None = None) -> Path:
    """Per-repo kon data directory: ``~/.kon/projects/<repo-name>/``."""
    return kon_data_dir() / _PROJECTS_SUBDIR / git_repo_name(project_dir)


def sessions_dir(project_dir: Path | str | None = None) -> Path:
    """Session history for the current repo."""
    return project_data_dir(project_dir) / "sessions"


def project_kon_dir(project_dir: Path | str | None = None) -> Path:
    """Project-local working artifacts (plan, rubrics, retry logs, test config)."""
    return resolve_project_path(project_dir) / ".kon"


def ensure_project_dir(project_dir: Path | str | None = None) -> Path:
    """Create ``~/.kon/projects/<repo-name>/``, ``sessions/``, and ``memory/`` if missing."""
    base = project_data_dir(project_dir)
    sessions = base / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    ensure_project_memory_dir(project_dir)
    ensure_public_memory_dir()
    meta = base / "meta.json"
    project_path = str(resolve_project_path(project_dir))
    if meta.is_file():
        try:
            existing = json.loads(meta.read_text(encoding="utf-8"))
            if existing.get("project_path") == project_path:
                return base
        except (json.JSONDecodeError, OSError):
            pass
    meta.write_text(
        json.dumps(
            {
                "repo_name": git_repo_name(project_dir),
                "project_path": project_path,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return base


def ensure_sessions_dir(project_dir: Path | str | None = None) -> Path:
    """Create the repo's sessions directory if needed; return its path."""
    ensure_project_dir(project_dir)
    return sessions_dir(project_dir)


def last_workspace_path() -> Path:
    """Path to the file that records the most recently active workspace."""
    return kon_data_dir() / _LAST_WORKSPACE_FILENAME


def write_last_workspace(project_path: Path | str) -> Path:
    """Persist the active workspace so user-level hooks can recover it.

    User-level Cursor hooks run with cwd=``~/.cursor/`` and the
    ``beforeSubmitPrompt`` payload omits workspace fields, so hooks that fire
    later in the lifecycle need a side channel. ``ensure_project_dir`` (which
    runs on ``sessionStart`` with the real workspace) writes this file; other
    hooks read it.
    """
    project = Path(project_path).expanduser().resolve()
    target = last_workspace_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_path": str(project),
        "repo_name": git_repo_name(project),
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def read_last_workspace() -> str | None:
    """Return the persisted workspace path if still on disk, else ``None``."""
    path = last_workspace_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    project = data.get("project_path") if isinstance(data, dict) else None
    if not isinstance(project, str) or not project.strip():
        return None
    if not Path(project).is_dir():
        return None
    return project.strip()


def public_memory_dir() -> Path:
    """Cross-project memory: ``~/.kon/public/memory/``."""
    return kon_data_dir() / _PUBLIC_SUBDIR / _MEMORY_SUBDIR


def project_memory_dir(project_dir: Path | str | None = None) -> Path:
    """Per-repo memory: ``~/.kon/projects/<repo-name>/memory/``."""
    return project_data_dir(project_dir) / _MEMORY_SUBDIR


def project_skills_dir(project_dir: Path | str | None = None) -> Path:
    """Per-repo skills directory: ``~/.kon/projects/<repo-name>/skills/``."""
    return project_data_dir(project_dir) / _SKILLS_SUBDIR


def iter_project_skill_paths(project_dir: Path | str | None = None) -> list[Path]:
    """All ``SKILL.md`` entry points under ``~/.kon/projects/<repo-name>/skills/*/``.

    Each named subdirectory is one skill. Returns paths sorted by skill name.
    Returns an empty list when the directory does not exist or has no skills.
    """
    skills = project_skills_dir(project_dir)
    if not skills.is_dir():
        return []
    return sorted(p for p in skills.glob("*/SKILL.md") if p.is_file())


def _memory_index_body(scope_label: str) -> str:
    return f"""# kon memory index ({scope_label})

Preferences and conventions loaded by agents at startup via `skills/memory-loading`.

Add entries below (one per line):

- [Title](slug.md) — one-line description

Entry files live in this directory with YAML frontmatter (`name`, `description`, `type`).
Types: `user`, `project`, `feedback`, `reference`.
"""


def ensure_memory_dir(memory_dir: Path, scope_label: str) -> Path:
    """Create a memory directory and empty ``MEMORY.md`` index if missing."""
    memory_dir.mkdir(parents=True, exist_ok=True)
    index = memory_dir / _MEMORY_INDEX
    if not index.is_file():
        index.write_text(_memory_index_body(scope_label), encoding="utf-8")
    return memory_dir


def ensure_public_memory_dir() -> Path:
    """Create ``~/.kon/public/memory/`` and index; migrate legacy ``~/.config/kon/memory/`` once."""
    target = ensure_memory_dir(public_memory_dir(), "public")
    legacy = _LEGACY_PUBLIC_MEMORY
    legacy_index = legacy / _MEMORY_INDEX
    target_index = target / _MEMORY_INDEX
    if legacy.is_dir() and legacy_index.is_file() and target_index.is_file():
        try:
            legacy_lines = {
                line.strip()
                for line in legacy_index.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith("- [")
            }
            target_text = target_index.read_text(encoding="utf-8")
            target_lines = {
                line.strip() for line in target_text.splitlines() if line.strip().startswith("- [")
            }
            new_lines = sorted(legacy_lines - target_lines)
            if new_lines:
                merged = target_text.rstrip() + "\n\n" + "\n".join(new_lines) + "\n"
                target_index.write_text(merged, encoding="utf-8")
            for path in legacy.glob("*.md"):
                if path.name == _MEMORY_INDEX:
                    continue
                dest = target / path.name
                if not dest.exists():
                    dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    return target


def ensure_project_memory_dir(project_dir: Path | str | None = None) -> Path:
    """Create ``~/.kon/projects/<repo>/memory/`` and index if missing."""
    repo_name = git_repo_name(project_dir)
    return ensure_memory_dir(project_memory_dir(project_dir), f"repo:{repo_name}")


def hook_log_path(name: str) -> Path:
    """Path to a hook's debug log under ``~/.kon/logs/``."""
    logs_dir = kon_data_dir() / _LOGS_SUBDIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip("-") or "hook"
    return logs_dir / f"{safe}.log"


def iter_sessions_dirs(project_dir: Path | str | None = None) -> list[Path]:
    """Session directories to scan — one repo or all projects under ~/.kon/projects/."""
    if project_dir is not None:
        return [sessions_dir(project_dir).resolve()]

    seen: set[Path] = set()
    dirs: list[Path] = []
    projects_root = kon_data_dir() / _PROJECTS_SUBDIR
    if projects_root.is_dir():
        for entry in sorted(projects_root.iterdir()):
            if entry.is_dir():
                path = (entry / "sessions").resolve()
                if path not in seen:
                    seen.add(path)
                    dirs.append(path)
    return dirs


def _cli() -> None:
    if len(sys.argv) < 2:
        print(
            "usage: _kon_paths.py "
            "<root|data|sessions|project-data|project-kon|public-memory|project-memory|"
            "project-skills-dir|project-skill-files|repo-name|ensure|write-config>",
            file=sys.stderr,
        )
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "root":
        print(kon_root())
    elif cmd == "write-config":
        if len(sys.argv) < 3:
            print("usage: _kon_paths.py write-config <kon_root>", file=sys.stderr)
            sys.exit(1)
        print(write_kon_config(sys.argv[2]))
    elif cmd == "data":
        print(kon_data_dir())
    elif cmd == "sessions":
        print(sessions_dir())
    elif cmd == "project-data":
        print(project_data_dir())
    elif cmd == "project-kon":
        print(project_kon_dir())
    elif cmd == "public-memory":
        print(ensure_public_memory_dir())
    elif cmd == "project-memory":
        print(ensure_project_memory_dir())
    elif cmd == "project-skills-dir":
        print(project_skills_dir())
    elif cmd == "project-skill-files":
        for path in iter_project_skill_paths():
            print(path)
    elif cmd == "repo-name":
        print(git_repo_name())
    elif cmd == "ensure":
        print(ensure_project_dir())
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
