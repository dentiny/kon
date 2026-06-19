#!/usr/bin/env python3
"""kon todo list — project-local tasks in .kon/todos.json."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from _kon_paths import (  # noqa: E402
    kon_data_dir,
    project_kon_dir,
    resolve_project_path,
)

VERSION = 1


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:32].strip("-") or "todo"


def _new_id(text: str) -> str:
    return _utcnow().strftime("%Y%m%d-%H%M%S") + "-" + _slug(text)


def todos_file(project: Path | str | None = None) -> Path:
    return project_kon_dir(project) / "todos.json"


def _empty_store() -> dict[str, Any]:
    return {"version": VERSION, "items": []}


def load_store(project: Path | str | None = None) -> dict[str, Any]:
    path = todos_file(project)
    if not path.is_file():
        return _empty_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_store()
    if not isinstance(data.get("items"), list):
        return _empty_store()
    data.setdefault("version", VERSION)
    return data


def save_store(data: dict[str, Any], project: Path | str | None = None) -> Path:
    directory = project_kon_dir(project)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "todos.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _find_item(store: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    for item in store.get("items") or []:
        if item.get("id") == item_id:
            return item
    return None


def add_todo(text: str, project: Path | str | None = None) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("todo text is required")
    store = load_store(project)
    item = {
        "id": _new_id(text),
        "text": text,
        "status": "open",
        "created_at": _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": None,
    }
    store.setdefault("items", []).append(item)
    save_store(store, project)
    return item


def list_todos(
    project: Path | str | None = None,
    status: str = "all",
) -> list[dict[str, Any]]:
    items = list(load_store(project).get("items") or [])
    if status == "open":
        items = [i for i in items if i.get("status") == "open"]
    elif status == "done":
        items = [i for i in items if i.get("status") == "done"]
    return items


def set_todo_status(
    item_id: str,
    status: str,
    project: Path | str | None = None,
) -> dict[str, Any]:
    if status not in ("open", "done"):
        raise ValueError(f"invalid status: {status}")
    store = load_store(project)
    item = _find_item(store, item_id)
    if item is None:
        raise LookupError(f"todo not found: {item_id}")
    item["status"] = status
    item["completed_at"] = _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") if status == "done" else None
    save_store(store, project)
    return item


def delete_todo(item_id: str, project: Path | str | None = None) -> dict[str, Any]:
    store = load_store(project)
    items = store.get("items") or []
    kept: list[dict[str, Any]] = []
    deleted: dict[str, Any] | None = None
    for item in items:
        if item.get("id") == item_id:
            deleted = item
        else:
            kept.append(item)
    if deleted is None:
        raise LookupError(f"todo not found: {item_id}")
    store["items"] = kept
    save_store(store, project)
    return deleted


def iter_project_todo_sources(
    project_filter: Path | str | None = None,
) -> list[tuple[Path, str]]:
    """Return (todos.json path, project_path) pairs to scan."""
    if project_filter is not None:
        project_path = str(resolve_project_path(project_filter))
        path = todos_file(project_filter)
        return [(path, project_path)] if path.is_file() else []

    sources: list[tuple[Path, str]] = []
    projects_root = kon_data_dir() / "projects"
    if not projects_root.is_dir():
        return sources

    for entry in sorted(projects_root.iterdir()):
        if not entry.is_dir():
            continue
        meta = entry / "meta.json"
        if not meta.is_file():
            continue
        try:
            meta_data = json.loads(meta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        project_path = meta_data.get("project_path")
        if not project_path:
            continue
        path = Path(project_path) / ".kon" / "todos.json"
        if path.is_file():
            sources.append((path, project_path))
    return sources


def load_all_todos(project_filter: Path | str | None = None) -> list[dict[str, Any]]:
    """Load todos from one or all projects; each item includes project_path."""
    items: list[dict[str, Any]] = []
    for path, project_path in iter_project_todo_sources(project_filter):
        try:
            store = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for item in store.get("items") or []:
            enriched = dict(item)
            enriched["project_path"] = project_path
            items.append(enriched)
    items.sort(key=lambda i: i.get("created_at") or "", reverse=True)
    return items


def cmd_add(args: argparse.Namespace) -> None:
    item = add_todo(args.text, args.project)
    print(item["id"])


def cmd_list(args: argparse.Namespace) -> None:
    for item in list_todos(args.project, args.status):
        mark = "✓" if item.get("status") == "done" else " "
        print(f"[{mark}] {item['id']}  {item.get('text', '')}")


def cmd_done(args: argparse.Namespace) -> None:
    set_todo_status(args.id, "done", args.project)
    print(args.id)


def cmd_open(args: argparse.Namespace) -> None:
    set_todo_status(args.id, "open", args.project)
    print(args.id)


def cmd_delete(args: argparse.Namespace) -> None:
    delete_todo(args.id, args.project)
    print(args.id)


def main() -> None:
    parser = argparse.ArgumentParser(description="kon todo list helper")
    parser.add_argument("--project", default=None, help="Project directory (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Add a todo item")
    add.add_argument("--text", required=True)
    add.set_defaults(func=cmd_add)

    lst = sub.add_parser("list", help="List todo items")
    lst.add_argument(
        "--status",
        default="all",
        choices=["all", "open", "done"],
    )
    lst.set_defaults(func=cmd_list)

    done = sub.add_parser("done", help="Mark a todo as done")
    done.add_argument("--id", required=True)
    done.set_defaults(func=cmd_done)

    reopen = sub.add_parser("open", help="Reopen a completed todo")
    reopen.add_argument("--id", required=True)
    reopen.set_defaults(func=cmd_open)

    delete = sub.add_parser("delete", help="Delete a todo item")
    delete.add_argument("--id", required=True)
    delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
