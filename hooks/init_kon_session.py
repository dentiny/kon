#!/usr/bin/env python3
"""Auto-create kon session JSON when the user submits a /kon:* slash command.

Dashboard and session-tracking rely on files under
``~/.kon/projects/<repo>/sessions/``. Orchestrators often skip the manual
``kon_session.py init`` step; this hook runs on ``beforeSubmitPrompt`` so
ongoing sessions appear immediately. Fail-open: never blocks the prompt.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import resolve_hook_cwd  # noqa: E402
from _kon_paths import kon_root  # noqa: E402

_KON_CMD = re.compile(r"/kon:(\w+)(?:\s+(.*))?", re.DOTALL)
_SKIP_COMMANDS = frozenset({"/kon:finish"})
# Plain follow-ups during /kon:begin reuse the open session — do not init again.
_IN_BEGIN_SKIP = frozenset(
    {"/kon:ask", "/kon:research", "/kon:review", "/kon:go", "/kon:quick", "/kon:design"}
)


def _parse_prompt(prompt: str) -> tuple[str, str] | None:
    match = _KON_CMD.search(prompt.strip())
    if not match:
        return None
    name = match.group(1)
    command = f"/kon:{name}"
    task = (match.group(2) or "").strip() or name.replace("-", " ")
    return command, task


def _active_begin_id(project: str) -> str | None:
    root = kon_root()
    script = root / "scripts" / "kon_session.py"
    if not script.is_file():
        return None
    proc = subprocess.run(
        [sys.executable, str(script), "--project", project, "active"],
        capture_output=True,
        text=True,
        check=False,
    )
    sid = proc.stdout.strip()
    return sid or None


def _init_session(project: str, command: str, task: str) -> str | None:
    root = kon_root()
    script = root / "scripts" / "kon_session.py"
    if not script.is_file():
        return None
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
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return None
    sid = proc.stdout.strip()
    return sid or None


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        prompt = str(data.get("prompt") or "")
        cwd = resolve_hook_cwd(data)

        parsed = _parse_prompt(prompt)
        if parsed is None:
            print(json.dumps({"continue": True}))
            return

        command, task = parsed
        if command in _SKIP_COMMANDS:
            print(json.dumps({"continue": True}))
            return

        if command in _IN_BEGIN_SKIP and _active_begin_id(cwd):
            print(json.dumps({"continue": True}))
            return

        sid = _init_session(cwd, command, task)
        if sid:
            print(json.dumps({"continue": True, "session_id": sid}), file=sys.stderr)
        print(json.dumps({"continue": True}))
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
