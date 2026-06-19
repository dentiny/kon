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
from _kon_paths import kon_root  # noqa: E402
from _token_estimate import SOURCE as USAGE_SOURCE, estimate_tokens_from_transcript  # noqa: E402

# Order matters — more specific roles first.
_ROLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Azusa-challenge", re.compile(r"Azusa-challenge|Azusa \(Challenge\)|challenge mode", re.I)),
    ("Mugi-revise", re.compile(r"Mugi-revise|Mugi \(Revise\)|revise mode", re.I)),
    ("Jun", re.compile(r"agents/Jun\.md|Researcher \(Jun\)|\bJun \(Researcher\)", re.I)),
    ("Nodoka", re.compile(r"Nodoka|Summarizer|agents/Nodoka\.md", re.I)),
    ("Sawako", re.compile(r"Sawako|Cleaner|agents/Sawako\.md", re.I)),
    ("Ritsu", re.compile(r"Ritsu|Verifier|agents/Ritsu\.md", re.I)),
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
    "Ritsu": "Ritsu",
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


def _usage_from_data(data: dict) -> dict | None:
    transcript = data.get("agent_transcript_path")
    if isinstance(transcript, str) and transcript.strip():
        return estimate_tokens_from_transcript(transcript.strip())
    return None


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


def _patch_open_session_usage(
    project: str,
    agent: str,
    usage: dict | None,
) -> None:
    if not usage:
        return
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
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--project",
            project,
            "patch-usage",
            "--id",
            sid,
            "--agent",
            agent,
            "--input-tokens",
            str(int(usage["input_tokens"])),
            "--output-tokens",
            str(int(usage["output_tokens"])),
            "--usage-source",
            str(usage.get("source", USAGE_SOURCE)),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


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
    _patch_open_session_usage(project, agent, _usage_from_data(data))
    emit("approve", f"{role}: quality check passed")


if __name__ == "__main__":
    main()
