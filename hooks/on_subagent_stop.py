#!/usr/bin/env python3
"""kon subagentStop bridge: run teammate_quality_check after Task subagents finish."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit, format_payload, read_hook_stdin, resolve_hook_cwd, set_hook_event  # noqa: E402
from _begin_log import (  # noqa: E402
    agent_logged_since_last_user,
    append_session_log,
    assistant_summary_from_text,
    find_active_begin,
    hook_log,
)
from _kon_paths import kon_root  # noqa: E402
from _token_estimate import (  # noqa: E402
    SOURCE as USAGE_SOURCE,
    estimate_tokens_from_output_text,
    estimate_tokens_from_transcript,
)

# Order matters — more specific roles first.
_ROLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Azusa-challenge", re.compile(r"Azusa-challenge|Azusa \(Challenge\)|challenge mode", re.I)),
    ("Mugi-revise", re.compile(r"Mugi-revise|Mugi \(Revise\)|revise mode", re.I)),
    ("Jun", re.compile(r"agents/Jun\.md|Researcher \(Jun\)|\bJun \(Researcher\)", re.I)),
    ("Nodoka", re.compile(r"Nodoka|Summarizer|agents/Nodoka\.md", re.I)),
    ("Sawako", re.compile(r"Sawako|Cleaner|agents/Sawako\.md", re.I)),
    ("Mio", re.compile(r"Mio|Reviewer|agents/Mio\.md", re.I)),
    ("Yui", re.compile(r"Yui|Implementer|agents/Yui\.md", re.I)),
    ("Mugi", re.compile(r"Mugi|Planner|agents/Mugi\.md", re.I)),
    ("Azusa", re.compile(r"Azusa|Explorer|agents/Azusa\.md", re.I)),
]

# Session steps_pending uses base agent names, not challenge/revise variants.
_ROLE_TO_AGENT: dict[str, str] = {
    "Azusa-challenge": "Azusa",
    "Mugi-revise": "Mugi",
    "Jun": "Jun",
    "Nodoka": "Nodoka",
    "Sawako": "Sawako",
    "Mio": "Mio",
    "Yui": "Yui",
    "Mugi": "Mugi",
    "Azusa": "Azusa",
}


def _infer_role(data: dict) -> str | None:
    haystack = "\n".join(str(data.get(key) or "") for key in ("task", "description", "summary"))
    for role, pattern in _ROLE_PATTERNS:
        if pattern.search(haystack):
            return role
    return None


def _load_output(data: dict) -> str:
    summary = str(data.get("summary") or "").strip()
    transcript = data.get("agent_transcript_path")
    if isinstance(transcript, str) and transcript.strip():
        path = Path(transcript.strip())
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                if len(text) > len(summary):
                    return text
            except OSError:
                pass
    return summary


def _session_agent_name(role: str) -> str:
    return _ROLE_TO_AGENT.get(role, role)


def _usage_from_data(data: dict, output: str) -> dict | None:
    transcript = data.get("agent_transcript_path")
    if isinstance(transcript, str) and transcript.strip():
        usage = estimate_tokens_from_transcript(transcript.strip())
        if usage:
            return usage
    return estimate_tokens_from_output_text(output)


def _summary_from_output(output: str, agent: str) -> str:
    summary = assistant_summary_from_text(output)
    if summary:
        return summary
    summary = assistant_summary_from_text(output[:500])
    return summary or f"{agent} finished"


def _complete_open_session_from_hook(
    project: str,
    agent: str,
    summary: str,
    usage: dict | None,
) -> None:
    root = kon_root()
    script = root / "scripts" / "kon_session.py"
    if not script.is_file():
        return
    proc = subprocess.run(
        [sys.executable, str(script), "--project", project, "open"],
        capture_output=True,
        text=True,
        check=False,
    )
    sid = proc.stdout.strip()
    if not sid:
        return
    cmd = [
        sys.executable,
        str(script),
        "--project",
        project,
        "complete-agent",
        "--id",
        sid,
        "--agent",
        agent,
        "--summary",
        summary,
    ]
    if usage:
        cmd += [
            "--input-tokens",
            str(int(usage["input_tokens"])),
            "--output-tokens",
            str(int(usage["output_tokens"])),
            "--usage-source",
            str(usage.get("source", USAGE_SOURCE)),
        ]
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def _quality_block_payload(role: str, output: str) -> dict | None:
    """Run quality check in a subprocess; return block payload or None if approved."""
    script = Path(__file__).resolve().parent / "teammate_quality_check.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps({"teammate_role": role, "teammate_output": output}),
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout.strip()
    if not out:
        return None
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return None
    if payload.get("decision") == "block":
        reason = str(payload.get("reason") or payload.get("systemMessage") or "blocked")
        return format_payload("block", reason, event="subagentStop")
    return None


def _log_subagent_to_begin_session(project: str, agent: str, output: str) -> None:
    found = find_active_begin(project)
    if found is None:
        return
    _, session = found
    log = session.get("log") or []
    if agent_logged_since_last_user(log, agent):
        return
    summary = assistant_summary_from_text(output)
    if summary is None:
        summary = assistant_summary_from_text(output[:500]) or f"{agent} finished"
    if append_session_log(project, session["id"], agent, summary, complete=True):
        hook_log(f"logged {agent} sid={session['id']} summary={summary[:60]!r}")


def main() -> None:
    data = read_hook_stdin()
    set_hook_event(data.get("hook_event_name") or "subagentStop")

    status = str(data.get("status") or "completed")
    if status != "completed":
        emit("approve", f"subagent status={status} — skipping quality check")

    role = _infer_role(data)
    if role is None:
        emit("approve", "no kon agent role detected in subagent output — skipping")

    output = _load_output(data)
    if not output.strip():
        emit("approve", f"{role}: empty subagent output — skipping quality check")

    block_payload = _quality_block_payload(role, output)
    if block_payload:
        sys.stdout.write(json.dumps(block_payload, ensure_ascii=False) + "\n")
        sys.exit(0)

    project = resolve_hook_cwd(data)
    agent = _session_agent_name(role)
    usage = _usage_from_data(data, output)
    summary = str(data.get("summary") or "").strip() or _summary_from_output(output, agent)
    _log_subagent_to_begin_session(project, agent, output)
    _complete_open_session_from_hook(project, agent, summary, usage)
    emit("approve", f"{role}: quality check passed")


if __name__ == "__main__":
    main()
