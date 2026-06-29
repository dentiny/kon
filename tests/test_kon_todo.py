"""Tests for kon_todo.py."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from conftest import run_kon_todo

ROOT = Path(__file__).resolve().parent.parent


def test_add_list_done_delete() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "repo"
        project.mkdir()
        env = {**os.environ, "KON_DATA_DIR": str(Path(tmp) / "kon-data")}
        todo_path = project / ".kon" / "todos.json"

        todo_id = run_kon_todo(["add", "--text", "ship todo feature"], env, project)
        assert todo_id
        assert todo_path.is_file()

        listing = run_kon_todo(["list", "--status", "open"], env, project)
        assert todo_id in listing
        assert "ship todo feature" in listing

        run_kon_todo(["done", "--id", todo_id], env, project)
        data = json.loads(todo_path.read_text(encoding="utf-8"))
        item = next(i for i in data["items"] if i["id"] == todo_id)
        assert item["status"] == "done"
        assert item["completed_at"]

        run_kon_todo(["open", "--id", todo_id], env, project)
        data = json.loads(todo_path.read_text(encoding="utf-8"))
        item = next(i for i in data["items"] if i["id"] == todo_id)
        assert item["status"] == "open"
        assert item["completed_at"] is None

        run_kon_todo(["delete", "--id", todo_id], env, project)
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
