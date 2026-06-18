#!/usr/bin/env python3
"""kon subagentStop bridge: run teammate_quality_check after Task subagents finish."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit, set_hook_event  # noqa: E402
from teammate_quality_check import ROLE_HANDLERS  # noqa: E402

# Order matters — more specific roles first.
_ROLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Azusa-challenge", re.compile(r"Azusa-challenge|Azusa \(Challenge\)|challenge mode", re.I)),
    ("Mugi-revise", re.compile(r"Mugi-revise|Mugi \(Revise\)|revise mode", re.I)),
    ("Nodoka", re.compile(r"Nodoka|Summarizer|agents/Nodoka\.md", re.I)),
    ("Sawako", re.compile(r"Sawako|Cleaner|agents/Sawako\.md", re.I)),
    ("Ritsu", re.compile(r"Ritsu|Verifier|agents/Ritsu\.md", re.I)),
    ("Mio", re.compile(r"Mio|Reviewer|agents/Mio\.md", re.I)),
    ("Yui", re.compile(r"Yui|Implementer|agents/Yui\.md", re.I)),
    ("Mugi", re.compile(r"Mugi|Planner|agents/Mugi\.md", re.I)),
    ("Azusa", re.compile(r"Azusa|Explorer|agents/Azusa\.md", re.I)),
]


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


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit("approve", "on_subagent_stop: invalid JSON input — skipping")

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

    handler = ROLE_HANDLERS.get(role)
    if handler is None:
        emit("approve", f"{role}: no quality spec — passing by default")

    handler(output)


if __name__ == "__main__":
    main()
