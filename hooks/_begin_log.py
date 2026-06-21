"""Shared helpers for auto-logging /kon:begin interactive session turns."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from _kon_paths import hook_log_path, iter_sessions_dirs, kon_root, resolve_project_path
from _session_paths import iter_session_json_paths

_BEGIN_COMMAND = "/kon:begin"
_KON_CMD = re.compile(r"^/kon:([\w-]+)(?:\s+(.*))?$", re.DOTALL | re.IGNORECASE)
_LOG_NAME = "log_begin_turn"
_SUMMARY_MAX = 200
_ASSISTANT_MIN = 12


def hook_log(message: str) -> None:
    try:
        path = hook_log_path(_LOG_NAME)
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def kon_session_script() -> Path | None:
    script = kon_root() / "scripts" / "kon_session.py"
    return script if script.is_file() else None


def find_active_begin(project: str | None) -> tuple[Path, dict] | None:
    project_path = str(resolve_project_path(project))
    best: tuple[Path, dict] | None = None
    best_key = ""
    for directory in iter_sessions_dirs(project):
        for _sid, path in iter_session_json_paths(directory):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("project_path") != project_path:
                continue
            if data.get("command") != _BEGIN_COMMAND:
                continue
            if data.get("status") not in {"in_progress", "waiting"}:
                continue
            key = data.get("started_at") or data.get("id") or ""
            if key >= best_key:
                best_key = key
                best = (path, data)
    return best


def truncate_summary(text: str, limit: int = _SUMMARY_MAX) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def user_summary_from_prompt(prompt: str) -> str | None:
    text = prompt.strip()
    if not text:
        return None
    match = _KON_CMD.match(text)
    if match:
        command = f"/kon:{match.group(1)}"
        if command in {"/kon:begin", "/kon:finish"}:
            return None
        task = (match.group(2) or "").strip()
        return truncate_summary(task or command.replace("/kon:", ""))
    return truncate_summary(text)


def assistant_summary_from_text(text: str) -> str | None:
    raw = text.strip()
    if not raw:
        return None
    for line in raw.splitlines():
        cleaned = re.sub(r"^#+\s*", "", line.strip())
        cleaned = re.sub(r"^\*+\s*", "", cleaned)
        cleaned = cleaned.strip()
        if len(cleaned) >= _ASSISTANT_MIN:
            return truncate_summary(cleaned)
    collapsed = truncate_summary(raw)
    return collapsed if len(collapsed) >= _ASSISTANT_MIN else None


def agent_logged_since_last_user(log: list[dict], agent: str) -> bool:
    last_user_idx = -1
    for i, entry in enumerate(log):
        if entry.get("agent") == "User":
            last_user_idx = i
    for entry in log[last_user_idx + 1 :]:
        if entry.get("agent") == agent:
            return True
    return False


def last_log_matches(log: list[dict], agent: str, summary: str) -> bool:
    if not log:
        return False
    last = log[-1]
    return last.get("agent") == agent and last.get("summary") == summary


def append_session_log(
    project: str,
    session_id: str,
    agent: str,
    summary: str,
    *,
    complete: bool = False,
) -> bool:
    script = kon_session_script()
    if script is None:
        return False
    subcmd = "complete-agent" if complete else "log-turn"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--project",
            project,
            subcmd,
            "--id",
            session_id,
            "--agent",
            agent,
            "--summary",
            summary,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        hook_log(
            f"append failed sid={session_id} agent={agent} "
            f"err={(proc.stderr or proc.stdout).strip()}"
        )
        return False
    return True
