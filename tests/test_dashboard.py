"""Tests for dashboard session delete."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

import dashboard  # noqa: E402


def test_delete_session_removes_json_and_summary() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        kon_data = tmp_path / "kon-data"
        sessions = kon_data / "projects" / "repo" / "sessions"
        sessions.mkdir(parents=True)
        (kon_data / "projects" / "repo" / "meta.json").write_text(
            json.dumps({"repo_name": "repo", "project_path": str(project.resolve())}),
            encoding="utf-8",
        )

        sid = "20260618-120000-test-delete"
        session_dir_path = sessions / sid
        session_json = session_dir_path / "session.json"
        summary = session_dir_path / "summary.md"
        legacy_flat = sessions / f"{sid}.json"
        legacy_summary = sessions / f"{sid}-summary.md"
        legacy_dir = project / ".kon" / "sessions"
        legacy_dir.mkdir(parents=True)
        legacy_json = legacy_dir / f"{sid}.json"
        legacy_project_summary = legacy_dir / f"{sid}-summary.md"

        payload = {
            "id": sid,
            "task": "test",
            "project_path": str(project.resolve()),
            "status": "completed",
        }
        session_dir_path.mkdir(parents=True)
        session_json.write_text(json.dumps(payload), encoding="utf-8")
        summary.write_text("# summary\n", encoding="utf-8")
        legacy_flat.write_text(json.dumps(payload), encoding="utf-8")
        legacy_summary.write_text("# legacy summary\n", encoding="utf-8")
        legacy_json.write_text(json.dumps(payload), encoding="utf-8")
        legacy_project_summary.write_text("# legacy project summary\n", encoding="utf-8")

        old_data = os.environ.get("KON_DATA_DIR")
        dashboard.PROJECT_FILTER = None
        dashboard._SESSION_FILES.clear()
        os.environ["KON_DATA_DIR"] = str(kon_data)
        try:
            deleted = dashboard.delete_session(sid)
        finally:
            if old_data is None:
                os.environ.pop("KON_DATA_DIR", None)
            else:
                os.environ["KON_DATA_DIR"] = old_data

        assert not session_json.exists()
        assert not session_dir_path.exists()
        assert not summary.exists()
        assert not legacy_flat.exists()
        assert not legacy_summary.exists()
        assert not legacy_json.exists()
        assert not legacy_project_summary.exists()
        assert len(deleted) >= 2


def test_delete_session_removes_project_review_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        kon_data = tmp_path / "kon-data"
        sessions = kon_data / "projects" / "repo" / "sessions"
        sessions.mkdir(parents=True)
        (kon_data / "projects" / "repo" / "meta.json").write_text(
            json.dumps({"repo_name": "repo", "project_path": str(project.resolve())}),
            encoding="utf-8",
        )

        sid = "20260618-120000-review-artifacts"
        session_root = sessions / sid
        session_json = session_root / "session.json"
        review_md = session_root / "review.md"
        debug_md = session_root / "debug.md"
        legacy_review = project / ".kon" / f"review-{sid}.md"
        session_root.mkdir(parents=True)
        review_md.write_text("# review\n", encoding="utf-8")
        debug_md.write_text("# debug\n", encoding="utf-8")
        legacy_review.parent.mkdir(parents=True)
        legacy_review.write_text("# legacy review\n", encoding="utf-8")

        payload = {
            "id": sid,
            "task": "review diff",
            "command": "/kon:review",
            "project_path": str(project.resolve()),
            "status": "completed",
        }
        session_json.write_text(json.dumps(payload), encoding="utf-8")

        old_data = os.environ.get("KON_DATA_DIR")
        dashboard.PROJECT_FILTER = None
        dashboard._SESSION_FILES.clear()
        os.environ["KON_DATA_DIR"] = str(kon_data)
        try:
            dashboard.delete_session(sid)
        finally:
            if old_data is None:
                os.environ.pop("KON_DATA_DIR", None)
            else:
                os.environ["KON_DATA_DIR"] = old_data

        assert not session_json.exists()
        assert not session_root.exists()
        assert not legacy_review.exists()


def test_dashboard_html_includes_token_usage_ui() -> None:
    assert "function fmtUsageBadge(" in dashboard._HTML
    assert "tok (est.)" in dashboard._HTML
    assert "usage-chip" in dashboard._HTML
