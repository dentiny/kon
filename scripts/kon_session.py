#!/usr/bin/env python3
"""kon session file CLI — reliable create/update for orchestrators."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from _kon_paths import ensure_sessions_dir, iter_sessions_dirs, resolve_project_path  # noqa: E402

_BEGIN_COMMAND = "/kon:begin"

# One-shot commands: auto-complete when the sole agent finishes (no dashboard clutter).
_EPHEMERAL_COMMANDS = frozenset({"/kon:ask", "/kon:research", "/kon:review"})


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _slug(task: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", task.lower())[:40].strip("-") or "task"


def _session_path(session_id: str, project: str | None) -> Path | None:
    for directory in iter_sessions_dirs(project):
        path = directory / f"{session_id}.json"
        if path.is_file():
            return path
    return None


def _load(session_id: str, project: str | None) -> tuple[Path, dict]:
    path = _session_path(session_id, project)
    if path is None:
        raise SystemExit(f"session not found: {session_id}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_command(command: str) -> str:
    """Require slash form: /kon:go, /kon:ask, …"""
    c = command.strip()
    if not c.startswith("/kon:"):
        raise SystemExit(f'command must be /kon:<name> (e.g. "/kon:go"), got: {command!r}')
    return c


def _default_pending(command: str) -> list[str]:
    c = _normalize_command(command)
    if c == "/kon:ask":
        return ["Azusa"]
    if c == "/kon:research":
        return ["Jun"]
    if c == "/kon:review":
        return ["Mio"]
    if c == "/kon:begin":
        return []
    if c == "/kon:design":
        return ["Azusa", "Mugi", "User"]
    return []


def _find_active_begin(project: str | None) -> tuple[Path, dict] | None:
    """Most recent open /kon:begin session for this project."""
    project_path = str(resolve_project_path(project))
    best: tuple[Path, dict] | None = None
    best_key = ""
    for directory in iter_sessions_dirs(project):
        for path in directory.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("command") != _BEGIN_COMMAND:
                continue
            if data.get("project_path") != project_path:
                continue
            if data.get("status") not in ("in_progress", "waiting"):
                continue
            key = data.get("started_at") or data.get("id") or ""
            if key >= best_key:
                best_key = key
                best = (path, data)
    return best


def _terminal_status_when_agents_done(command: str) -> str:
    if command == _BEGIN_COMMAND:
        return "in_progress"
    if command in _EPHEMERAL_COMMANDS:
        return "completed"
    return "waiting"


def _supersede_open_sessions(project: str | None, new_sid: str) -> None:
    """Close other in_progress/waiting sessions for this project when a new run starts."""
    project_path = str(resolve_project_path(project))
    ts = _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for directory in iter_sessions_dirs(project):
        for path in directory.glob("*.json"):
            if path.stem == new_sid:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("project_path") != project_path:
                continue
            if data.get("status") not in ("in_progress", "waiting"):
                continue
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
    sid = _utcnow().strftime("%Y%m%d-%H%M%S") + "-" + _slug(args.task)
    command = _normalize_command(args.command)
    pending = args.pending if args.pending is not None else _default_pending(command)
    data = {
        "id": sid,
        "task": args.task,
        "command": command,
        "project_path": str(resolve_project_path(args.project)),
        "started_at": _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    path = ensure_sessions_dir(args.project) / f"{sid}.json"
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


def cmd_complete_agent(args: argparse.Namespace) -> None:
    path, data = _load(args.id, args.project)
    agent = args.agent
    completed = data.get("steps_completed") or []
    if agent not in completed:
        completed.append(agent)
    data["steps_completed"] = completed
    pending = data.get("steps_pending") or []
    if agent in pending:
        pending.remove(agent)
    data["steps_pending"] = pending
    data["current_agent"] = None
    pending = data.get("steps_pending") or []
    waiting = data.get("steps_waiting") or []
    failed = data.get("steps_failed") or []
    if not pending and not waiting and not failed:
        data["status"] = _terminal_status_when_agents_done(data.get("command", ""))
    log = data.get("log") or []
    log.append(
        {
            "ts": _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": agent,
            "summary": args.summary,
        }
    )
    data["log"] = log
    _save(path, data)


def cmd_log_turn(args: argparse.Namespace) -> None:
    path, data = _load(args.id, args.project)
    log = data.get("log") or []
    log.append(
        {
            "ts": _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": args.agent,
            "summary": args.summary,
        }
    )
    data["log"] = log
    if data.get("command") == _BEGIN_COMMAND:
        data["status"] = "in_progress"
    _save(path, data)


def cmd_active(args: argparse.Namespace) -> None:
    found = _find_active_begin(args.project)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="kon session file helper")
    parser.add_argument("--project", default=None, help="Project directory (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="Create a new session JSON")
    init.add_argument("--command", required=True, help='e.g. "/kon:ask", "/kon:go"')
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
    done.set_defaults(func=cmd_complete_agent)

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

    status = sub.add_parser("set-status", help="Set session status")
    status.add_argument("--id", required=True)
    status.add_argument(
        "--status", required=True, choices=["in_progress", "waiting", "completed", "blocked"]
    )
    status.set_defaults(func=cmd_set_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
