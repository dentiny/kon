#!/usr/bin/env python3
"""Ensure ~/.kon/projects/<repo-name>/ exists for the current workspace.

Runs on Cursor sessionStart (and can be invoked manually). Fail-open: never
blocks the session from starting.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _kon_paths import ensure_project_dir  # noqa: E402


def _resolve_cwd(data: dict) -> str:
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


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        cwd = _resolve_cwd(data)
        path = ensure_project_dir(cwd)
        print(json.dumps({"ok": True, "project_data_dir": str(path)}))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(0)  # fail-open for sessionStart


if __name__ == "__main__":
    main()
