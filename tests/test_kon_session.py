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


def test_debug_default_pending() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:debug", "--task", "dashboard undefined dots"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["command"] == "/kon:debug"
        assert data["steps_pending"] == ["Azusa", "Yui", "Mio", "Ritsu", "Nodoka"]
        assert data["status"] == "in_progress"


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


def test_begin_turns_added_per_user_log_turn() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        assert _load_session(sessions, sid).get("turns") == []

        _run(
            ["log-turn", "--id", sid, "--agent", "User", "--summary", "how does auth work"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["turns"] == [{"n": 1, "summary": "how does auth work"}]

        _run(
            ["log-turn", "--id", sid, "--agent", "User", "--summary", "what commands exist"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert len(data["turns"]) == 2
        assert data["turns"][1] == {"n": 2, "summary": "what commands exist"}


def test_begin_turns_not_added_for_non_user_agents() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        _run(
            ["log-turn", "--id", sid, "--agent", "Azusa", "--summary", "explored codebase"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["turns"] == []
        assert len(data["log"]) == 1


def test_begin_init_includes_empty_turns() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "plan to start Q&A"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert "turns" in data
        assert data["turns"] == []
        assert data["mode"] == "interactive"


def test_init_refuses_during_active_begin() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        begin_sid = _run(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        with pytest.raises(subprocess.CalledProcessError) as exc:
            _run(
                ["init", "--command", "/kon:go", "--task", "should not create"],
                env,
                project,
            )
        assert "refusing init" in exc.value.stderr
        assert _load_session(sessions, begin_sid)["status"] == "in_progress"
        assert len(list(sessions.glob("*.json"))) == 1
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:go", "--task", "patch usage"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explored"],
            env,
            project,
        )
        _run(
            [
                "patch-usage",
                "--id",
                sid,
                "--agent",
                "Azusa",
                "--input-tokens",
                "100",
                "--output-tokens",
                "200",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert data["log"][0]["usage"]["total_tokens"] == 300
        assert data["usage_totals"]["total_tokens"] == 300


def test_patch_usage_replaces_without_double_counting() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:go", "--task", "patch usage"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explored"],
            env,
            project,
        )
        _run(
            [
                "patch-usage",
                "--id",
                sid,
                "--agent",
                "Azusa",
                "--input-tokens",
                "10",
                "--output-tokens",
                "20",
            ],
            env,
            project,
        )
        _run(
            [
                "patch-usage",
                "--id",
                sid,
                "--agent",
                "Azusa",
                "--input-tokens",
                "100",
                "--output-tokens",
                "200",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["log"][0]["usage"]["total_tokens"] == 300
        assert data["usage_totals"]["total_tokens"] == 300


def test_patch_usage_accumulates_across_agents() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:go", "--task", "token tracking"],
            env,
            project,
        )
        for agent, inp, out in [("Azusa", 100, 200), ("Mugi", 50, 150)]:
            _run(
                ["complete-agent", "--id", sid, "--agent", agent, "--summary", "done"],
                env,
                project,
            )
            _run(
                [
                    "patch-usage",
                    "--id",
                    sid,
                    "--agent",
                    agent,
                    "--input-tokens",
                    str(inp),
                    "--output-tokens",
                    str(out),
                ],
                env,
                project,
            )
        totals = _load_session(sessions, sid)["usage_totals"]
        assert totals["input_tokens"] == 150
        assert totals["output_tokens"] == 350
        assert totals["total_tokens"] == 500


def test_complete_agent_without_usage_omits_fields() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:go", "--task", "no usage"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "done"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert "usage" not in data["log"][-1]
        assert "usage_totals" not in data
