"""Tests for kon_todo.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "kon_todo.py"


def _run(args: list[str], env: dict, cwd: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=str(cwd),
    )
    return proc.stdout.strip()


def test_add_list_done_delete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "repo"
        project.mkdir()
        env = {**os.environ, "KON_DATA_DIR": str(Path(tmp) / "kon-data")}
        todo_path = project / ".kon" / "todos.json"

        todo_id = _run(["add", "--text", "ship todo feature"], env, project)
        assert todo_id
        assert todo_path.is_file()

        listing = _run(["list", "--status", "open"], env, project)
        assert todo_id in listing
        assert "ship todo feature" in listing

        _run(["done", "--id", todo_id], env, project)
        data = json.loads(todo_path.read_text(encoding="utf-8"))
        item = next(i for i in data["items"] if i["id"] == todo_id)
        assert item["status"] == "done"
        assert item["completed_at"]

        _run(["open", "--id", todo_id], env, project)
        data = json.loads(todo_path.read_text(encoding="utf-8"))
        item = next(i for i in data["items"] if i["id"] == todo_id)
        assert item["status"] == "open"
        assert item["completed_at"] is None

        _run(["delete", "--id", todo_id], env, project)
        data = json.loads(todo_path.read_text(encoding="utf-8"))
        assert data["items"] == []


def test_add_requires_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "repo"
        project.mkdir()

        sys.path.insert(0, str(ROOT / "scripts"))
        from kon_todo import add_todo  # noqa: E402

        with pytest.raises(ValueError, match="required"):
            add_todo("   ", project)
