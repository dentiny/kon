"""Shared I/O helpers for kon hooks.

Hooks emit JSON to stdout and exit 0. Output shape depends on the harness hook
event (Cursor camelCase or Claude Code PascalCase when ``hook_event_name`` is
set on stdin); manual orchestrator pipes without an event keep the legacy
``{decision, reason, systemMessage}`` format.
"""

from __future__ import annotations

import json
import os
import sys
from typing import NoReturn

_current_event: str | None = None

# Claude Code PascalCase → internal Cursor-style names used by hook logic.
_CLAUDE_EVENT_ALIASES: dict[str, str] = {
    "SessionStart": "sessionStart",
    "UserPromptSubmit": "beforeSubmitPrompt",
    "PreToolUse": "preToolUse",
    "SubagentStop": "subagentStop",
    "Stop": "stop",
    "PreCompact": "preCompact",
    "AfterAgentResponse": "afterAgentResponse",
}


def hook_event_name(data: dict) -> str | None:
    """Return hook event name from stdin payload (Cursor or Claude Code)."""
    for key in ("hook_event_name", "hookEventName"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def is_claude_code_event(event: str | None) -> bool:
    """True when *event* uses Claude Code's PascalCase hook names."""
    return bool(event and event[0].isupper())


def normalize_hook_event(event: str | None) -> str | None:
    """Map harness-specific event names to the internal Cursor-style set."""
    if not event:
        return None
    return _CLAUDE_EVENT_ALIASES.get(event, event)


def set_hook_event(name: str | None) -> None:
    global _current_event
    _current_event = name


def resolve_hook_cwd(data: dict) -> str:
    """Best-effort project root from hook stdin."""
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
    normalized = normalize_hook_event(hook_event)

    if is_claude_code_event(hook_event):
        if normalized == "preToolUse":
            if decision == "block":
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            return {}
        if normalized in ("stop", "subagentStop"):
            if decision == "block" and reason.strip():
                return {"decision": "block", "reason": reason}
            return {}
        if decision == "approve":
            return {}
        return {"decision": decision, "reason": reason, "systemMessage": reason}

    if normalized in ("beforeShellExecution", "preToolUse"):
        if decision == "block":
            return {
                "permission": "deny",
                "user_message": reason,
                "agent_message": reason,
            }
        return {"permission": "allow"}
    if normalized in ("stop", "subagentStop"):
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
