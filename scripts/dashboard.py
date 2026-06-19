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
import json
import re
import shutil
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from _kon_paths import (  # noqa: E402
    iter_sessions_dirs,
    kon_data_dir,
    project_data_dir,
    project_kon_dir,
    resolve_project_path,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kon_todo  # noqa: E402

PROJECT_FILTER: str | None = None
_SESSION_FILES: dict[str, Path] = {}

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>kon dashboard</title>
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
.project-badge { padding: 2px 9px; border-radius: 6px; font-size: 11px; font-weight: 600;
                 flex-shrink: 0; max-width: 160px; overflow: hidden;
                 text-overflow: ellipsis; white-space: nowrap;
                 background: #21262d; border: 1px solid #388bfd44; color: #79c0ff; }
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
.view-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.view-tab { padding: 6px 16px; border-radius: 8px; font-size: 14px; cursor: pointer;
            background: transparent; border: 1px solid #30363d; color: #8b949e; }
.view-tab.active { background: #21262d; border-color: #58a6ff; color: #79c0ff; font-weight: 600; }
.todo { background: #161b22; border: 1px solid #30363d; border-radius: 10px;
        margin-bottom: 10px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; }
.todo.done { opacity: 0.65; }
.todo-text { flex: 1; min-width: 0; font-size: 14px; line-height: 1.4; }
.todo.done .todo-text { text-decoration: line-through; color: #8b949e; }
.todo-meta { color: #484f58; font-size: 11px; flex-shrink: 0; white-space: nowrap; }
.todo-id { color: #484f58; font-size: 11px; font-family: monospace; flex-shrink: 0; }
.todo-actions { display: flex; gap: 6px; flex-shrink: 0; }
.todo-btn { background: none; border: 1px solid #30363d; cursor: pointer; color: #8b949e;
            font-size: 12px; padding: 2px 8px; border-radius: 4px; line-height: 1.2; }
.todo-btn:hover { border-color: #58a6ff; color: #e6edf3; }
.todo-btn.done-btn { border-color: #238636; color: #56d364; }
.todo-btn.done-btn:hover { background: #1a4f2a; }
.todo-btn.del-btn:hover { border-color: #f85149; color: #f85149; }
.panel { display: none; }
.panel.active { display: block; }
</style>
</head>
<body>
<h1>🎸 kon dashboard <small id="ts"></small></h1>
<div class="view-tabs">
  <button class="view-tab active" onclick="setView('sessions')" id="view-sessions">Sessions</button>
  <button class="view-tab" onclick="setView('todos')" id="view-todos">Todos</button>
</div>
<div id="sessions-panel" class="panel active">
<div class="tabs">
  <button class="tab active" onclick="setTab('all')"   id="tab-all">All</button>
  <button class="tab"        onclick="setTab('active')" id="tab-active">Active</button>
  <button class="tab"        onclick="setTab('past')"   id="tab-past">Past</button>
</div>
<div id="root"></div>
</div>
<div id="todos-panel" class="panel">
<div class="tabs">
  <button class="tab active" onclick="setTodoTab('open')" id="todo-tab-open">Open</button>
  <button class="tab" onclick="setTodoTab('done')" id="todo-tab-done">Done</button>
  <button class="tab" onclick="setTodoTab('all')" id="todo-tab-all">All</button>
</div>
<div id="todo-root"></div>
</div>
<script>
const EM = {Azusa:'🎸',Jun:'📚',Mugi:'🍰',Yui:'🎶',Mio:'📝',Ritsu:'🥁',Sawako:'🧹',Nodoka:'📋'};
const open_ids = new Set();
let currentTab = 'all';
let currentView = 'sessions';
let currentTodoTab = 'open';
let allSessions = [];
let allTodos = [];

function setView(view) {
  currentView = view;
  document.getElementById('view-sessions').classList.toggle('active', view === 'sessions');
  document.getElementById('view-todos').classList.toggle('active', view === 'todos');
  document.getElementById('sessions-panel').classList.toggle('active', view === 'sessions');
  document.getElementById('todos-panel').classList.toggle('active', view === 'todos');
  refresh();
}

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

function projectBadge(path) {
  if (!path) return '';
  const name = fmtProject(path);
  return `<span class="project-badge" title="${path}">${name}</span>`;
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
  let dots;
  if (s.command === '/kon:begin') {
    const turns = s.turns || [];
    dots = turns.map((t, i) => {
      const isLast = i === turns.length - 1;
      const cls = (isLast && cur) ? 'active' : 'done';
      const label = `Q${t.n}: ${t.summary}`;
      return `<div class="dot ${cls}" data-label="${label}"></div>`;
    }).join('');
  } else {
    const pend    = s.steps_pending   || [];
    const failed  = s.steps_failed    || [];
    const waiting = s.steps_waiting   || [];
    const done    = s.steps_completed || [];
    const all     = [...done, ...failed, ...waiting, ...(cur ? [cur] : []), ...pend];
    dots = all.map(a => {
      let cls;
      if (done.includes(a))    cls = 'done';
      else if (failed.includes(a))  cls = 'failed';
      else if (waiting.includes(a)) cls = 'waiting';
      else if (a === cur)      cls = (s.status === 'waiting' ? 'waiting' : 'active');
      else                     cls = 'pending';
      return `<div class="dot ${cls}" data-label="${EM[a]||''} ${a}"></div>`;
    }).join('');
  }
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
  const projectLabel = projectBadge(s.project_path);
  return `
    <div class="session${isPast?' past':''}" data-session-id="${s.id}">
      <div class="hdr">
        <span class="chevron${isOpen?' open':''}">▶</span>
        <span class="badge ${s.status}">${s.status.replace('_',' ')}</span>
        ${projectLabel}
        <span class="task" title="${s.task}">${s.task}</span>
        <span class="cmd">${s.command}</span>
        <div class="pipeline">${dots}</div>
        <span class="when">${fmtWhen(s.started_at)}</span>
        <span class="cur-agent">${curLabel}</span>
        ${canClose ? `<button type="button" class="close-btn" title="Mark as done">✓</button>` : ''}
        <button type="button" class="del-btn" title="Delete session">🗑</button>
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
  const session = document.querySelector('.session[data-session-id="' + id + '"]');
  if (!session) return;
  const log = session.querySelector('.log');
  const chevron = session.querySelector('.chevron');
  if (log) log.classList.toggle('open');
  if (chevron) chevron.classList.toggle('open');
}

async function closeSession(id, event) {
  if (event) event.stopPropagation();
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

async function deleteSession(id, event) {
  if (event) event.stopPropagation();
  const s = allSessions.find(x => x.id === id);
  const task = s ? s.task : id;
  if (!confirm(`Delete session?\\n\\n"${task}"\\n\\nThis removes session files from disk.`)) return;
  try {
    const r = await fetch('/sessions/' + encodeURIComponent(id), {method: 'DELETE'});
    if (r.ok) {
      allSessions = allSessions.filter(s => s.id !== id);
      open_ids.delete(id);
      render(allSessions);
    } else {
      const msg = await r.text();
      alert('Delete failed (' + r.status + '): ' + msg);
    }
  } catch (err) {
    alert('Delete failed: ' + err);
  }
}

document.getElementById('root').addEventListener('click', (e) => {
  const delBtn = e.target.closest('.del-btn');
  if (delBtn) {
    e.stopPropagation();
    const id = delBtn.closest('.session')?.dataset.sessionId;
    if (id) deleteSession(id, e);
    return;
  }
  const closeBtn = e.target.closest('.close-btn');
  if (closeBtn) {
    e.stopPropagation();
    const id = closeBtn.closest('.session')?.dataset.sessionId;
    if (id) closeSession(id, e);
    return;
  }
  const hdr = e.target.closest('.hdr');
  if (hdr && !e.target.closest('button')) {
    const id = hdr.closest('.session')?.dataset.sessionId;
    if (id) toggle(id);
  }
});

function setTodoTab(tab) {
  currentTodoTab = tab;
  ['open','done','all'].forEach(t => {
    document.getElementById('todo-tab-'+t).classList.toggle('active', t === tab);
  });
  renderTodos(allTodos);
}

function renderTodo(t) {
  const isDone = t.status === 'done';
  const projectLabel = projectBadge(t.project_path);
  return `
    <div class="todo${isDone ? ' done' : ''}">
      ${projectLabel}
      <div class="todo-text">${t.text}</div>
      <span class="todo-id" title="${t.id}">${t.id.slice(-12)}</span>
      <span class="todo-meta">${fmtWhen(t.created_at)}</span>
      <div class="todo-actions">
        ${!isDone ? `<button class="todo-btn done-btn" onclick="markTodoDone('${t.id}',${JSON.stringify(t.project_path)},event)">✓</button>` : `<button class="todo-btn" onclick="reopenTodo('${t.id}',${JSON.stringify(t.project_path)},event)">↩</button>`}
        <button class="todo-btn del-btn" onclick="deleteTodo('${t.id}',${JSON.stringify(t.project_path)},${JSON.stringify(t.text)},event)">🗑</button>
      </div>
    </div>`;
}

function renderTodos(todos) {
  const open = todos.filter(t => t.status === 'open');
  const done = todos.filter(t => t.status === 'done');
  document.getElementById('todo-tab-open').innerHTML = `Open <span class="count">${open.length}</span>`;
  document.getElementById('todo-tab-done').innerHTML = `Done <span class="count">${done.length}</span>`;
  document.getElementById('todo-tab-all').innerHTML = `All <span class="count">${todos.length}</span>`;
  const filtered = currentTodoTab === 'open' ? open : currentTodoTab === 'done' ? done : todos;
  const label = currentTodoTab === 'open'
    ? 'No open todos — add one with /kon:todo <task>.'
    : currentTodoTab === 'done' ? 'No completed todos yet.' : 'No todos yet — add one with /kon:todo <task>.';
  document.getElementById('todo-root').innerHTML = filtered.length
    ? filtered.map(renderTodo).join('')
    : `<p class="empty">${label}</p>`;
}

async function markTodoDone(id, projectPath, event) {
  event.stopPropagation();
  try {
    const r = await fetch('/todos/' + id, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: 'done', project_path: projectPath})
    });
    if (r.ok) refresh();
  } catch (_) {}
}

async function reopenTodo(id, projectPath, event) {
  event.stopPropagation();
  try {
    const r = await fetch('/todos/' + id, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: 'open', project_path: projectPath})
    });
    if (r.ok) refresh();
  } catch (_) {}
}

async function deleteTodo(id, projectPath, text, event) {
  event.stopPropagation();
  if (!confirm(`Delete todo?\n\n"${text}"`)) return;
  try {
    const r = await fetch('/todos/' + id, {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({project_path: projectPath})
    });
    if (r.ok) refresh();
  } catch (_) {}
}

async function refresh() {
  try {
    const [sessionsResp, todosResp] = await Promise.all([
      fetch('/sessions'),
      fetch('/todos'),
    ]);
    allSessions = await sessionsResp.json();
    allTodos = await todosResp.json();
    document.getElementById('ts').textContent = 'refreshed ' + fmtTime(new Date().toISOString());
    render(allSessions);
    renderTodos(allTodos);
  } catch (_) {}
}

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""


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
    for directory in _session_dirs():
        path = directory / f"{session_id}.json"
        if path.is_file():
            return path
    return None


def _session_related_paths(session_id: str, project_path: str | None = None) -> list[Path]:
    """All session artifacts to remove: json, summary, optional legacy copies, session dir."""
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            paths.append(path)

    canonical = _session_file(session_id)
    if canonical is not None:
        add(canonical)
        add(canonical.parent / f"{session_id}-summary.md")
        session_dir = canonical.parent / session_id
        if session_dir.is_dir():
            add(session_dir)

    for directory in _session_dirs():
        add(directory / f"{session_id}.json")
        add(directory / f"{session_id}-summary.md")
        add(directory / session_id)

    if project_path:
        legacy_sessions = project_kon_dir(project_path) / "sessions"
        add(legacy_sessions / f"{session_id}.json")
        add(legacy_sessions / f"{session_id}-summary.md")
        add(legacy_sessions / session_id)

    return paths


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
