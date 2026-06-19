"""Resolve the user project workspace from Cursor hook stdin payloads."""

from __future__ import annotations

import os
from pathlib import Path

from _kon_paths import kon_root, read_last_workspace

_CURSOR_DIR = (Path.home() / ".cursor").resolve()


def is_workspace_like(path: str | None) -> bool:
    if not path or not isinstance(path, str):
        return False
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        return False
    if not resolved.is_dir():
        return False
    if resolved == _CURSOR_DIR or _CURSOR_DIR in resolved.parents:
        return False
    return True


def walk_to_git_root(path: Path) -> Path | None:
    try:
        candidate = path.expanduser().resolve()
    except OSError:
        return None
    for parent in [candidate, *candidate.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def project_from_attachments(data: dict) -> str | None:
    attachments = data.get("attachments") or []
    if not isinstance(attachments, list):
        return None
    kon_plugin_root = kon_root().resolve()
    for att in attachments:
        if not isinstance(att, dict):
            continue
        if att.get("type") == "rule":
            continue
        fp = att.get("file_path")
        if not isinstance(fp, str) or not fp.strip():
            continue
        root = walk_to_git_root(Path(fp.strip()))
        if root is None:
            continue
        if root == kon_plugin_root:
            continue
        if is_workspace_like(str(root)):
            return str(root)
    return None


def read_cwd_from_terminal_file(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for _ in range(15):
                line = fh.readline()
                if not line:
                    return None
                stripped = line.strip()
                if stripped.startswith("cwd:"):
                    return stripped[4:].strip()
                if stripped.startswith("---") and stripped != "---":
                    return None
    except OSError:
        return None
    return None


def project_from_cursor_terminals() -> str | None:
    projects_root = _CURSOR_DIR / "projects"
    if not projects_root.is_dir():
        return None
    best_mtime = 0.0
    best_cwd: str | None = None
    for project_dir in projects_root.iterdir():
        terminals_dir = project_dir / "terminals"
        if not terminals_dir.is_dir():
            continue
        for term_file in terminals_dir.iterdir():
            if not term_file.is_file():
                continue
            try:
                mtime = term_file.stat().st_mtime
            except OSError:
                continue
            if mtime <= best_mtime:
                continue
            cwd = read_cwd_from_terminal_file(term_file)
            if cwd and is_workspace_like(cwd):
                best_mtime = mtime
                best_cwd = cwd
    return best_cwd


def resolve_workspace(data: dict) -> tuple[str | None, str]:
    """Return ``(workspace_path, source)`` where ``source`` names the strategy used."""
    for key in ("cwd", "rootPath", "workspacePath", "workspace_path"):
        value = data.get(key)
        if isinstance(value, str) and is_workspace_like(value):
            return value.strip(), f"stdin.{key}"
    for key in ("workspace_roots", "workspaceRoots"):
        roots = data.get(key)
        if isinstance(roots, list) and roots:
            first = roots[0]
            if isinstance(first, str) and is_workspace_like(first):
                return first.strip(), f"stdin.{key}[0]"

    last = read_last_workspace()
    if is_workspace_like(last):
        return last, "last_workspace.json"

    attached = project_from_attachments(data)
    if attached:
        return attached, "attachments"

    terminal = project_from_cursor_terminals()
    if terminal:
        return terminal, "cursor_terminal"

    cwd = os.getcwd()
    if is_workspace_like(cwd):
        return cwd, "os.getcwd"

    return None, "unresolved"
