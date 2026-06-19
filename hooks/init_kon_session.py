#!/usr/bin/env python3
"""Auto-create kon session JSON when the user submits a /kon:* slash command.

Dashboard and session-tracking rely on files under
``~/.kon/projects/<repo>/sessions/``. Orchestrators often skip the manual
``kon_session.py init`` step; this hook runs on ``beforeSubmitPrompt`` so
ongoing sessions appear immediately.

Workspace resolution is non-trivial because user-level Cursor hooks run with
cwd=``~/.cursor/`` and the ``beforeSubmitPrompt`` payload only contains
``prompt`` and ``attachments`` — no workspace fields. We resolve in priority
order:

  1. Explicit fields on stdin (future-proofing if Cursor adds them).
  2. ``~/.kon/last_workspace.json`` written by ``ensure_project_dir`` on
     ``sessionStart`` (the canonical signal).
  3. Walk up from any non-rule file attachment to a git root.
  4. Read ``cwd:`` from the most recently active terminal in
     ``~/.cursor/projects/<encoded>/terminals/*.txt``.

If none succeed (or the result is ``~/.cursor`` itself), we log and skip
rather than write to a wrong project. Fail-open: never blocks the prompt.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _kon_paths import (  # noqa: E402
    hook_log_path,
    kon_root,
    read_last_workspace,
)

_KON_CMD = re.compile(r"/kon:([\w-]+)(?:\s+(.*))?", re.DOTALL)
_SKIP_COMMANDS = frozenset({"/kon:finish"})
_BEGIN_COMMAND = "/kon:begin"
_LOG_NAME = "init_kon_session"
_CURSOR_DIR = (Path.home() / ".cursor").resolve()


def _log(message: str) -> None:
    """Best-effort append to ``~/.kon/logs/init_kon_session.log``."""
    try:
        path = hook_log_path(_LOG_NAME)
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] {message}\n")
    except OSError:
        pass


def _is_workspace_like(path: str | None) -> bool:
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


def _walk_to_git_root(path: Path) -> Path | None:
    try:
        candidate = path.expanduser().resolve()
    except OSError:
        return None
    for parent in [candidate, *candidate.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _project_from_attachments(data: dict) -> str | None:
    attachments = data.get("attachments") or []
    if not isinstance(attachments, list):
        return None
    kon_plugin_root = kon_root().resolve()
    for att in attachments:
        if not isinstance(att, dict):
            continue
        if att.get("type") == "rule":
            continue  # rule files come from the kon plugin, not the user workspace
        fp = att.get("file_path")
        if not isinstance(fp, str) or not fp.strip():
            continue
        root = _walk_to_git_root(Path(fp.strip()))
        if root is None:
            continue
        if root == kon_plugin_root:
            # An attachment from inside the kon clone tells us nothing about
            # which project the user is editing.
            continue
        if _is_workspace_like(str(root)):
            return str(root)
    return None


def _project_from_cursor_terminals() -> str | None:
    """Best-effort: read cwd from the most recently touched Cursor terminal file."""
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
            cwd = _read_cwd_from_terminal_file(term_file)
            if cwd and _is_workspace_like(cwd):
                best_mtime = mtime
                best_cwd = cwd
    return best_cwd


def _read_cwd_from_terminal_file(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for _ in range(15):  # header is the first ~10 lines
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


def _resolve_workspace(data: dict) -> tuple[str | None, str]:
    """Return ``(workspace_path, source)`` where ``source`` names the strategy used."""
    for key in ("cwd", "rootPath", "workspacePath", "workspace_path"):
        value = data.get(key)
        if isinstance(value, str) and _is_workspace_like(value):
            return value.strip(), f"stdin.{key}"
    for key in ("workspace_roots", "workspaceRoots"):
        roots = data.get(key)
        if isinstance(roots, list) and roots:
            first = roots[0]
            if isinstance(first, str) and _is_workspace_like(first):
                return first.strip(), f"stdin.{key}[0]"

    last = read_last_workspace()
    if _is_workspace_like(last):
        return last, "last_workspace.json"

    attached = _project_from_attachments(data)
    if attached:
        return attached, "attachments"

    terminal = _project_from_cursor_terminals()
    if terminal:
        return terminal, "cursor_terminal"

    cwd = os.getcwd()
    if _is_workspace_like(cwd):
        return cwd, "os.getcwd"

    return None, "unresolved"


def _parse_prompt(prompt: str) -> tuple[str, str] | None:
    match = _KON_CMD.search(prompt.strip())
    if not match:
        return None
    name = match.group(1)
    command = f"/kon:{name}"
    task = (match.group(2) or "").strip() or name.replace("-", " ")
    return command, task


def _kon_session_script() -> Path | None:
    script = kon_root() / "scripts" / "kon_session.py"
    return script if script.is_file() else None


def _active_begin_id(project: str) -> str | None:
    script = _kon_session_script()
    if script is None:
        return None
    proc = subprocess.run(
        [sys.executable, str(script), "--project", project, "active"],
        capture_output=True,
        text=True,
        check=False,
    )
    sid = proc.stdout.strip()
    return sid or None


def _init_session(project: str, command: str, task: str) -> tuple[str | None, str]:
    script = _kon_session_script()
    if script is None:
        return None, "kon_session.py not found"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--project",
            project,
            "init",
            "--command",
            command,
            "--task",
            task,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout).strip()
    sid = proc.stdout.strip()
    return (sid or None), ""


def main() -> None:
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            _log(f"invalid json on stdin: {exc}")
            print(json.dumps({"continue": True}))
            return

        prompt = str(data.get("prompt") or "")
        parsed = _parse_prompt(prompt)
        if parsed is None:
            print(json.dumps({"continue": True}))
            return

        command, task = parsed
        if command in _SKIP_COMMANDS:
            _log(f"skip command: {command}")
            print(json.dumps({"continue": True}))
            return

        workspace, source = _resolve_workspace(data)
        if workspace is None:
            _log(
                f"command={command} workspace=UNRESOLVED source={source} "
                f"prompt_head={prompt[:80]!r}"
            )
            print(json.dumps({"continue": True}))
            return

        if command != _BEGIN_COMMAND and _active_begin_id(workspace):
            _log(f"command={command} workspace={workspace} reuse begin session")
            print(json.dumps({"continue": True}))
            return

        sid, err = _init_session(workspace, command, task)
        if sid:
            _log(f"command={command} workspace={workspace} source={source} sid={sid}")
        else:
            _log(f"command={command} workspace={workspace} source={source} init_failed: {err}")

        print(json.dumps({"continue": True}))
    except Exception as exc:  # noqa: BLE001
        _log(f"unexpected error: {exc}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
