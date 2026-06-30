"""Tests for kon_session.py lifecycle (supersede + ephemeral auto-complete)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import isolated_kon_env, load_session, run_kon_session


def test_supersede_closes_previous_waiting() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid1 = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "first", "--pending", "Yui"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid1, "--agent", "Yui", "--summary", "done"],
            env,
            project,
        )
        assert load_session(sessions, sid1)["status"] == "waiting"

        sid2 = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "second"],
            env,
            project,
        )
        assert load_session(sessions, sid1)["status"] == "completed"
        assert load_session(sessions, sid2)["status"] == "in_progress"


def test_begin_stays_open_after_agent() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "work on auth"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explored auth"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["status"] == "in_progress"
        assert data.get("mode") == "interactive"


def test_active_begin() -> None:
    tmp, project, env, _sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        active = run_kon_session(["active"], env, project)
        assert active == sid


@pytest.mark.parametrize(
    ("command", "task", "expected_pending"),
    [
        pytest.param(
            "/kon:debug",
            "dashboard undefined dots",
            ["Azusa", "Mugi", "User", "Yui", "Sawako", "Mio", "Nodoka"],
            id="debug",
        ),
        pytest.param(
            "/kon:team",
            "add email validation",
            ["Azusa", "Mugi", "User", "Yui", "Sawako", "Mio", "Nodoka"],
            id="team",
        ),
        pytest.param(
            "/kon:review-pr",
            "review pr for auth changes",
            ["Mio"],
            id="review-pr",
        ),
        pytest.param(
            "/kon:describe-issue",
            "summarize issue 42",
            ["Jun"],
            id="describe-issue",
        ),
        pytest.param(
            "/kon:understand-codebase",
            "hooks and session tracking",
            ["Azusa", "Jun"],
            id="understand-codebase",
        ),
    ],
)
def test_default_pending(command: str, task: str, expected_pending: list[str]) -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", command, "--task", task],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["command"] == command
        assert data["steps_pending"] == expected_pending
        assert data["status"] == "in_progress"


@pytest.mark.parametrize(
    ("command", "agent", "task"),
    [
        pytest.param("/kon:ask", "Azusa", "how does X work", id="ask"),
        pytest.param("/kon:research", "Jun", "pytest exit codes", id="research"),
        pytest.param("/kon:review", "Mio", "review diff", id="review"),
        pytest.param("/kon:review-pr", "Mio", "review pr", id="review-pr"),
        pytest.param("/kon:describe-issue", "Jun", "summarize issue", id="describe-issue"),
    ],
)
def test_ephemeral_auto_completes(command: str, agent: str, task: str) -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", command, "--task", task],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", agent, "--summary", "done"],
            env,
            project,
        )
        assert load_session(sessions, sid)["status"] == "completed"


def test_log_turn_appends_without_closing_begin() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        run_kon_session(
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
        data = load_session(sessions, sid)
        assert data["status"] == "in_progress"
        assert len(data["log"]) == 1
        assert data["log"][0]["agent"] == "User"


def test_begin_turns_added_per_user_log_turn() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        assert load_session(sessions, sid).get("turns") == []

        run_kon_session(
            ["log-turn", "--id", sid, "--agent", "User", "--summary", "how does auth work"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["turns"] == [{"n": 1, "summary": "how does auth work"}]

        run_kon_session(
            ["log-turn", "--id", sid, "--agent", "User", "--summary", "what commands exist"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert len(data["turns"]) == 2
        assert data["turns"][1] == {"n": 2, "summary": "what commands exist"}


def test_begin_turns_not_added_for_non_user_agents() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        run_kon_session(
            ["log-turn", "--id", sid, "--agent", "Azusa", "--summary", "explored codebase"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["turns"] == []
        assert len(data["log"]) == 1


def test_begin_init_includes_empty_turns() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "plan to start Q&A"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert "turns" in data
        assert data["turns"] == []
        assert data["mode"] == "interactive"


def test_init_refuses_during_active_begin() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        begin_sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        with pytest.raises(subprocess.CalledProcessError) as exc:
            run_kon_session(
                ["init", "--command", "/kon:team", "--task", "should not create"],
                env,
                project,
            )
        assert "refusing init" in exc.value.stderr
        assert load_session(sessions, begin_sid)["status"] == "in_progress"
        assert len(list(sessions.glob("*/session.json"))) == 1


def test_patch_usage_replaces_without_double_counting() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "patch usage"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explored"],
            env,
            project,
        )
        run_kon_session(
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
        run_kon_session(
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
        data = load_session(sessions, sid)
        assert data["log"][0]["usage"]["total_tokens"] == 300
        assert data["usage_totals"]["total_tokens"] == 300


def test_patch_usage_accumulates_across_agents() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "token tracking"],
            env,
            project,
        )
        for agent, inp, out in [("Azusa", 100, 200), ("Mugi", 50, 150)]:
            run_kon_session(
                ["complete-agent", "--id", sid, "--agent", agent, "--summary", "done"],
                env,
                project,
            )
            run_kon_session(
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
        totals = load_session(sessions, sid)["usage_totals"]
        assert totals["input_tokens"] == 150
        assert totals["output_tokens"] == 350
        assert totals["total_tokens"] == 500


def test_complete_agent_without_usage_omits_fields() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "no usage"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "done"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert "usage" not in data["log"][-1]
        assert "usage_totals" not in data


def test_complete_agent_with_inline_usage() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "inline usage"],
            env,
            project,
        )
        run_kon_session(
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
        data = load_session(sessions, sid)
        assert data["log"][0]["usage"]["total_tokens"] == 2000
        assert data["usage_totals"]["total_tokens"] == 2000


def test_complete_agent_dedupes_hook_logged_step() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "dedupe"],
            env,
            project,
        )
        run_kon_session(
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
        run_kon_session(
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
        data = load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert "orchestrator" in data["log"][0]["summary"]
        assert data["log"][0]["usage"]["total_tokens"] == 30


def test_complete_agent_dedupes_hook_without_usage() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "dedupe no usage"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Yui", "--summary", "hook summary"],
            env,
            project,
        )
        run_kon_session(
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
        data = load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert data["log"][0]["summary"] == "orchestrator summary"
        assert "usage" not in data["log"][0]
        assert data["steps_completed"] == ["Yui"]


def test_complete_agent_dedupe_merges_usage() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "dedupe merge usage"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Mio", "--summary", "hook summary"],
            env,
            project,
        )
        run_kon_session(
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
        data = load_session(sessions, sid)
        assert len(data["log"]) == 1
        assert data["log"][0]["usage"]["total_tokens"] == 100
        assert data["usage_totals"]["total_tokens"] == 100


def test_repeat_agent_appends_steps_completed() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "milestone loop"],
            env,
            project,
        )
        for summary in ("milestone 1", "milestone 2"):
            run_kon_session(
                ["start-agent", "--id", sid, "--agent", "Yui"],
                env,
                project,
            )
            run_kon_session(
                ["complete-agent", "--id", sid, "--agent", "Yui", "--summary", summary],
                env,
                project,
            )
        data = load_session(sessions, sid)
        assert data["steps_completed"] == ["Yui", "Yui"]
        assert len(data["log"]) == 2


def test_finish_closes_most_recent_open_session() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:begin", "--task", "interactive"],
            env,
            project,
        )
        closed = run_kon_session(["finish"], env, project)
        assert closed == sid
        data = load_session(sessions, sid)
        assert data["status"] == "completed"
        assert data["current_agent"] is None
        assert data["log"][-1]["agent"] == "User"
        assert data["log"][-1]["summary"] == "Session closed by user."


def test_finish_by_id() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "waiting pipeline", "--pending", "Yui"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Yui", "--summary", "done"],
            env,
            project,
        )
        assert load_session(sessions, sid)["status"] == "waiting"
        run_kon_session(["finish", "--id", sid, "--summary", "Done for today"], env, project)
        data = load_session(sessions, sid)
        assert data["status"] == "completed"
        assert data["log"][-1]["summary"] == "Done for today"


def test_finish_no_open_session_exits_nonzero() -> None:
    tmp, project, env, _sessions = isolated_kon_env()
    with tmp:
        with pytest.raises(subprocess.CalledProcessError) as exc:
            run_kon_session(["finish"], env, project)
        assert "no open session found" in exc.value.stderr


def test_finish_rejects_already_completed() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:ask", "--task", "how does X work"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Azusa", "--summary", "explained"],
            env,
            project,
        )
        assert load_session(sessions, sid)["status"] == "completed"
        with pytest.raises(subprocess.CalledProcessError) as exc:
            run_kon_session(["finish", "--id", sid], env, project)
        assert "not open" in exc.value.stderr


def test_wait_for_user_and_user_continued_plan_gate() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "milestone gates"],
            env,
            project,
        )
        run_kon_session(
            ["complete-agent", "--id", sid, "--agent", "Mugi", "--summary", "plan ready"],
            env,
            project,
        )
        run_kon_session(
            [
                "wait-for-user",
                "--id",
                sid,
                "--after",
                "plan",
                "--summary",
                "Plan ready — approve to start?",
            ],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["status"] == "waiting"
        assert data["steps_waiting"] == ["User"]
        assert data["checkpoint"]["after"] == "plan"
        assert data["current_agent"] is None

        run_kon_session(
            [
                "user-continued",
                "--id",
                sid,
                "--summary",
                "Approved plan",
            ],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["status"] == "in_progress"
        assert data["steps_waiting"] == []
        assert "checkpoint" not in data
        assert "User" in data["steps_completed"]
        assert "User" not in data["steps_pending"]
        assert data["log"][-1]["agent"] == "User"


def test_wait_for_user_after_milestone_gate() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "gate after each milestone"],
            env,
            project,
        )
        run_kon_session(
            [
                "wait-for-user",
                "--id",
                sid,
                "--after",
                "milestone",
                "--milestone",
                "2",
                "--summary",
                "Milestone 2 approved — proceed to milestone 3?",
            ],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["status"] == "waiting"
        assert data["checkpoint"]["after"] == "milestone"
        assert data["checkpoint"]["milestone"] == 2
        assert data["steps_waiting"] == ["User"]

        run_kon_session(
            ["user-continued", "--id", sid, "--summary", "Approved milestone 2"],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["status"] == "in_progress"
        assert "checkpoint" not in data
        assert "User" in data["steps_completed"]


def test_wait_for_user_milestone_requires_number() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "milestone gate validation"],
            env,
            project,
        )
        with pytest.raises(subprocess.CalledProcessError) as exc:
            run_kon_session(
                [
                    "wait-for-user",
                    "--id",
                    sid,
                    "--after",
                    "milestone",
                    "--summary",
                    "Missing milestone number",
                ],
                env,
                project,
            )
        assert "--milestone" in exc.value.stderr


def test_task_agent_set_get_clear() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "resume loop"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Mio",
                "--task-id",
                "abc-123-task",
            ],
            env,
            project,
        )
        data = load_session(sessions, sid)
        assert data["task_agents"]["impl-loop"]["Mio"] == "abc-123-task"
        assert (
            run_kon_session(["get-task-agent", "--id", sid, "--agent", "Mio"], env, project)
            == "abc-123-task"
        )
        assert (
            run_kon_session(["get-task-agent", "--id", sid, "--agent", "Yui"], env, project) == ""
        )
        run_kon_session(["clear-task-agents", "--id", sid], env, project)
        data = load_session(sessions, sid)
        assert "task_agents" not in data


def test_should_refresh_task_agents_keep_when_under_budget() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "context budget"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--task-id",
                "yui-task-1",
            ],
            env,
            project,
        )
        run_kon_session(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--summary",
                "m1 done",
                "--input-tokens",
                "10000",
                "--output-tokens",
                "5000",
            ],
            env,
            project,
        )
        verdict = run_kon_session(
            [
                "should-refresh-task-agents",
                "--id",
                sid,
                "--budget",
                "200000",
                "--threshold",
                "0.8",
            ],
            env,
            project,
        )
        assert verdict == "keep"
        assert load_session(sessions, sid)["task_agents"]["impl-loop"]["Yui"] == "yui-task-1"


def test_should_refresh_task_agents_refresh_when_over_threshold() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "context budget"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Mio",
                "--task-id",
                "mio-task-1",
            ],
            env,
            project,
        )
        run_kon_session(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Mio",
                "--summary",
                "review done",
                "--input-tokens",
                "150000",
                "--output-tokens",
                "10000",
            ],
            env,
            project,
        )
        verdict = run_kon_session(
            [
                "should-refresh-task-agents",
                "--id",
                sid,
                "--budget",
                "200000",
                "--threshold",
                "0.8",
            ],
            env,
            project,
        )
        assert verdict == "refresh"


def test_maybe_clear_task_agents_keeps_ids_under_budget() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "maybe clear"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Sawako",
                "--task-id",
                "sawako-1",
            ],
            env,
            project,
        )
        run_kon_session(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Sawako",
                "--summary",
                "cleaned",
                "--input-tokens",
                "1000",
                "--output-tokens",
                "500",
            ],
            env,
            project,
        )
        result = run_kon_session(
            ["maybe-clear-task-agents", "--id", sid, "--budget", "100000"],
            env,
            project,
        )
        assert result == "kept"
        assert load_session(sessions, sid)["task_agents"]["impl-loop"]["Sawako"] == "sawako-1"


def test_maybe_clear_task_agents_clears_when_over_budget() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "maybe clear"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--task-id",
                "yui-heavy",
            ],
            env,
            project,
        )
        run_kon_session(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--summary",
                "large context",
                "--input-tokens",
                "90000",
                "--output-tokens",
                "10000",
            ],
            env,
            project,
        )
        result = run_kon_session(
            [
                "maybe-clear-task-agents",
                "--id",
                sid,
                "--budget",
                "100000",
                "--threshold",
                "0.8",
            ],
            env,
            project,
        )
        assert result == "cleared"
        assert "task_agents" not in load_session(sessions, sid)


def test_should_refresh_keeps_when_context_window_unknown() -> None:
    """Without observed window or --budget, never refresh (fail-open on agent retention)."""
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "unknown window"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Mio",
                "--task-id",
                "mio-heavy",
            ],
            env,
            project,
        )
        run_kon_session(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Mio",
                "--summary",
                "large context",
                "--input-tokens",
                "150000",
                "--output-tokens",
                "10000",
            ],
            env,
            project,
        )
        verdict = run_kon_session(
            ["should-refresh-task-agents", "--id", sid],
            env,
            project,
        )
        assert verdict == "keep"


def test_should_refresh_uses_context_profile() -> None:
    tmp, project, env, sessions = isolated_kon_env()
    with tmp:
        data_dir = Path(env["KON_DATA_DIR"])
        data_dir.mkdir(parents=True, exist_ok=True)
        profile = data_dir / "context_profile.json"
        profile.write_text(
            json.dumps({"context_window_size": 100000, "source": "preCompact"}),
            encoding="utf-8",
        )
        sid = run_kon_session(
            ["init", "--command", "/kon:team", "--task", "profile window"],
            env,
            project,
        )
        run_kon_session(
            [
                "set-task-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--task-id",
                "yui-heavy",
            ],
            env,
            project,
        )
        run_kon_session(
            [
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--summary",
                "heavy",
                "--input-tokens",
                "85000",
                "--output-tokens",
                "5000",
            ],
            env,
            project,
        )
        session = load_session(sessions, sid)
        assert session["task_context"]["Yui"]["usage_percent"] == 90.0
        verdict = run_kon_session(
            [
                "should-refresh-task-agents",
                "--id",
                sid,
                "--threshold",
                "0.8",
            ],
            env,
            project,
        )
        assert verdict == "refresh"
