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
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _kon_paths import (  # noqa: E402
    hook_log_path,
    kon_root,
)
from _orchestrator_model import extract_orchestrator_model  # noqa: E402
from _workspace import resolve_workspace  # noqa: E402

_KON_CMD = re.compile(r"/kon:([\w-]+)(?:\s+(.*))?", re.DOTALL)
_SKIP_COMMANDS = frozenset({"/kon:finish", "/kon:todo"})
_BEGIN_COMMAND = "/kon:begin"
_LOG_NAME = "init_kon_session"


def _log(message: str) -> None:
    """Best-effort append to ``~/.kon/logs/init_kon_session.log``."""
    try:
        path = hook_log_path(_LOG_NAME)
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] {message}\n")
    except Exception:
        pass


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


def _orchestrator_model_argv(data: dict) -> list[str]:
    snap = extract_orchestrator_model(data)
    if not snap:
        return []
    argv: list[str] = []
    model = snap.get("orchestrator_model")
    if model:
        argv += ["--orchestrator-model", model]
    model_id = snap.get("orchestrator_model_id")
    if model_id:
        argv += ["--orchestrator-model-id", model_id]
    params = snap.get("orchestrator_model_params")
    if params:
        argv += ["--orchestrator-model-params", json.dumps(params)]
    return argv


def _init_session(project: str, command: str, task: str, data: dict) -> tuple[str | None, str]:
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
        ]
        + _orchestrator_model_argv(data),
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

        workspace, source = resolve_workspace(data)
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

        sid, err = _init_session(workspace, command, task, data)
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
