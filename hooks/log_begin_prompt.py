#!/usr/bin/env python3
"""Auto-log user prompts into the active /kon:begin session.

Runs on ``beforeSubmitPrompt``. When an interactive begin session is open,
appends a User log line from the submitted prompt — no orchestrator CLI call
needed. Skips ``/kon:begin`` (task already on the card) and ``/kon:finish``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _begin_log import (  # noqa: E402
    append_session_log,
    find_active_begin,
    hook_log,
    last_log_matches,
    user_summary_from_prompt,
)
from _workspace import resolve_workspace  # noqa: E402


def main() -> None:
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            hook_log(f"invalid json on stdin: {exc}")
            print(json.dumps({"continue": True}))
            return

        prompt = str(data.get("prompt") or "")
        summary = user_summary_from_prompt(prompt)
        if summary is None:
            print(json.dumps({"continue": True}))
            return

        workspace, source = resolve_workspace(data)
        if workspace is None:
            hook_log(f"workspace=UNRESOLVED source={source} prompt_head={prompt[:80]!r}")
            print(json.dumps({"continue": True}))
            return

        found = find_active_begin(workspace)
        if found is None:
            print(json.dumps({"continue": True}))
            return

        _, session = found
        sid = session["id"]
        log = session.get("log") or []
        if last_log_matches(log, "User", summary):
            print(json.dumps({"continue": True}))
            return

        if append_session_log(workspace, sid, "User", summary):
            hook_log(f"logged User sid={sid} source={source} summary={summary[:60]!r}")

        print(json.dumps({"continue": True}))
    except Exception as exc:  # noqa: BLE001
        hook_log(f"unexpected error: {exc}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
