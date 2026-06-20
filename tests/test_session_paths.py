"""Tests for per-session directory layout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

from _session_paths import (  # noqa: E402
    ARTIFACT_PLAN,
    ARTIFACT_REVIEW,
    SESSION_JSON,
    all_session_delete_paths,
    session_artifact_path,
    session_dir,
)


def test_init_creates_session_directory() -> None:
    script = ROOT / "scripts" / "kon_session.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        env = {**os.environ, "KON_DATA_DIR": str(tmp_path / "kon-data")}
        old = os.environ.get("KON_DATA_DIR")
        os.environ["KON_DATA_DIR"] = str(tmp_path / "kon-data")
        try:
            sid = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "init",
                    "--command",
                    "/kon:team",
                    "--task",
                    "layout test",
                ],
                capture_output=True,
                text=True,
                check=True,
                env=env,
                cwd=str(project),
            ).stdout.strip()
            directory = session_dir(project, sid)
            assert directory.is_dir()
            assert (directory / SESSION_JSON).is_file()
            data = json.loads((directory / SESSION_JSON).read_text(encoding="utf-8"))
            assert data["id"] == sid
        finally:
            if old is None:
                os.environ.pop("KON_DATA_DIR", None)
            else:
                os.environ["KON_DATA_DIR"] = old


def test_artifact_path_cli() -> None:
    script = ROOT / "scripts" / "kon_session.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        env = {**os.environ, "KON_DATA_DIR": str(tmp_path / "kon-data")}
        sid = subprocess.run(
            [sys.executable, str(script), "init", "--command", "/kon:review", "--task", "paths"],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            cwd=str(project),
        ).stdout.strip()
        plan = subprocess.run(
            [
                sys.executable,
                str(script),
                "artifact-path",
                "--id",
                sid,
                "--name",
                ARTIFACT_PLAN,
            ],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            cwd=str(project),
        ).stdout.strip()
        assert plan.endswith(f"/sessions/{sid}/{ARTIFACT_PLAN}")


def test_all_session_delete_paths_includes_dir_and_legacy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "repo"
        project.mkdir()
        kon_data = tmp_path / "kon-data"
        sessions = kon_data / "projects" / "repo" / "sessions"
        sid = "20260619-140000-delete-me"
        session_root = sessions / sid
        session_root.mkdir(parents=True)
        (session_root / SESSION_JSON).write_text("{}", encoding="utf-8")
        (session_root / ARTIFACT_REVIEW).write_text("# review", encoding="utf-8")
        legacy_plan = project / ".kon" / f"plan-{sid}.md"
        legacy_plan.parent.mkdir(parents=True)
        legacy_plan.write_text("# plan", encoding="utf-8")
        (sessions / f"{sid}.json").write_text("{}", encoding="utf-8")

        old = os.environ.get("KON_DATA_DIR")
        os.environ["KON_DATA_DIR"] = str(kon_data)
        try:
            paths = all_session_delete_paths(sid, str(project.resolve()))
        finally:
            if old is None:
                os.environ.pop("KON_DATA_DIR", None)
            else:
                os.environ["KON_DATA_DIR"] = old

        resolved = {p.resolve() for p in paths}
        assert session_root.resolve() in resolved
        assert (sessions / f"{sid}.json").resolve() in resolved
        assert legacy_plan.resolve() in resolved
