"""Tests for review artifact markdown (sessions/<session-id>/review.md)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

from _review_artifact import (  # noqa: E402
    extract_assistant_markdown,
    maybe_write_review_from_hook,
    review_artifact_path,
    write_review_artifact,
)
from _session_paths import ARTIFACT_REVIEW, SESSION_JSON  # noqa: E402


def test_extract_assistant_markdown_prefers_transcript() -> None:
    summary = "short summary"
    transcript = (
        json.dumps(
            {
                "role": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "📝 Mio: APPROVED — full review body"}]
                },
            }
        )
        + "\n"
    )
    body = extract_assistant_markdown(summary, transcript_path=None)
    assert body == summary

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
        fh.write(transcript)
        path = fh.name
    try:
        body = extract_assistant_markdown(summary, transcript_path=path)
        assert "full review body" in body
    finally:
        os.unlink(path)


def test_write_review_artifact_creates_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "repo"
        project.mkdir()
        path = write_review_artifact(
            project,
            "20260619-120000-test",
            command="/kon:review",
            task="review auth diff",
            body="## Verdict\nAPPROVED\n",
        )
        assert path is not None
        assert path == review_artifact_path(project, "20260619-120000-test")
        text = path.read_text(encoding="utf-8")
        assert "# Code review" in text
        assert "/kon:review" in text
        assert "review auth diff" in text
        assert "APPROVED" in text


def test_write_review_artifact_appends_for_debug() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "repo"
        project.mkdir()
        sid = "20260619-120000-debug"
        write_review_artifact(
            project,
            sid,
            command="/kon:debug",
            task="fix crash",
            body="First review pass",
        )
        write_review_artifact(
            project,
            sid,
            command="/kon:debug",
            task="fix crash",
            body="Second review pass",
            append=True,
        )
        text = review_artifact_path(project, sid).read_text(encoding="utf-8")
        assert "First review pass" in text
        assert "Second review pass" in text
        assert text.count("## Review —") == 1


def test_maybe_write_review_from_hook_review_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        kon_data = tmp_path / "kon-data"
        sessions = kon_data / "projects" / "repo" / "sessions"
        sessions.mkdir(parents=True)
        sid = "20260619-130000-review-hook"
        session_root = sessions / sid
        session_root.mkdir(parents=True)
        payload = {
            "id": sid,
            "task": "review staged diff",
            "command": "/kon:review",
            "project_path": str(project.resolve()),
            "status": "in_progress",
            "log": [],
        }
        (session_root / SESSION_JSON).write_text(json.dumps(payload), encoding="utf-8")

        old = os.environ.get("KON_DATA_DIR")
        os.environ["KON_DATA_DIR"] = str(kon_data)
        try:
            path = maybe_write_review_from_hook(
                project,
                agent="Mio",
                output="📝 Mio: ## Verdict\nAPPROVED\n",
            )
        finally:
            if old is None:
                os.environ.pop("KON_DATA_DIR", None)
            else:
                os.environ["KON_DATA_DIR"] = old

        assert path is not None
        assert path.is_file()
        assert "APPROVED" in path.read_text(encoding="utf-8")


def test_maybe_write_review_skips_team_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        kon_data = tmp_path / "kon-data"
        sessions = kon_data / "projects" / "repo" / "sessions"
        sessions.mkdir(parents=True)
        sid = "20260619-130000-team"
        session_root = sessions / sid
        session_root.mkdir(parents=True)
        payload = {
            "id": sid,
            "task": "feature",
            "command": "/kon:team",
            "project_path": str(project.resolve()),
            "status": "in_progress",
        }
        (session_root / SESSION_JSON).write_text(json.dumps(payload), encoding="utf-8")

        old = os.environ.get("KON_DATA_DIR")
        os.environ["KON_DATA_DIR"] = str(kon_data)
        try:
            path = maybe_write_review_from_hook(
                project,
                agent="Mio",
                output="📝 Mio: APPROVED",
            )
        finally:
            if old is None:
                os.environ.pop("KON_DATA_DIR", None)
            else:
                os.environ["KON_DATA_DIR"] = old

        assert path is None


def _mio_output(verdict: str) -> str:
    labels = [
        "acceptance match",
        "evidence per function",
        "edge case coverage",
        "convention conformance",
        "no unsafe pattern",
        "no unexplained magic",
        "no TODO evasion",
        "no defensive bloat",
        "no completeness theatre",
    ]
    checklist = "\n".join(f"- [x] {label}" for label in labels)
    return (
        "## Loaded memory entries\n(no relevant entries)\n\n"
        f"## Verdict\n{verdict}\n\n"
        f"## Checklist\n{checklist}\n"
    )


def _run_hook(script: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "hooks" / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


def test_hook_writes_review_file_for_review_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    data_root = tmp_path / "kon-data"
    monkeypatch.setenv("KON_DATA_DIR", str(data_root))
    monkeypatch.setenv("KON_ROOT", str(ROOT))

    sid = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "kon_session.py"),
            "--project",
            str(project),
            "init",
            "--command",
            "/kon:review",
            "--task",
            "review uncommitted diff",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    mio_output = _mio_output("APPROVED")
    _run_hook(
        "on_subagent_stop.py",
        {
            "hook_event_name": "subagentStop",
            "status": "completed",
            "cwd": str(project),
            "task": "Mio reviewer agents/Mio.md",
            "summary": mio_output,
        },
    )

    review_path = review_artifact_path(str(project), sid)
    assert review_path.is_file()
    text = review_path.read_text(encoding="utf-8")
    assert "APPROVED" in text
    assert "/kon:review" in text
