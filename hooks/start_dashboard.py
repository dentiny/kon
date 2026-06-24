#!/usr/bin/env python3
"""Start the kon dashboard on Cursor sessionStart if not already running.

Try to bind ``http://localhost:<port>`` (default 9090). If the server is
already up or the port is taken, tolerate it and exit 0 — never block or crash
Cursor. Does not open a browser tab.

Disable with ``KON_DASHBOARD_AUTO_START=0`` or ``dashboard_auto_start: false``
in ``~/.kon/config.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _dashboard_autostart import (  # noqa: E402
    _load_kon_config,
    dashboard_auto_start_enabled,
    dashboard_port,
    start_dashboard_if_needed,
)
from _kon_paths import kon_root  # noqa: E402


def main() -> None:
    try:
        sys.stdin.read()  # sessionStart payload — ignored; fail-open if malformed
        cfg = _load_kon_config()
        if not dashboard_auto_start_enabled(cfg):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "dashboard": {"started": False, "reason": "disabled"},
                    }
                )
            )
            return

        port = dashboard_port(cfg)
        result = start_dashboard_if_needed(kon_root(), port=port)
        print(json.dumps({"ok": True, "dashboard": result}))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
