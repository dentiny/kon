"""Shared I/O helpers for kon hooks.

Hooks emit JSON to stdout and exit 0. Output shape depends on the Cursor hook
event (when ``hook_event_name`` is set on stdin); manual orchestrator pipes
without an event keep the legacy ``{decision, reason, systemMessage}`` format.
"""

from __future__ import annotations

import json
import os
import sys
from typing import NoReturn

_current_event: str | None = None


def set_hook_event(name: str | None) -> None:
    global _current_event
    _current_event = name


def resolve_hook_cwd(data: dict) -> str:
    """Best-effort project root from Cursor hook stdin."""
    for key in ("cwd", "rootPath", "workspacePath", "workspace_path"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("workspace_roots", "workspaceRoots"):
        roots = data.get(key)
        if isinstance(roots, list) and roots:
            first = roots[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
    return os.getcwd()


def format_payload(decision: str, reason: str, event: str | None = None) -> dict:
    """Build hook stdout JSON for the given event (testable without exiting)."""
    hook_event = event if event is not None else _current_event
    if hook_event in ("beforeShellExecution", "preToolUse"):
        if decision == "block":
            return {
                "permission": "deny",
                "user_message": reason,
                "agent_message": reason,
            }
        return {"permission": "allow"}
    if hook_event in ("stop", "subagentStop"):
        if decision == "block" and reason.strip():
            return {"followup_message": reason}
        return {}
    return {"decision": decision, "reason": reason, "systemMessage": reason}


def emit(decision: str, reason: str) -> NoReturn:
    """Write the hook decision payload to stdout and exit 0."""
    payload = format_payload(decision, reason)
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.exit(0)


def read_hook_stdin() -> dict:
    """Read and parse JSON from stdin; emit approve + exit on parse error."""
    raw = sys.stdin.read()
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit("approve", "kon hook: invalid JSON input — skipping")
