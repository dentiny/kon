#!/usr/bin/env python3
"""Auto-log orchestrator replies into the active /kon:begin session.

Runs on ``afterAgentResponse``. Appends an Assistant log line from the
completed assistant message text.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _begin_log import (  # noqa: E402
    append_session_log,
    assistant_summary_from_text,
    find_active_begin,
    hook_log,
    last_log_matches,
)
from _workspace import resolve_workspace  # noqa: E402


def main() -> None:
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            hook_log(f"invalid json on stdin: {exc}")
            print("{}")
            return

        text = str(data.get("text") or data.get("last_assistant_message") or "")
        summary = assistant_summary_from_text(text)
        if summary is None:
            print("{}")
            return

        workspace, source = resolve_workspace(data)
        if workspace is None:
            hook_log(f"workspace=UNRESOLVED source={source}")
            print("{}")
            return

        found = find_active_begin(workspace)
        if found is None:
            print("{}")
            return

        _, session = found
        sid = session["id"]
        log = session.get("log") or []
        if last_log_matches(log, "Assistant", summary):
            print("{}")
            return

        if append_session_log(workspace, sid, "Assistant", summary):
            hook_log(f"logged Assistant sid={sid} source={source} summary={summary[:60]!r}")

        print("{}")
    except Exception as exc:  # noqa: BLE001
        hook_log(f"unexpected error: {exc}")
        print("{}")


if __name__ == "__main__":
    main()
