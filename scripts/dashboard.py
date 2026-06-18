#!/usr/bin/env python3
"""kon session dashboard.

Serves a live dashboard of kon agent sessions stored in ~/.kon/projects/<repo-name>/sessions/.
Sessions are auto-refreshed every 3 seconds. Click any session to expand its log.

Usage:
    python3 scripts/dashboard.py            # http://localhost:9090
    python3 scripts/dashboard.py --port 9000
    python3 scripts/dashboard.py --open     # also opens browser automatically
    python3 scripts/dashboard.py --project /path/to/repo  # one project only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hooks"))
from _kon_paths import (  # noqa: E402
    iter_sessions_dirs,
    kon_data_dir,
    project_data_dir,
    resolve_project_path,
)

PROJECT_FILTER: str | None = None
_SESSION_FILES: dict[str, pathlib.Path] = {}

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>kon sessions</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: #0d1117; color: #e6edf3; padding: 32px; min-height: 100vh; }
h1   { font-size: 22px; margin-bottom: 20px; }
h1 small { color: #8b949e; font-size: 14px; font-weight: 400; margin-left: 10px; }
.tabs { display: flex; gap: 6px; margin-bottom: 20px; }
.tab { padding: 5px 14px; border-radius: 6px; font-size: 13px; cursor: pointer;
       background: transparent; border: 1px solid #30363d; color: #8b949e;
       transition: all .15s; }
.tab:hover  { border-color: #58a6ff; color: #e6edf3; }
.tab.active { background: #1f3a5f; border-color: #388bfd; color: #79c0ff; font-weight: 600; }
.count { font-size: 11px; background: #21262d; padding: 1px 5px;
         border-radius: 8px; margin-left: 4px; }
.empty { color: #8b949e; padding: 16px 0; font-size: 14px; }
.session { background: #161b22; border: 1px solid #30363d; border-radius: 10px;
           margin-bottom: 14px; overflow: hidden; transition: opacity .2s; }
.session.past { opacity: 0.6; }
.session.past:hover { opacity: 1; }
.hdr { padding: 18px 20px; display: flex; align-items: center; gap: 12px;
       cursor: pointer; user-select: none; min-height: 58px; }
.hdr:hover { background: #1c2128; }
.chevron { color: #484f58; font-size: 10px; flex-shrink: 0;
           transition: transform .15s; display: inline-block; }
.chevron.open { transform: rotate(90deg); }
.badge { padding: 3px 10px; border-radius: 10px; font-size: 12px;
         font-weight: 600; flex-shrink: 0; }
.badge.in_progress { background: #1158a0; color: #79c0ff; }
.badge.waiting     { background: rgba(210, 153, 34, 0.10); color: #d4a72c;
                     border: 1px solid rgba(210, 153, 34, 0.25); }
.badge.completed   { background: #1a4f2a; color: #56d364; }
.badge.blocked     { background: #5a1a1a; color: #f85149; }
.task  { flex: 1; min-width: 0; font-size: 15px; font-weight: 500; color: #e6edf3;
         overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project { color: #484f58; font-size: 11px; flex-shrink: 0; max-width: 140px;
           overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cmd   { color: #8b949e; font-size: 13px; flex-shrink: 0; }
.when  { color: #484f58; font-size: 12px; flex-shrink: 0; white-space: nowrap; }
.pipeline { display: flex; gap: 4px; align-items: center; flex-shrink: 0; }
.dot { width: 12px; height: 12px; border-radius: 50%; position: relative; cursor: default; }
.dot:hover::after { content: attr(data-label);
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  background: #1c2128; border: 1px solid #30363d; padding: 3px 7px;
  border-radius: 4px; font-size: 11px; white-space: nowrap;
  color: #e6edf3; z-index: 10; pointer-events: none; }
.dot.done    { background: #238636; }
.dot.active  { background: #1f6feb; box-shadow: 0 0 0 3px #388bfd33; }
.dot.waiting { background: rgba(210, 153, 34, 0.35);
               border: 1px solid rgba(210, 153, 34, 0.45); box-sizing: border-box; }
.dot.failed  { background: #da3633; }
.dot.pending { background: #30363d; }
.cur-agent { font-size: 14px; color: #8b949e; flex-shrink: 0; min-width: 80px; text-align: right; }
.close-btn { background: none; border: 1px solid #238636; cursor: pointer; color: #56d364;
             font-size: 13px; padding: 2px 8px; border-radius: 4px; flex-shrink: 0;
             line-height: 1; transition: all .15s; }
.close-btn:hover { background: #1a4f2a; }
.del-btn { background: none; border: none; cursor: pointer; color: #484f58;
           font-size: 14px; padding: 2px 4px; border-radius: 4px; flex-shrink: 0;
           line-height: 1; transition: color .15s; }
.del-btn:hover { color: #f85149; }
.log { border-top: 1px solid #21262d; display: none; max-height: 300px; overflow-y: auto; }
.log.open { display: block; }
.log-row { display: flex; gap: 10px; padding: 7px 16px; font-size: 12px;
           border-bottom: 1px solid #21262d; }
.log-row:last-child { border-bottom: none; }
.ts      { color: #484f58; flex-shrink: 0; font-family: monospace; font-size: 11px; }
.agent   { color: #e6edf3; flex-shrink: 0; width: 68px; }
.summary { color: #8b949e; }
</style>
</head>
<body>
<h1>🎸 kon sessions <small id="ts"></small></h1>
<div class="tabs">
  <button class="tab active" onclick="setTab('all')"   id="tab-all">All</button>
  <button class="tab"        onclick="setTab('active')" id="tab-active">Active</button>
  <button class="tab"        onclick="setTab('past')"   id="tab-past">Past</button>
</div>
<div id="root"></div>
<script>
const EM = {Azusa:'🎸',Jun:'📚',Mugi:'🍰',Yui:'🎶',Mio:'📝',Ritsu:'🥁',Sawako:'🧹',Nodoka:'📋'};
const showProject = __SHOW_PROJECT__;
const open_ids = new Set();
let currentTab = 'all';
let allSessions = [];

function fmtTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
function fmtWhen(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  return isToday
    ? d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
    : d.toLocaleDateString([], {month:'short',day:'numeric'}) + ' ' +
      d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}
function fmtProject(p) {
  if (!p) return '';
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

function setTab(tab) {
  currentTab = tab;
  ['all','active','past'].forEach(t => {
    document.getElementById('tab-'+t).classList.toggle('active', t === tab);
  });
  render(allSessions);
}

function renderSession(s) {
  const isPast  = s.status === 'completed' || s.status === 'blocked';
  const cur     = s.current_agent;
  const pend    = s.steps_pending   || [];
  const failed  = s.steps_failed    || [];
  const waiting = s.steps_waiting   || [];
  const done    = s.steps_completed || [];
  const all     = [...done, ...failed, ...waiting, ...(cur ? [cur] : []), ...pend];
  const dots    = all.map(a => {
    let cls;
    if (done.includes(a))    cls = 'done';
    else if (failed.includes(a))  cls = 'failed';
    else if (waiting.includes(a)) cls = 'waiting';
    else if (a === cur)      cls = (s.status === 'waiting' ? 'waiting' : 'active');
    else                     cls = 'pending';
    return `<div class="dot ${cls}" data-label="${EM[a]||''} ${a}"></div>`;
  }).join('');
  const curLabel = cur
    ? `${EM[cur]||''} ${cur}`
    : (s.status==='completed' ? '✓ done'
    : s.status==='waiting'   ? '⏸ waiting'
    : s.status==='blocked'   ? '✗ blocked' : '—');
  const isOpen   = open_ids.has(s.id);
  const canClose = s.status === 'in_progress' || s.status === 'waiting';
  const logRows  = (s.log||[]).map(e =>
    `<div class="log-row">
      <span class="ts">${fmtTime(e.ts)}</span>
      <span class="agent">${EM[e.agent]||''} ${e.agent}</span>
      <span class="summary">${e.summary}</span>
    </div>`).join('');
  const projectLabel = showProject && s.project_path
    ? `<span class="project" title="${s.project_path}">${fmtProject(s.project_path)}</span>`
    : '';
  return `
    <div class="session${isPast?' past':''}">
      <div class="hdr" onclick="toggle('${s.id}')">
        <span class="chevron${isOpen?' open':''}">▶</span>
        <span class="badge ${s.status}">${s.status.replace('_',' ')}</span>
        <span class="task" title="${s.task}">${s.task}</span>
        ${projectLabel}
        <span class="cmd">${s.command}</span>
        <div class="pipeline">${dots}</div>
        <span class="when">${fmtWhen(s.started_at)}</span>
        <span class="cur-agent">${curLabel}</span>
        ${canClose ? `<button class="close-btn" onclick="closeSession('${s.id}',event)" title="Mark as done">✓</button>` : ''}
        <button class="del-btn" onclick="deleteSession('${s.id}',${JSON.stringify(s.task)},event)" title="Delete session">🗑</button>
      </div>
      <div class="log${isOpen?' open':''}" id="log-${s.id}">
        ${logRows || '<div class="log-row"><span class="summary" style="color:#484f58">No log entries yet.</span></div>'}
      </div>
    </div>`;
}

function render(sessions) {
  const active = sessions.filter(s => s.status === 'in_progress' || s.status === 'waiting');
  const past   = sessions.filter(s => s.status === 'completed' || s.status === 'blocked');
  document.getElementById('tab-all').innerHTML    = `All <span class="count">${sessions.length}</span>`;
  document.getElementById('tab-active').innerHTML = `Active <span class="count">${active.length}</span>`;
  document.getElementById('tab-past').innerHTML   = `Past <span class="count">${past.length}</span>`;
  const filtered = currentTab === 'active' ? active : currentTab === 'past' ? past : sessions;
  const label = currentTab === 'active' ? 'No active sessions.' : currentTab === 'past' ? 'No past sessions yet.' : 'No sessions yet — run a kon command to get started.';
  document.getElementById('root').innerHTML = filtered.length
    ? filtered.map(renderSession).join('')
    : `<p class="empty">${label}</p>`;
}

function toggle(id) {
  if (open_ids.has(id)) open_ids.delete(id); else open_ids.add(id);
  document.getElementById('log-'+id).classList.toggle('open');
  const hdr = document.getElementById('log-'+id).previousElementSibling;
  hdr.querySelector('.chevron').classList.toggle('open');
}

async function closeSession(id, event) {
  event.stopPropagation();
  try {
    const r = await fetch('/sessions/' + id, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: 'completed'})
    });
    if (r.ok) {
      const s = allSessions.find(s => s.id === id);
      if (s) { s.status = 'completed'; s.current_agent = null; }
      render(allSessions);
    }
  } catch (_) {}
}

async function deleteSession(id, task, event) {
  event.stopPropagation();
  if (!confirm(`Delete session?\n\n"${task}"\n\nThis removes the session file and its summary.`)) return;
  try {
    const r = await fetch('/sessions/' + id, {method: 'DELETE'});
    if (r.ok) {
      allSessions = allSessions.filter(s => s.id !== id);
      open_ids.delete(id);
      render(allSessions);
    }
  } catch (_) {}
}

async function refresh() {
  try {
    allSessions = await (await fetch('/sessions')).json();
    document.getElementById('ts').textContent = 'refreshed ' + fmtTime(new Date().toISOString());
    render(allSessions);
  } catch (_) {}
}

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            show_project = "true" if PROJECT_FILTER is None else "false"
            html = _HTML.replace("__SHOW_PROJECT__", show_project)
            self._send(200, "text/html; charset=utf-8", html.encode())
        elif self.path == "/sessions":
            body = json.dumps(_load_sessions(), ensure_ascii=False).encode()
            self._send(200, "application/json", body)
        else:
            self._send(404, "text/plain", b"not found")

    def do_PATCH(self) -> None:
        if self.path.startswith("/sessions/"):
            session_id = self.path[len("/sessions/") :]
            if not re.fullmatch(r"[\w\-]+", session_id):
                self._send(400, "text/plain", b"invalid session id")
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            try:
                updates = json.loads(body)
            except json.JSONDecodeError:
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
        if self.path.startswith("/sessions/"):
            session_id = self.path[len("/sessions/") :]
            if not re.fullmatch(r"[\w\-]+", session_id):
                self._send(400, "text/plain", b"invalid session id")
                return
            target = _session_file(session_id)
            if target is None:
                self._send(404, "text/plain", b"session not found")
                return
            summary = target.parent / f"{session_id}-summary.md"
            deleted = []
            for path in (target, summary):
                if path.exists():
                    try:
                        path.unlink()
                        deleted.append(path.name)
                    except OSError:
                        pass
            if deleted:
                _SESSION_FILES.pop(session_id, None)
                self._send(200, "application/json", json.dumps({"deleted": deleted}).encode())
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


def _session_dirs() -> list[pathlib.Path]:
    if PROJECT_FILTER:
        return iter_sessions_dirs(PROJECT_FILTER)
    return iter_sessions_dirs()


def _session_file(session_id: str) -> pathlib.Path | None:
    if session_id in _SESSION_FILES:
        return _SESSION_FILES[session_id]
    for d in _session_dirs():
        path = d / f"{session_id}.json"
        if path.exists():
            return path
    return None


def _load_sessions() -> list[dict]:
    _SESSION_FILES.clear()
    sessions: list[dict] = []
    seen: set[str] = set()

    for directory in _session_dirs():
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            sid = data.get("id", path.stem)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="kon session dashboard")
    parser.add_argument("--port", type=int, default=9090, help="Port (default: 9090)")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
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
    if args.open:
        webbrowser.open(url)

    server = HTTPServer(("", args.port), _Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
