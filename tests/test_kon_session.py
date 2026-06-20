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
    nested = sessions_dir / sid / "session.json"
    if nested.is_file():
        return json.loads(nested.read_text(encoding="utf-8"))
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
            ["init", "--command", "/kon:team", "--task", "first", "--pending", "Yui"],
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
            ["init", "--command", "/kon:team", "--task", "second"],
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
        assert data["steps_pending"] == ["Azusa", "Mugi", "User", "Yui", "Sawako", "Mio", "Nodoka"]
        assert data["status"] == "in_progress"


def test_team_default_pending() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "add email validation"],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["command"] == "/kon:team"
        assert data["steps_pending"] == [
            "Azusa",
            "Mugi",
            "User",
            "Yui",
            "Sawako",
            "Mio",
            "Nodoka",
        ]


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
                ["init", "--command", "/kon:team", "--task", "should not create"],
                env,
                project,
            )
        assert "refusing init" in exc.value.stderr
        assert _load_session(sessions, begin_sid)["status"] == "in_progress"
        assert len(list(sessions.glob("*/session.json"))) == 1
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "patch usage"],
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
            ["init", "--command", "/kon:team", "--task", "patch usage"],
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
            ["init", "--command", "/kon:team", "--task", "token tracking"],
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
            ["init", "--command", "/kon:team", "--task", "no usage"],
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


def test_complete_agent_with_inline_usage() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "inline usage"],
            env,
            project,
        )
        _run(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--summary",
                "milestone done",
                "--input-tokens",
                "500",
                "--output-tokens",
                "1500",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert data["log"][0]["usage"]["total_tokens"] == 2000
        assert data["usage_totals"]["total_tokens"] == 2000


def test_complete_agent_dedupes_hook_logged_step() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "dedupe"],
            env,
            project,
        )
        _run(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Mugi",
                "--summary",
                "hook summary",
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
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Mugi",
                "--summary",
                "orchestrator summary with more detail",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert "orchestrator" in data["log"][0]["summary"]
        assert data["log"][0]["usage"]["total_tokens"] == 30


def test_complete_agent_dedupes_hook_without_usage() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "dedupe no usage"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Yui", "--summary", "hook summary"],
            env,
            project,
        )
        _run(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--summary",
                "orchestrator summary",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert data["log"][0]["summary"] == "orchestrator summary"
        assert "usage" not in data["log"][0]
        assert data["steps_completed"] == ["Yui"]


def test_complete_agent_dedupe_merges_usage() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "dedupe merge usage"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Mio", "--summary", "hook summary"],
            env,
            project,
        )
        _run(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Mio",
                "--summary",
                "orchestrator summary",
                "--input-tokens",
                "40",
                "--output-tokens",
                "60",
            ],
            env,
            project,
        )
        data = _load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert data["log"][0]["usage"]["total_tokens"] == 100
        assert data["usage_totals"]["total_tokens"] == 100


def test_repeat_agent_appends_steps_completed() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "milestone loop"],
            env,
            project,
        )
        for summary in ("milestone 1", "milestone 2"):
            _run(
                ["start-agent", "--id", sid, "--agent", "Yui"],
                env,
                project,
            )
            _run(
                ["complete-agent", "--id", sid, "--agent", "Yui", "--summary", summary],
                env,
                project,
            )
        data = _load_session(sessions, sid)
        assert data["steps_completed"] == ["Yui", "Yui"]
        assert len(data["log"]) == 2


def test_finish_closes_most_recent_open_session() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        closed = _run(["finish"], env, project)
        assert closed == sid
        data = _load_session(sessions, sid)
        assert data["status"] == "completed"
        assert data["current_agent"] is None
        assert data["log"][-1]["agent"] == "User"
        assert data["log"][-1]["summary"] == "Session closed by user."


def test_finish_by_id() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:team", "--task", "waiting pipeline", "--pending", "Yui"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Yui", "--summary", "done"],
            env,
            project,
        )
        assert _load_session(sessions, sid)["status"] == "waiting"
        _run(["finish", "--id", sid, "--summary", "Done for today"], env, project)
        data = _load_session(sessions, sid)
        assert data["status"] == "completed"
        assert data["log"][-1]["summary"] == "Done for today"


def test_finish_no_open_session_exits_nonzero() -> None:
    tmp, project, env, _sessions = _isolated_env()
    with tmp:
        with pytest.raises(subprocess.CalledProcessError) as exc:
            _run(["finish"], env, project)
        assert "no open session found" in exc.value.stderr


def test_finish_rejects_already_completed() -> None:
    tmp, project, env, sessions = _isolated_env()
    with tmp:
        sid = _run(
            ["init", "--command", "/kon:ask", "--task", "how does X work"],
            env,
            project,
        )
        _run(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explained"],
            env,
            project,
        )
        assert _load_session(sessions, sid)["status"] == "completed"
        with pytest.raises(subprocess.CalledProcessError) as exc:
            _run(["finish", "--id", sid], env, project)
        assert "not open" in exc.value.stderr
