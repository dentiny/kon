"""Start the kon dashboard HTTP server in the background if not already running.

Policy: always use the configured fixed port (default 9090). Try to start the
server; if the port is already taken or something is already listening, return
``already_running`` and never raise — the hook must not block or crash Cursor.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

DEFAULT_DASHBOARD_PORT = 9090


def _load_kon_config() -> dict:
    from _kon_paths import kon_config_path

    path = kon_config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def dashboard_auto_start_enabled(config: dict | None = None) -> bool:
    env = os.environ.get("KON_DASHBOARD_AUTO_START", "").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    if env in {"1", "true", "yes", "on"}:
        return True
    cfg = config if config is not None else _load_kon_config()
    raw = cfg.get("dashboard_auto_start", True)
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def dashboard_port(config: dict | None = None) -> int:
    env = os.environ.get("KON_DASHBOARD_PORT", "").strip()
    if env:
        return int(env)
    cfg = config if config is not None else _load_kon_config()
    raw = cfg.get("dashboard_port", DEFAULT_DASHBOARD_PORT)
    return int(raw)


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """True when the fixed port is already serving or bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        if probe.connect_ex((host, port)) == 0:
            return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bind_probe:
        bind_probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            bind_probe.bind((host, port))
            return False
        except OSError:
            return True


def start_dashboard_if_needed(
    kon_root: Path,
    *,
    port: int | None = None,
    popen: type[subprocess.Popen] = subprocess.Popen,
) -> dict:
    """Try to start ``scripts/dashboard.py`` on the fixed port.

    Returns ``started: False, reason: already_running`` when the port is taken —
    that is success, not an error. Never raises to callers.
    """
    port = port if port is not None else DEFAULT_DASHBOARD_PORT
    url = f"http://localhost:{port}"

    if port_in_use(port):
        return {"started": False, "reason": "already_running", "port": port, "url": url}

    script = kon_root / "scripts" / "dashboard.py"
    if not script.is_file():
        return {"started": False, "reason": "dashboard_script_missing", "port": port, "url": url}

    try:
        popen(
            [sys.executable, str(script), "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(kon_root),
        )
    except OSError:
        return {"started": False, "reason": "already_running", "port": port, "url": url}

    return {"started": True, "port": port, "url": url}
