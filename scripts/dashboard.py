#!/usr/bin/env python3
"""kon session dashboard.

Serves a live dashboard of kon agent sessions stored in ~/.kon/projects/<repo-name>/sessions/
and project todo lists in <project>/.kon/todos.json.

Sessions and todos are auto-refreshed every 3 seconds. Click any session to expand its log.

Usage:
    python3 scripts/dashboard.py            # http://localhost:9090
    python3 scripts/dashboard.py --port 9000
    python3 scripts/dashboard.py --open     # also opens browser automatically
    python3 scripts/dashboard.py --project /path/to/repo  # one project only
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from _kon_paths import (  # noqa: E402
    iter_sessions_dirs,
    kon_data_dir,
    project_data_dir,
    resolve_project_path,
)
from _session_paths import all_session_delete_paths, iter_session_json_paths, resolve_session_json  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kon_todo  # noqa: E402

PROJECT_FILTER: str | None = None
_SESSION_FILES: dict[str, Path] = {}

_DASHBOARD_HTML_PATH = Path(__file__).resolve().parent / "dashboard.html"


def _load_dashboard_html() -> str:
    return _DASHBOARD_HTML_PATH.read_text(encoding="utf-8")


_HTML = _load_dashboard_html()


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict | None:
    """Read Content-Length bytes from handler.rfile; return parsed JSON or None on error."""
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            html = _HTML
            self._send(200, "text/html; charset=utf-8", html.encode())
        elif self.path == "/sessions":
            body = json.dumps(_load_sessions(), ensure_ascii=False).encode()
            self._send(200, "application/json", body)
        elif self.path == "/sessions/waiting":
            body = json.dumps(
                waiting_sessions_fifo(_load_sessions()),
                ensure_ascii=False,
            ).encode()
            self._send(200, "application/json", body)
        elif self.path == "/todos":
            body = json.dumps(
                kon_todo.load_all_todos(PROJECT_FILTER),
                ensure_ascii=False,
            ).encode()
            self._send(200, "application/json", body)
        else:
            self._send(404, "text/plain", b"not found")

    def do_PATCH(self) -> None:
        if self.path.startswith("/todos/"):
            todo_id = self.path[len("/todos/") :]
            if not re.fullmatch(r"[\w\-]+", todo_id):
                self._send(400, "text/plain", b"invalid todo id")
                return
            updates = _read_json_body(self)
            if updates is None:
                self._send(400, "text/plain", b"invalid JSON")
                return
            project_path = updates.get("project_path")
            status = updates.get("status")
            if not project_path or status not in ("open", "done"):
                self._send(400, "text/plain", b"project_path and status required")
                return
            try:
                item = kon_todo.set_todo_status(todo_id, status, project_path)
                self._send(200, "application/json", json.dumps(item, ensure_ascii=False).encode())
            except LookupError:
                self._send(404, "text/plain", b"todo not found")
            except (OSError, ValueError):
                self._send(500, "text/plain", b"write failed")
            return
        if self.path.startswith("/sessions/"):
            session_id = _path_id(self.path, "/sessions/")
            if session_id is None or not re.fullmatch(r"[\w\-]+", session_id):
                self._send(400, "text/plain", b"invalid session id")
                return
            updates = _read_json_body(self)
            if updates is None:
                self._send(400, "text/plain", b"invalid JSON")
                return
            target = _session_file(session_id)
            if target is None:
                self._send(404, "text/plain", b"session not found")
                return
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                data.update({k: v for k, v in updates.items() if k in ("status", "current_agent")})
                target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                self._send(200, "application/json", json.dumps({"ok": True}).encode())
            except (OSError, json.JSONDecodeError):
                self._send(500, "text/plain", b"write failed")
        else:
            self._send(404, "text/plain", b"not found")

    def do_DELETE(self) -> None:
        if self.path.startswith("/todos/"):
            todo_id = self.path[len("/todos/") :]
            if not re.fullmatch(r"[\w\-]+", todo_id):
                self._send(400, "text/plain", b"invalid todo id")
                return
            payload = _read_json_body(self)
            if payload is None:
                self._send(400, "text/plain", b"invalid JSON")
                return
            project_path = payload.get("project_path")
            if not project_path:
                self._send(400, "text/plain", b"project_path required")
                return
            try:
                deleted = kon_todo.delete_todo(todo_id, project_path)
                self._send(
                    200,
                    "application/json",
                    json.dumps({"deleted": deleted}, ensure_ascii=False).encode(),
                )
            except LookupError:
                self._send(404, "text/plain", b"todo not found")
            except OSError:
                self._send(500, "text/plain", b"write failed")
            return
        if self.path.startswith("/sessions/"):
            session_id = _path_id(self.path, "/sessions/")
            if session_id is None or not re.fullmatch(r"[\w\-]+", session_id):
                self._send(400, "text/plain", b"invalid session id")
                return
            deleted = delete_session(session_id)
            if deleted:
                self._send(
                    200,
                    "application/json",
                    json.dumps({"deleted": deleted}, ensure_ascii=False).encode(),
                )
            else:
                self._send(404, "text/plain", b"session not found")
        else:
            self._send(404, "text/plain", b"not found")

    def _send(self, status: int, ctype: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        pass


def _path_id(path: str, prefix: str) -> str | None:
    if not path.startswith(prefix):
        return None
    segment = path[len(prefix) :].split("?", 1)[0]
    return segment or None


def _session_dirs() -> list[Path]:
    if PROJECT_FILTER:
        return iter_sessions_dirs(PROJECT_FILTER)
    return iter_sessions_dirs()


def _session_file(session_id: str) -> Path | None:
    if session_id in _SESSION_FILES:
        return _SESSION_FILES[session_id]
    path = resolve_session_json(None, session_id)
    if path is not None:
        return path
    return None


def _session_related_paths(session_id: str, project_path: str | None = None) -> list[Path]:
    """All session artifacts to remove — one directory plus legacy scattered files."""
    return all_session_delete_paths(session_id, project_path)


def delete_session(session_id: str) -> list[str]:
    """Delete session artifacts from disk. Returns deleted path names."""
    target = _session_file(session_id)
    project_path: str | None = None
    if target is not None and target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            project_path = data.get("project_path")
        except (json.JSONDecodeError, OSError):
            pass

    deleted: list[str] = []
    for path in _session_related_paths(session_id, project_path):
        if not path.exists():
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            deleted.append(str(path))
        except OSError:
            continue

    if deleted:
        _SESSION_FILES.pop(session_id, None)
    return deleted


def is_user_waiting(data: dict) -> bool:
    """True when wait-for-user set a checkpoint (FIFO queue membership)."""
    if data.get("status") != "waiting":
        return False
    checkpoint = data.get("checkpoint") or {}
    return bool(checkpoint.get("ts"))


def waiting_sessions_fifo(sessions: list[dict]) -> list[dict]:
    """Sessions waiting for user input, oldest checkpoint first (FIFO)."""
    waiting = [s for s in sessions if is_user_waiting(s)]
    waiting.sort(
        key=lambda s: (str((s.get("checkpoint") or {}).get("ts") or ""), s.get("id") or "")
    )
    return waiting


def _load_sessions() -> list[dict]:
    _SESSION_FILES.clear()
    sessions: list[dict] = []
    seen: set[str] = set()

    for directory in _session_dirs():
        if not directory.exists():
            continue
        candidates: list[tuple[float, str, Path, dict]] = []
        for sid, path in iter_session_json_paths(directory):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            mtime = path.stat().st_mtime
            candidates.append((mtime, sid, path, data))
        for _mtime, sid, path, data in sorted(candidates, key=lambda row: row[0], reverse=True):
            if sid in seen:
                continue
            if PROJECT_FILTER:
                project = data.get("project_path")
                meta_path = None
                meta = directory.parent / "meta.json"
                if meta.is_file():
                    try:
                        meta_path = json.loads(meta.read_text(encoding="utf-8")).get("project_path")
                    except (json.JSONDecodeError, OSError):
                        pass
                if project != PROJECT_FILTER and meta_path != PROJECT_FILTER:
                    continue
            seen.add(sid)
            _SESSION_FILES[sid] = path
            sessions.append(data)

    return sessions


def _pids_on_port(port: int) -> list[int]:
    try:
        out = subprocess.check_output(
            ["lsof", "-t", "-i", f":{port}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    pids: list[int] = []
    for line in out.strip().splitlines():
        try:
            pids.append(int(line.strip()))
        except ValueError:
            continue
    return pids


def _process_command(pid: int) -> str:
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "command="],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def kill_kon_dashboard_on_port(port: int) -> list[int]:
    """Stop kon dashboard.py listeners on ``port``. Returns killed PIDs."""
    killed: list[int] = []
    for pid in _pids_on_port(port):
        if "dashboard.py" not in _process_command(pid):
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            killed.append(pid)
        except ProcessLookupError:
            continue
    return killed


def main() -> None:
    parser = argparse.ArgumentParser(description="kon session dashboard")
    parser.add_argument("--port", type=int, default=9090, help="Port (default: 9090)")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Stop any kon dashboard already on this port, then start fresh",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Only show sessions for this project",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Deprecated alias for --project",
    )
    args = parser.parse_args()

    global PROJECT_FILTER
    project_arg = args.project or args.dir
    if project_arg:
        PROJECT_FILTER = str(resolve_project_path(project_arg))

    url = f"http://localhost:{args.port}"
    print(f"kon dashboard → {url}")
    print(f"Watching: {kon_data_dir() / 'projects'}/*/sessions")
    if PROJECT_FILTER:
        print(f"Project:  {project_data_dir(PROJECT_FILTER)}")
    else:
        print(f"Data dir: {kon_data_dir()}")
    print("Ctrl+C to stop.\n")

    # --open / --restart must load fresh HTML; a stale listener on :9090 exits 0 silently
    # unless we stop it first (common footgun after code changes).
    if args.restart or args.open:
        killed = kill_kon_dashboard_on_port(args.port)
        if killed:
            print(f"Stopped previous dashboard (pid(s): {', '.join(map(str, killed))})")
            time.sleep(0.3)

    if args.open:
        webbrowser.open(url)

    try:
        server = HTTPServer(("", args.port), _Handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            # Port taken — treat as success (autostart hook, second manual launch).
            print(
                f"Port {args.port} is already in use — another dashboard may be running."
                f" Run: python3 scripts/dashboard.py --restart --port {args.port}"
                + (" --open" if args.open else ""),
            )
            sys.exit(0)
        raise
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
