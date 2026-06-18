"""Shared path helpers for kon session and project-local artifacts.

Session history lives under ``~/.kon/projects/<repo-name>/sessions/`` (outside any
git repo). Project working files (plan, rubrics, retry logs) stay in
``<project>/.kon/``.

Override the data root with ``KON_DATA_DIR``.
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


def kon_data_dir() -> Path:
    """User-level kon data directory (default ``~/.kon``)."""
    raw = os.environ.get("KON_DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".kon").resolve()


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
    """Project-local working artifacts (plan, rubrics, retry logs)."""
    return resolve_project_path(project_dir) / ".kon"


def legacy_sessions_dir(project_dir: Path | str | None = None) -> Path:
    """Pre-migration session location inside a project repo."""
    return project_kon_dir(project_dir) / "sessions"


def legacy_flat_sessions_dir() -> Path:
    """Flat global sessions dir from an earlier layout."""
    return kon_data_dir() / "sessions"


def ensure_project_dir(project_dir: Path | str | None = None) -> Path:
    """Create ``~/.kon/projects/<repo-name>/`` and ``sessions/`` if missing."""
    base = project_data_dir(project_dir)
    sessions = base / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
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


def iter_sessions_dirs(project_dir: Path | str | None = None) -> list[Path]:
    """All session directories to scan (current repo, all projects, legacy)."""
    seen: set[Path] = set()
    dirs: list[Path] = []

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            dirs.append(resolved)

    if project_dir is not None:
        add(sessions_dir(project_dir))
        add(legacy_sessions_dir(project_dir))
    else:
        projects_root = kon_data_dir() / _PROJECTS_SUBDIR
        if projects_root.is_dir():
            for entry in sorted(projects_root.iterdir()):
                if entry.is_dir():
                    add(entry / "sessions")
        add(legacy_flat_sessions_dir())

    return dirs


def _cli() -> None:
    if len(sys.argv) < 2:
        print(
            "usage: _kon_paths.py "
            "<data|sessions|project-data|project-kon|legacy-sessions|repo-name|ensure>",
            file=sys.stderr,
        )
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "data":
        print(kon_data_dir())
    elif cmd == "sessions":
        print(sessions_dir())
    elif cmd == "project-data":
        print(project_data_dir())
    elif cmd == "project-kon":
        print(project_kon_dir())
    elif cmd == "legacy-sessions":
        print(legacy_sessions_dir())
    elif cmd == "repo-name":
        print(git_repo_name())
    elif cmd == "ensure":
        print(ensure_project_dir())
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
