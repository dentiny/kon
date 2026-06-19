#!/usr/bin/env python3
"""kon shell guard: block git commit and git push without human approval.

Wired to Cursor ``beforeShellExecution`` (and compatible with ``preToolUse`` Shell).
Agents must draft the message and ask the user to run it manually.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit, read_hook_stdin, set_hook_event  # noqa: E402

_BLOCKED_SUBCOMMANDS = frozenset({"commit", "push"})

# Global git options that consume a separate argument (or ``--opt=value`` form).
_GIT_GLOBAL_OPTS_WITH_ARG = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--exec-path",
        "--html-path",
        "--man-path",
        "--info-path",
    }
)

_SHELL_SEGMENT_SPLIT = ["&&", "||", ";", "|"]


def _split_shell_segments(command: str) -> list[str]:
    segments = [command]
    for sep in _SHELL_SEGMENT_SPLIT:
        next_segments: list[str] = []
        for segment in segments:
            next_segments.extend(segment.split(sep))
        segments = next_segments
    return [segment.strip() for segment in segments if segment.strip()]


def _is_git_executable(token: str) -> bool:
    return Path(token).name.lower() == "git"


def _skip_git_global_options(tokens: list[str], index: int) -> int:
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            if name in _GIT_GLOBAL_OPTS_WITH_ARG:
                index += 1 if "=" in token else 2
                continue
            break
        if token.startswith("-") and len(token) > 1:
            if token in ("-C", "-c"):
                index += 2
                continue
            if token.startswith("-c") and len(token) > 2:
                index += 1
                continue
            index += 1
            continue
        break
    return index


def _segment_has_git_write(tokens: list[str]) -> bool:
    index = 0
    while index < len(tokens):
        if not _is_git_executable(tokens[index]):
            index += 1
            continue
        index += 1
        index = _skip_git_global_options(tokens, index)
        if index < len(tokens) and tokens[index].lower() in _BLOCKED_SUBCOMMANDS:
            return True
        index += 1
    return False


def is_git_write_blocked(command: str) -> bool:
    """Return True if *command* runs ``git commit`` or ``git push`` anywhere."""
    for segment in _split_shell_segments(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        if _segment_has_git_write(tokens):
            return True
    return False


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
    data = read_hook_stdin()
    set_hook_event(data.get("hook_event_name"))

    command = _shell_command(data)
    if not command:
        emit("approve", "")

    if is_git_write_blocked(command):
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
