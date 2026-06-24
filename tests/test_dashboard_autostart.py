"""Tests for dashboard auto-start helpers and hook."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"

sys.path.insert(0, str(HOOKS))
from _dashboard_autostart import (  # noqa: E402
    dashboard_auto_start_enabled,
    start_dashboard_if_needed,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_hook(script: str, payload: dict | None = None) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip())


class TestDashboardAutostart:
    def test_disabled_by_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KON_DASHBOARD_AUTO_START", "0")
        assert dashboard_auto_start_enabled({}) is False

    def test_start_spawns_when_port_free(self) -> None:
        port = _free_port()
        calls: list[list[str]] = []

        class FakePopen:
            def __init__(self, args, **kwargs):
                calls.append(list(args))

        result = start_dashboard_if_needed(ROOT, port=port, popen=FakePopen)
        assert result["started"] is True
        assert result["port"] == port
        assert calls
        assert str(port) in calls[0]

    def test_skips_when_port_in_use(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import _dashboard_autostart as mod

        monkeypatch.setattr(mod, "port_in_use", lambda _port: True)
        result = start_dashboard_if_needed(ROOT, port=9090, popen=MagicMock())
        assert result["started"] is False
        assert result["reason"] == "already_running"
        assert result["port"] == 9090

    def test_dashboard_exits_quietly_when_port_taken(self) -> None:
        port = _free_port()
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind(("0.0.0.0", port))
        holder.listen(1)
        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "dashboard.py"), "--port", str(port)],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            assert proc.returncode == 0
        finally:
            holder.close()

    def test_start_dashboard_hook_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        kon_home = tmp_path / "kon-home"
        kon_home.mkdir()
        kon_data = kon_home / ".kon"
        kon_data.mkdir()
        (kon_data / "config.json").write_text(
            json.dumps({"kon_root": str(ROOT), "dashboard_auto_start": False}),
            encoding="utf-8",
        )
        monkeypatch.setenv("HOME", str(kon_home))
        monkeypatch.delenv("KON_DATA_DIR", raising=False)
        monkeypatch.delenv("KON_DASHBOARD_AUTO_START", raising=False)

        result = _run_hook("start_dashboard.py")
        assert result["ok"] is True
        assert result["dashboard"]["reason"] == "disabled"

    def test_start_dashboard_hook(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import start_dashboard

        port = _free_port()
        seen: dict = {}

        def fake_start(kon_root: Path, *, port=None, popen=subprocess.Popen):
            seen["port"] = port
            seen["kon_root"] = kon_root
            return {"started": True, "port": port, "url": f"http://localhost:{port}"}

        monkeypatch.setattr(start_dashboard, "start_dashboard_if_needed", fake_start)
        monkeypatch.setattr(start_dashboard, "dashboard_auto_start_enabled", lambda _cfg: True)
        monkeypatch.setattr(start_dashboard, "dashboard_port", lambda _cfg: port)
        monkeypatch.setattr(start_dashboard, "kon_root", lambda: ROOT)
        monkeypatch.setattr(sys, "stdin", type("R", (), {"read": lambda self: "{}"})())

        from io import StringIO

        buf = StringIO()
        monkeypatch.setattr(sys, "stdout", buf)
        start_dashboard.main()
        result = json.loads(buf.getvalue().strip())
        assert result["ok"] is True
        assert result["dashboard"]["started"] is True
        assert seen["port"] == port
