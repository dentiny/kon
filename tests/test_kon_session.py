"""Tests for kon_session.py lifecycle (supersede + ephemeral auto-complete)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "kon_session.py"


def _run(args: list[str], env: dict, cwd: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=str(cwd),
    )
    return proc.stdout.strip()


def _load_session(sessions_dir: Path, sid: str) -> dict:
    return json.loads((sessions_dir / f"{sid}.json").read_text(encoding="utf-8"))


def _isolated_env() -> tuple[tempfile.TemporaryDirectory[str], Path, dict, Path]:
    tmp = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp.name)
    project = tmp_path / "repo"
    project.mkdir()
    env = {**os.environ, "KON_DATA_DIR": str(tmp_path / "kon-data")}
    sessions = tmp_path / "kon-data" / "projects" / "repo" / "sessions"
    return tmp, project, env, sessions


def test_supersede_closes_previous_waiting() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid1 = _run(
            ["init", "--command", "/kon:go", "--task", "first"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid1, "--agent", "Yui", "--summary", "done"],
            env,
            project,
        )
        assert _load_session(sessions, sid1)["status"] == "waiting"

        sid2 = _run(
            ["init", "--command", "/kon:go", "--task", "second"],
            env,
            project,
        )
        assert _load_session(sessions, sid1)["status"] == "completed"
        assert _load_session(sessions, sid2)["status"] == "in_progress"


def test_begin_stays_open_after_agent() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "work on auth"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explored auth"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["status"] == "in_progress"
        assert data.get("mode") == "interactive"


def test_active_begin() -> None:
    tmp, project, env, _sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        active = _run(["active"], env, project)
        assert active == sid


@pytest.mark.parametrize(
    ("command", "agent", "task"),
    [
        pytest.param("/kon:ask", "Azusa", "how does X work", id="ask"),
        pytest.param("/kon:research", "Jun", "pytest exit codes", id="research"),
        pytest.param("/kon:review", "Mio", "review diff", id="review"),
    ],
)
def test_ephemeral_auto_completes(command: str, agent: str, task: str) -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", command, "--task", task],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", agent, "--summary", "done"],
            env,
            project,
        )
        assert _load_session(sessions, sid)["status"] == "completed"


def test_log_turn_appends_without_closing_begin() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        _run(
            [
                "log-turn",
                "--id",
                sid,
                "--agent",
                "User",
                "--summary",
                "check auth flow",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["status"] == "in_progress"
        assert len(data["log"]) == 1
        assert data["log"][0]["agent"] == "User"
