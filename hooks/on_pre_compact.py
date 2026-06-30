#!/usr/bin/env python3
"""Record Cursor context window size from preCompact for Task agent budget checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _begin_log import find_active_begin, hook_log  # noqa: E402
from _context_profile import update_from_pre_compact  # noqa: E402
from _hook_io import emit, read_hook_stdin, resolve_hook_cwd  # noqa: E402


def _patch_active_session_context(project: str, profile: dict) -> None:
    window = profile.get("context_window_size")
    if not window:
        return
    found = find_active_begin(project)
    if found is None:
        return
    path, data = found
    data["context_window_size"] = int(window)
    usage_pct = profile.get("context_usage_percent")
    if usage_pct is not None:
        try:
            data["context_usage_percent"] = float(usage_pct)
        except (TypeError, ValueError):
            pass
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    hook_log(f"patched session sid={data.get('id')} context_window_size={window}")


def main() -> None:
    data = read_hook_stdin()
    profile = update_from_pre_compact(data)
    project = resolve_hook_cwd(data)
    _patch_active_session_context(project, profile)
    window = profile.get("context_window_size")
    emit("approve", f"recorded context_window_size={window}")


if __name__ == "__main__":
    main()
