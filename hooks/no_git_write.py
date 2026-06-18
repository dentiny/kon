#!/usr/bin/env python3
"""kon shell guard: block git commit and git push without human approval.

Wired to Cursor ``beforeShellExecution`` (and compatible with ``preToolUse`` Shell).
Agents must draft the message and ask the user to run it manually.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit, set_hook_event  # noqa: E402

_BLOCKED_PATTERN = re.compile(
    r"\bgit\s+commit\b|\bgit\s+push\b",
    re.IGNORECASE,
)


def _shell_command(data: dict) -> str:
    command = data.get("command")
    if isinstance(command, str):
        return command
    tool = (data.get("tool_name") or "").strip()
    if tool in ("Bash", "Shell"):
        tool_input = data.get("tool_input") or {}
        if isinstance(tool_input, dict):
            inner = tool_input.get("command")
            if isinstance(inner, str):
                return inner
    return ""


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit("approve", "no_git_write: invalid JSON input — skipping")

    set_hook_event(data.get("hook_event_name"))

    command = _shell_command(data)
    if not command:
        emit("approve", "")

    if _BLOCKED_PATTERN.search(command):
        emit(
            "block",
            "git commit and git push require human approval. "
            "Draft the commit message and present it to the user — "
            "never run `git commit` or `git push` directly. "
            "The user will run the command themselves.",
        )

    emit("approve", "")


if __name__ == "__main__":
    main()
