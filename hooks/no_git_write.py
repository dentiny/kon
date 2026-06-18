#!/usr/bin/env python3
"""kon PreToolUse hook: block git commit and git push without human approval.

Any Bash call containing `git commit` or `git push` is blocked.
Agents must draft the message and ask the user to run it manually.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit  # noqa: E402

_BLOCKED_PATTERN = re.compile(
    r"\bgit\s+commit\b|\bgit\s+push\b",
    re.IGNORECASE,
)


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit("approve", "no_git_write: invalid JSON input — skipping")

    tool = (data.get("tool_name") or "").strip()
    if tool != "Bash":
        emit("approve", "")

    command = (data.get("tool_input") or {}).get("command", "")
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
