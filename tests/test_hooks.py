"""Tests for kon hook scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"

sys.path.insert(0, str(HOOKS))
from _hook_io import format_payload  # noqa: E402
from on_subagent_stop import _infer_role  # noqa: E402


def _run_hook(script: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


class TestHookIo:
    def test_shell_deny(self) -> None:
        payload = format_payload("block", "nope", event="beforeShellExecution")
        assert payload["permission"] == "deny"
        assert payload["user_message"] == "nope"

    def test_stop_followup(self) -> None:
        payload = format_payload("block", "retry please", event="stop")
        assert payload == {"followup_message": "retry please"}

    def test_legacy_approve(self) -> None:
        payload = format_payload("approve", "ok", event=None)
        assert payload["decision"] == "approve"


class TestNoGitWrite:
    def test_blocks_commit(self) -> None:
        result = _run_hook(
            "no_git_write.py",
            {
                "hook_event_name": "beforeShellExecution",
                "command": "git commit -m test",
            },
        )
        assert result["permission"] == "deny"

    def test_allows_status(self) -> None:
        result = _run_hook(
            "no_git_write.py",
            {
                "hook_event_name": "beforeShellExecution",
                "command": "git status",
            },
        )
        assert result["permission"] == "allow"


class TestOnSubagentStop:
    def test_infers_mio(self) -> None:
        role = _infer_role({"task": "You are Mio reviewer agents/Mio.md", "summary": ""})
        assert role == "Mio"

    def test_blocks_missing_verdict(self) -> None:
        result = _run_hook(
            "on_subagent_stop.py",
            {
                "hook_event_name": "subagentStop",
                "status": "completed",
                "task": "Mio reviewer agents/Mio.md",
                "summary": "## Loaded memory entries\n(no relevant entries)\n\nNo verdict here.",
            },
        )
        assert "followup_message" in result
        assert "verdict" in result["followup_message"].lower()


class TestTeammateQualityCheck:
    def test_mio_approved(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "Verdict: APPROVED\n"
            "- [x] item 1\n- [x] item 2\n"
        )
        result = _run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Mio", "teammate_output": output},
        )
        assert result["decision"] == "approve"

    def test_jun_with_sources(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Research summary\n- `.kon/research.md` — Cursor stop hook docs\n\n"
            "## Sources\n- https://cursor.com/docs/hooks — hook events\n"
        )
        result = _run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Jun", "teammate_output": output},
        )
        assert result["decision"] == "approve"


class TestOnSubagentStopRole:
    def test_infers_jun(self) -> None:
        role = _infer_role({"task": "Jun researcher agents/Jun.md", "summary": ""})
        assert role == "Jun"

    def test_jun_not_june(self) -> None:
        role = _infer_role({"task": "Review schedule for June release", "summary": ""})
        assert role is None


class TestVerifyCompletion:
    def test_skips_aborted_stop(self) -> None:
        result = _run_hook(
            "verify_completion.py",
            {"hook_event_name": "stop", "status": "aborted"},
        )
        assert result == {}
