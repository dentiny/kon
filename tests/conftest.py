"""Shared pytest helpers for kon tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"
KON_SESSION_SCRIPT = ROOT / "scripts" / "kon_session.py"
KON_TODO_SCRIPT = ROOT / "scripts" / "kon_todo.py"


def run_script(script: Path, args: list[str], env: dict, cwd: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=str(cwd),
    )
    return proc.stdout.strip()


def run_kon_session(args: list[str], env: dict, cwd: Path) -> str:
    return run_script(KON_SESSION_SCRIPT, args, env, cwd)


def run_kon_todo(args: list[str], env: dict, cwd: Path) -> str:
    return run_script(KON_TODO_SCRIPT, args, env, cwd)


def run_hook(script: str, payload: dict | None = None, *, hooks_dir: Path = HOOKS) -> dict:
    proc = subprocess.run(
        [sys.executable, str(hooks_dir / script)],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


def mio_output(
    verdict: str,
    *,
    checklist_marks: list[str] | None = None,
    extra: str = "",
) -> str:
    labels = [
        "1. simplest correct implementation",
        "2. requirement coverage",
        "3. correctness proven",
        "4. edge cases handled",
        "5. no regression",
        "6. no performance issue",
        "7. consistent, safe, and tested",
    ]
    if checklist_marks is None:
        checklist_marks = ["x"] * len(labels)
    checklist = "\n".join(f"- [{mark}] {label}" for mark, label in zip(checklist_marks, labels))
    return (
        "## Loaded memory entries\n(no relevant entries)\n\n"
        f"## Verdict\n{verdict}\n\n"
        f"## Checklist\n{checklist}\n"
        f"{extra}"
    )


def isolated_kon_env() -> tuple[tempfile.TemporaryDirectory[str], Path, dict, Path]:
    tmp = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp.name)
    project = tmp_path / "repo"
    project.mkdir()
    env = {**os.environ, "KON_DATA_DIR": str(tmp_path / "kon-data")}
    sessions = tmp_path / "kon-data" / "projects" / "repo" / "sessions"
    return tmp, project, env, sessions


def load_session(sessions_dir: Path, sid: str) -> dict:
    nested = sessions_dir / sid / "session.json"
    if nested.is_file():
        return json.loads(nested.read_text(encoding="utf-8"))
    return json.loads((sessions_dir / f"{sid}.json").read_text(encoding="utf-8"))
