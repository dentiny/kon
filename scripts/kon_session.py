#!/usr/bin/env python3
"""kon session file CLI — reliable create/update for orchestrators."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from _kon_paths import iter_sessions_dirs, resolve_project_path  # noqa: E402
from _session_paths import (  # noqa: E402
    ensure_session_dir,
    iter_session_json_paths,
    resolve_session_json,
    session_artifact_path,
    session_dir,
    session_json_path,
)
from _token_estimate import SOURCE as USAGE_SOURCE  # noqa: E402

_BEGIN_COMMAND = "/kon:begin"
_TASK_AGENT_SCOPE_DEFAULT = "impl-loop"
_IMPL_LOOP_AGENTS = frozenset({"Yui", "Sawako", "Mio"})

# One-shot commands: auto-complete when the sole agent finishes (no dashboard clutter).
_EPHEMERAL_COMMANDS = frozenset(
    {
        "/kon:ask",
        "/kon:hunt",
        "/kon:research",
        "/kon:review",
        "/kon:review-pr",
        "/kon:describe-issue",
    }
)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _ts() -> str:
    """Current UTC time as ISO-8601 string."""
    return _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(task: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", task.lower())[:40].strip("-") or "task"


def _session_path(session_id: str, project: str | None) -> Path | None:
    return resolve_session_json(project, session_id)


def _load(session_id: str, project: str | None) -> tuple[Path, dict]:
    path = _session_path(session_id, project)
    if path is None:
        raise SystemExit(f"session not found: {session_id}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_command(command: str) -> str:
    """Require slash form: /kon:team, /kon:ask, …"""
    c = command.strip()
    if not c.startswith("/kon:"):
        raise SystemExit(f'command must be /kon:<name> (e.g. "/kon:team"), got: {command!r}')
    return c


def _default_pending(command: str) -> list[str]:
    c = _normalize_command(command)
    if c == "/kon:ask":
        return ["Azusa"]
    if c == "/kon:hunt":
        return ["Azusa"]
    if c == "/kon:research":
        return ["Jun"]
    if c == "/kon:review":
        return ["Mio"]
    if c == "/kon:review-pr":
        return ["Mio"]
    if c == "/kon:describe-issue":
        return ["Jun"]
    if c == "/kon:begin":
        return []
    if c == "/kon:design":
        return ["Azusa", "Mugi", "User"]
    if c == "/kon:team":
        return ["Azusa", "Mugi", "User", "Yui", "Sawako", "Mio", "Nodoka"]
    if c == "/kon:debug":
        return ["Azusa", "Mugi", "User", "Yui", "Sawako", "Mio", "Nodoka"]
    return []


def iter_session_files(
    project: str | None,
    *,
    status: frozenset[str] | None = None,
    command: str | None = None,
    exclude_sid: str | None = None,
) -> Iterator[tuple[Path, dict]]:
    """Yield (path, data) for every valid session matching the filters."""
    project_path = str(resolve_project_path(project))
    for directory in iter_sessions_dirs(project):
        for session_id, path in iter_session_json_paths(directory):
            if exclude_sid and session_id == exclude_sid:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("project_path") != project_path:
                continue
            if status is not None and data.get("status") not in status:
                continue
            if command is not None and data.get("command") != command:
                continue
            yield path, data


def _find_open_session(
    project: str | None,
    *,
    command: str | None = None,
) -> tuple[Path, dict] | None:
    """Most recent open session for this project (optionally filtered by command)."""
    best: tuple[Path, dict] | None = None
    best_key = ""
    for path, data in iter_session_files(
        project, status=frozenset({"in_progress", "waiting"}), command=command
    ):
        key = data.get("started_at") or data.get("id") or ""
        if key >= best_key:
            best_key = key
            best = (path, data)
    return best


def _find_active_begin(project: str | None) -> tuple[Path, dict] | None:
    """Most recent open /kon:begin session for this project."""
    return _find_open_session(project, command=_BEGIN_COMMAND)


def _terminal_status_when_agents_done(command: str) -> str:
    if command == _BEGIN_COMMAND:
        return "in_progress"
    if command in _EPHEMERAL_COMMANDS:
        return "completed"
    return "waiting"


def _supersede_open_sessions(project: str | None, new_sid: str) -> None:
    """Close other in_progress/waiting sessions for this project when a new run starts."""
    ts = _ts()
    for path, data in iter_session_files(
        project,
        status=frozenset({"in_progress", "waiting"}),
        exclude_sid=new_sid,
    ):
        data["status"] = "completed"
        data["current_agent"] = None
        log = data.get("log") or []
        log.append(
            {
                "ts": ts,
                "agent": "System",
                "summary": f"Superseded by new session {new_sid}.",
            }
        )
        data["log"] = log
        _save(path, data)


def cmd_init(args: argparse.Namespace) -> None:
    command = _normalize_command(args.command)
    active_begin = _find_active_begin(args.project)
    if active_begin is not None and command != _BEGIN_COMMAND:
        _, data = active_begin
        raise SystemExit(
            f"refusing init during active /kon:begin session {data['id']}: "
            "reuse that id (`kon_session.py active`)"
        )
    sid = _utcnow().strftime("%Y%m%d-%H%M%S") + "-" + _slug(args.task)
    pending = args.pending if args.pending is not None else _default_pending(command)
    data = {
        "id": sid,
        "task": args.task,
        "command": command,
        "project_path": str(resolve_project_path(args.project)),
        "started_at": _ts(),
        "status": "in_progress",
        "current_agent": None,
        "steps_completed": [],
        "steps_pending": pending,
        "steps_failed": [],
        "steps_waiting": [],
        "log": [],
    }
    if command == _BEGIN_COMMAND:
        data["mode"] = "interactive"
        data["turns"] = []
    ensure_session_dir(args.project, sid)
    path = session_json_path(args.project, sid)
    _save(path, data)
    _supersede_open_sessions(args.project, sid)
    print(sid)


def cmd_start_agent(args: argparse.Namespace) -> None:
    path, data = _load(args.id, args.project)
    agent = args.agent
    pending = data.get("steps_pending") or []
    if agent in pending:
        pending.remove(agent)
    data["steps_pending"] = pending
    data["current_agent"] = agent
    data["status"] = "in_progress"
    _save(path, data)


def _recompute_usage_totals(data: dict) -> None:
    totals: dict[str, int | str] = {}
    for entry in data.get("log") or []:
        usage = entry.get("usage")
        if not usage:
            continue
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = usage.get(key)
            if value is not None:
                totals[key] = int(totals.get(key, 0)) + int(value)
    if totals:
        totals["source"] = USAGE_SOURCE
        data["usage_totals"] = totals
    else:
        data.pop("usage_totals", None)


def _build_usage(input_tokens: int, output_tokens: int, source: str | None) -> dict:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "source": source or USAGE_SOURCE,
    }


def _last_log_index_for_agent(log: list, agent: str) -> int | None:
    for i in range(len(log) - 1, -1, -1):
        if log[i].get("agent") == agent:
            return i
    return None


def _hook_already_logged_step(log: list, agent: str, current_agent: str | None) -> bool:
    """True when subagentStop hook just finished this agent (orchestrator dedupe).

    A new milestone loop calls start-agent first, so current_agent is set again.
    """
    if not log:
        return False
    if log[-1].get("agent") != agent:
        return False
    return current_agent is None


def _apply_step_completion(data: dict, agent: str) -> None:
    completed = data.get("steps_completed") or []
    completed.append(agent)
    data["steps_completed"] = completed
    pending = data.get("steps_pending") or []
    if agent in pending:
        pending.remove(agent)
    data["steps_pending"] = pending
    data["current_agent"] = None
    waiting = data.get("steps_waiting") or []
    failed = data.get("steps_failed") or []
    if not pending and not waiting and not failed:
        data["status"] = _terminal_status_when_agents_done(data.get("command", ""))


def cmd_complete_agent(args: argparse.Namespace) -> None:
    path, data = _load(args.id, args.project)
    agent = args.agent
    log = data.get("log") or []
    usage = None
    if args.input_tokens is not None or args.output_tokens is not None:
        usage = _build_usage(
            int(args.input_tokens or 0),
            int(args.output_tokens or 0),
            args.usage_source,
        )

    if _hook_already_logged_step(log, agent, data.get("current_agent")):
        last = log[-1]
        if args.summary:
            last["summary"] = args.summary
        if usage and not last.get("usage"):
            last["usage"] = usage
        data["log"] = log
        _recompute_usage_totals(data)
        _save(path, data)
        return

    _apply_step_completion(data, agent)
    entry: dict = {"ts": _ts(), "agent": agent, "summary": args.summary}
    if usage:
        entry["usage"] = usage
    log.append(entry)
    data["log"] = log
    _recompute_usage_totals(data)
    _save(path, data)


def cmd_patch_usage(args: argparse.Namespace) -> None:
    """Legacy/backfill: attach token usage to latest log row. Prefer complete-agent --input-tokens."""
    path, data = _load(args.id, args.project)
    agent = args.agent
    log = data.get("log") or []
    usage = _build_usage(
        int(args.input_tokens or 0),
        int(args.output_tokens or 0),
        args.usage_source,
    )

    target_idx = _last_log_index_for_agent(log, agent)
    if target_idx is None:
        if not getattr(args, "summary", None):
            return
        log.append(
            {
                "ts": _ts(),
                "agent": agent,
                "summary": args.summary,
                "usage": usage,
            }
        )
        data["log"] = log
        _recompute_usage_totals(data)
        _save(path, data)
        return

    log[target_idx]["usage"] = usage
    data["log"] = log
    _recompute_usage_totals(data)
    _save(path, data)


def cmd_log_turn(args: argparse.Namespace) -> None:
    path, data = _load(args.id, args.project)
    log = data.get("log") or []
    log.append(
        {
            "ts": _ts(),
            "agent": args.agent,
            "summary": args.summary,
        }
    )
    data["log"] = log
    if data.get("command") == _BEGIN_COMMAND:
        data["status"] = "in_progress"
        if args.agent == "User":
            turns = data.get("turns") or []
            turns.append({"n": len(turns) + 1, "summary": args.summary})
            data["turns"] = turns
    _save(path, data)


def cmd_active(args: argparse.Namespace) -> None:
    found = _find_active_begin(args.project)
    if found is None:
        return
    _, data = found
    print(data["id"])


def cmd_open(args: argparse.Namespace) -> None:
    found = _find_open_session(args.project)
    if found is None:
        return
    _, data = found
    print(data["id"])


def cmd_set_status(args: argparse.Namespace) -> None:
    path, data = _load(args.id, args.project)
    data["status"] = args.status
    if args.status == "completed":
        data["current_agent"] = None
    _save(path, data)


_WAIT_AFTER_CHOICES = ("plan", "milestone", "milestones", "decision")


def cmd_wait_for_user(args: argparse.Namespace) -> None:
    """Pause pipeline until the user approves the next stage (dashboard shows waiting)."""
    if args.after == "milestone" and args.milestone is None:
        raise SystemExit("--milestone N is required when --after milestone")
    path, data = _load(args.id, args.project)
    data["status"] = "waiting"
    data["current_agent"] = None
    waiting = list(data.get("steps_waiting") or [])
    if "User" not in waiting:
        waiting.append("User")
    data["steps_waiting"] = waiting
    checkpoint: dict = {
        "summary": args.summary.strip(),
        "after": args.after,
        "ts": _ts(),
    }
    if args.milestone is not None:
        checkpoint["milestone"] = int(args.milestone)
    data["checkpoint"] = checkpoint
    _save(path, data)


def cmd_user_continued(args: argparse.Namespace) -> None:
    """Resume after wait-for-user — user approved proceeding to the next stage."""
    path, data = _load(args.id, args.project)
    checkpoint = data.get("checkpoint") or {}
    after = checkpoint.get("after")
    summary = (args.summary or "User approved — continuing.").strip()

    waiting = list(data.get("steps_waiting") or [])
    if "User" in waiting:
        waiting.remove("User")
    data["steps_waiting"] = waiting
    data.pop("checkpoint", None)
    data["status"] = "in_progress"

    completed = list(data.get("steps_completed") or [])
    pending = list(data.get("steps_pending") or [])
    if after in {"plan", "milestone", "milestones", "decision"}:
        if "User" in pending:
            pending.remove("User")
        if "User" not in completed:
            completed.append("User")
    data["steps_completed"] = completed
    data["steps_pending"] = pending

    log = data.get("log") or []
    log.append({"ts": _ts(), "agent": "User", "summary": summary})
    data["log"] = log
    _save(path, data)


def _close_session(path: Path, data: dict, *, summary: str) -> None:
    data["status"] = "completed"
    data["current_agent"] = None
    log = data.get("log") or []
    log.append({"ts": _ts(), "agent": "User", "summary": summary})
    data["log"] = log
    _save(path, data)


def cmd_finish(args: argparse.Namespace) -> None:
    """Close the most recent open session (or --id) — same as dashboard ✓."""
    summary = args.summary or "Session closed by user."
    if args.id:
        path, data = _load(args.id, args.project)
        if data.get("status") not in {"in_progress", "waiting"}:
            raise SystemExit(f"session is not open: {args.id} (status={data.get('status')!r})")
    else:
        found = _find_open_session(args.project)
        if found is None:
            raise SystemExit("no open session found")
        path, data = found
    _close_session(path, data, summary=summary)
    print(data["id"])


def cmd_session_dir(args: argparse.Namespace) -> None:
    directory = session_dir(args.project, args.id)
    if not resolve_session_json(args.project, args.id):
        raise SystemExit(f"session not found: {args.id}")
    print(directory)


def cmd_artifact_path(args: argparse.Namespace) -> None:
    if not resolve_session_json(args.project, args.id):
        raise SystemExit(f"session not found: {args.id}")
    print(session_artifact_path(args.project, args.id, args.name))


def _task_agent_scope(args: argparse.Namespace) -> str:
    return (getattr(args, "scope", None) or _TASK_AGENT_SCOPE_DEFAULT).strip()


def _task_agent_bucket(data: dict, scope: str, create: bool = False) -> dict[str, str]:
    if create:
        task_agents = data.setdefault("task_agents", {})
        return task_agents.setdefault(scope, {})
    return (data.get("task_agents") or {}).get(scope, {})


def cmd_set_task_agent(args: argparse.Namespace) -> None:
    """Persist a Cursor Task subagent id for resume within an implementation loop."""
    agent = args.agent.strip()
    if agent not in _IMPL_LOOP_AGENTS:
        raise SystemExit(
            f"unsupported agent for task-agent tracking: {agent!r} "
            f"(expected one of {sorted(_IMPL_LOOP_AGENTS)})"
        )
    task_id = args.task_id.strip()
    if not task_id:
        raise SystemExit("task_id must be non-empty")
    path, data = _load(args.id, args.project)
    bucket = _task_agent_bucket(data, _task_agent_scope(args), create=True)
    bucket[agent] = task_id
    _save(path, data)
    print(task_id)


def cmd_get_task_agent(args: argparse.Namespace) -> None:
    """Print stored Task subagent id for resume, or nothing if unset."""
    path, data = _load(args.id, args.project)
    task_id = _task_agent_bucket(data, _task_agent_scope(args)).get(args.agent.strip())
    if task_id:
        print(task_id)


def cmd_clear_task_agents(args: argparse.Namespace) -> None:
    """Drop stored Task ids for a scope (e.g. after Mio approves a milestone)."""
    path, data = _load(args.id, args.project)
    scope = _task_agent_scope(args)
    task_agents = data.get("task_agents") or {}
    if scope in task_agents:
        del task_agents[scope]
    if task_agents:
        data["task_agents"] = task_agents
    else:
        data.pop("task_agents", None)
    _save(path, data)


def main() -> None:
    parser = argparse.ArgumentParser(description="kon session file helper")
    parser.add_argument("--project", default=None, help="Project directory (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="Create a new session JSON")
    init.add_argument("--command", required=True, help='e.g. "/kon:ask", "/kon:team"')
    init.add_argument("--task", required=True, help="Task or question text")
    init.add_argument("--pending", nargs="*", default=None, help="Override steps_pending")
    init.set_defaults(func=cmd_init)

    start = sub.add_parser("start-agent", help="Mark agent as current")
    start.add_argument("--id", required=True)
    start.add_argument("--agent", required=True)
    start.set_defaults(func=cmd_start_agent)

    done = sub.add_parser("complete-agent", help="Mark agent done and append log")
    done.add_argument("--id", required=True)
    done.add_argument("--agent", required=True)
    done.add_argument("--summary", required=True)
    done.add_argument("--input-tokens", type=int, default=None)
    done.add_argument("--output-tokens", type=int, default=None)
    done.add_argument("--usage-source", default=None)
    done.set_defaults(func=cmd_complete_agent)

    patch_usage = sub.add_parser(
        "patch-usage",
        help="Attach token usage to the latest log entry for an agent",
    )
    patch_usage.add_argument("--id", required=True)
    patch_usage.add_argument("--agent", required=True)
    patch_usage.add_argument("--summary", default=None, help="Create log row if agent has none")
    patch_usage.add_argument("--input-tokens", type=int, default=None)
    patch_usage.add_argument("--output-tokens", type=int, default=None)
    patch_usage.add_argument("--usage-source", default=None)
    patch_usage.set_defaults(func=cmd_patch_usage)

    log_turn = sub.add_parser(
        "log-turn",
        help="Append a log entry without completing an agent step",
    )
    log_turn.add_argument("--id", required=True)
    log_turn.add_argument("--agent", required=True)
    log_turn.add_argument("--summary", required=True)
    log_turn.set_defaults(func=cmd_log_turn)

    active = sub.add_parser("active", help="Print active /kon:begin session id if any")
    active.set_defaults(func=cmd_active)

    open_cmd = sub.add_parser("open", help="Print most recent open session id if any")
    open_cmd.set_defaults(func=cmd_open)

    finish = sub.add_parser(
        "finish",
        help="Close the most recent open session (in_progress or waiting)",
    )
    finish.add_argument(
        "--id",
        default=None,
        help="Session id to close (default: most recent open session for this project)",
    )
    finish.add_argument(
        "--summary",
        default=None,
        help='Log summary (default: "Session closed by user.")',
    )
    finish.set_defaults(func=cmd_finish)

    status = sub.add_parser("set-status", help="Set session status")
    status.add_argument("--id", required=True)
    status.add_argument(
        "--status", required=True, choices=["in_progress", "waiting", "completed", "blocked"]
    )
    status.set_defaults(func=cmd_set_status)

    wait_user = sub.add_parser(
        "wait-for-user",
        help="Pause for user approval before the next pipeline stage",
    )
    wait_user.add_argument("--id", required=True)
    wait_user.add_argument(
        "--summary",
        required=True,
        help="What the user is approving (shown in dashboard)",
    )
    wait_user.add_argument(
        "--after",
        required=True,
        choices=_WAIT_AFTER_CHOICES,
        help="Stage just finished: plan, milestone (requires --milestone), decision (generic user gate), milestones (legacy)",
    )
    wait_user.add_argument(
        "--milestone",
        type=int,
        default=None,
        help="Milestone number (required for --after milestone; optional for --after milestones)",
    )
    wait_user.set_defaults(func=cmd_wait_for_user)

    user_cont = sub.add_parser(
        "user-continued",
        help="Resume after user approved wait-for-user checkpoint",
    )
    user_cont.add_argument("--id", required=True)
    user_cont.add_argument(
        "--summary",
        default=None,
        help='Log line (default: "User approved — continuing.")',
    )
    user_cont.set_defaults(func=cmd_user_continued)

    session_dir_cmd = sub.add_parser("session-dir", help="Print session artifact directory")
    session_dir_cmd.add_argument("--id", required=True)
    session_dir_cmd.set_defaults(func=cmd_session_dir)

    artifact = sub.add_parser("artifact-path", help="Print path to a named session artifact")
    artifact.add_argument("--id", required=True)
    artifact.add_argument(
        "--name",
        required=True,
        help="Artifact filename (e.g. plan.md, review.md, debug.md, summary.md)",
    )
    artifact.set_defaults(func=cmd_artifact_path)

    set_task = sub.add_parser(
        "set-task-agent",
        help="Store Cursor Task subagent id for resume (implementation loop)",
    )
    set_task.add_argument("--id", required=True)
    set_task.add_argument(
        "--agent",
        required=True,
        choices=sorted(_IMPL_LOOP_AGENTS),
        help="Yui, Sawako, or Mio",
    )
    set_task.add_argument("--task-id", required=True, help="Task subagent id from first spawn")
    set_task.add_argument(
        "--scope",
        default=_TASK_AGENT_SCOPE_DEFAULT,
        help=f"Loop scope (default: {_TASK_AGENT_SCOPE_DEFAULT})",
    )
    set_task.set_defaults(func=cmd_set_task_agent)

    get_task = sub.add_parser(
        "get-task-agent",
        help="Print stored Task subagent id for resume, if any",
    )
    get_task.add_argument("--id", required=True)
    get_task.add_argument(
        "--agent",
        required=True,
        choices=sorted(_IMPL_LOOP_AGENTS),
    )
    get_task.add_argument(
        "--scope",
        default=_TASK_AGENT_SCOPE_DEFAULT,
        help=f"Loop scope (default: {_TASK_AGENT_SCOPE_DEFAULT})",
    )
    get_task.set_defaults(func=cmd_get_task_agent)

    clear_task = sub.add_parser(
        "clear-task-agents",
        help="Clear stored Task ids for a scope (after milestone approved)",
    )
    clear_task.add_argument("--id", required=True)
    clear_task.add_argument(
        "--scope",
        default=_TASK_AGENT_SCOPE_DEFAULT,
        help=f"Loop scope (default: {_TASK_AGENT_SCOPE_DEFAULT})",
    )
    clear_task.set_defaults(func=cmd_clear_task_agents)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
