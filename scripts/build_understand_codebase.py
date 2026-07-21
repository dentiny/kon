#!/usr/bin/env python3
"""Build interactive HTML study pack from /kon:understand-codebase session artifacts.

Reads:
  sessions/<id>/understand-guide.md
  sessions/<id>/understand-study.json

Writes:
  sessions/<id>/understand-guide.html   (primary — clickable terms/diagrams + side panel)
  sessions/<id>/understand-study.html   (flashcards + quiz)
  sessions/<id>/understand-guide.pdf    (optional — when pandoc + LaTeX available)

Usage:
  python3 scripts/build_understand_codebase.py --id <session-id>
  python3 scripts/build_understand_codebase.py --session-dir /path/to/session
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from _session_paths import resolve_session_json, session_dir  # noqa: E402

GUIDE_MD = "understand-guide.md"
STUDY_JSON = "understand-study.json"
GUIDE_HTML = "understand-guide.html"
GUIDE_PDF = "understand-guide.pdf"
STUDY_HTML = "understand-study.html"

_SOURCE_EXT = r"(?:py|md|json|sh|yaml|yml|tsx?|jsx?|rs|go|toml|mdc)"
_PATH_LINE_RE = re.compile(
    rf"(?P<path>[\w./-]+\.{_SOURCE_EXT})(?::(?P<line>\d+)(?:-(?P<end>\d+))?)?"
)
_MD_LINK_REF_RE = re.compile(
    rf"\[([^\]]*)\]\((?P<path>[\w./-]+\.{_SOURCE_EXT}):(?P<line>\d+)(?:-(?P<end>\d+))?\)"
)
_BACKTICK_REF_RE = re.compile(
    rf"`(?P<path>[\w./-]+\.{_SOURCE_EXT}):(?P<line>\d+)(?:-(?P<end>\d+))?`"
)
_FENCE_CITATION_RE = re.compile(
    rf"^```(?P<start>\d+):(?P<end>\d+):(?P<path>[\w./-]+\.{_SOURCE_EXT})\s*$"
)


def _project_root_from_session(session_directory: Path) -> Path | None:
    session_json = session_directory / "session.json"
    if not session_json.is_file():
        return None
    try:
        data = json.loads(session_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    raw = data.get("project_path")
    if not raw:
        return None
    path = Path(str(raw)).expanduser()
    return path.resolve() if path.is_dir() else None


def ide_open_url(project_root: Path, rel_path: str, line: int) -> str:
    """Open file at line in VS Code / Cursor."""
    abs_path = (project_root / rel_path).resolve()
    return f"vscode://file/{abs_path}:{line}:1"


def _read_snippet(project_root: Path, rel_path: str, start: int, end: int) -> str | None:
    source = (project_root / rel_path).resolve()
    if not source.is_file():
        return None
    try:
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if start < 1 or start > len(lines):
        return None
    end = min(end, len(lines))
    return "\n".join(lines[start - 1 : end])


def enrich_markdown_snippets(md: str, project_root: Path | None) -> str:
    """Insert reference code fences after Source lines when Jun omitted the snippet."""
    if project_root is None:
        return md
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        match = _BACKTICK_REF_RE.search(line) or _MD_LINK_REF_RE.search(line)
        if match and "Reference code" not in line:
            path = match.group("path")
            start = int(match.group("line"))
            end = int(match.group("end") or start)
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            has_fence = j < len(lines) and lines[j].strip().startswith("```")
            if not has_fence:
                snippet = _read_snippet(project_root, path, start, end)
                if snippet:
                    out.append("")
                    out.append(f"```{start}:{end}:{path}")
                    out.append(snippet)
                    out.append("```")
        i += 1
    return "\n".join(out)


def linkify_markdown_refs(md: str, project_root: Path | None) -> str:
    """Turn path:line markdown links into vscode:// URLs for PDF/HTML."""
    if project_root is None:
        return md

    def md_link_repl(match: re.Match[str]) -> str:
        label, path, line_s, end_s = (
            match.group(1),
            match.group("path"),
            match.group("line"),
            match.group("end"),
        )
        line = int(line_s)
        display = label.strip() or f"{path}:{line}" + (f"-{end_s}" if end_s else "")
        url = ide_open_url(project_root, path, line)
        return f"[{display}]({url})"

    parts: list[str] = []
    in_fence = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            parts.append(line)
            continue
        if in_fence:
            parts.append(line)
            continue
        line = _MD_LINK_REF_RE.sub(md_link_repl, line)

        def backtick_repl(m: re.Match[str]) -> str:
            path, line_s, end_s = m.group("path"), m.group("line"), m.group("end")
            line = int(line_s)
            label = f"{path}:{line}" + (f"-{end_s}" if end_s else "")
            return f"[`{label}`]({ide_open_url(project_root, path, line)})"

        line = _BACKTICK_REF_RE.sub(backtick_repl, line)
        parts.append(line)
    return "\n".join(parts)


def linkify_html_refs(content: str, project_root: Path | None) -> str:
    """Add clickable IDE links to path:line mentions in generated HTML."""
    if project_root is None:
        return content

    def repl(match: re.Match[str]) -> str:
        path, line_s, end_s = match.group("path"), match.group("line"), match.group("end")
        if not line_s:
            return match.group(0)
        line = int(line_s)
        label = f"{path}:{line}" + (f"-{end_s}" if end_s else "")
        url = html.escape(ide_open_url(project_root, path, line), quote=True)
        return f'<a class="code-ref" href="{url}">{html.escape(label)}</a>'

    # Inside <code> tags
    def code_repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        linked = _PATH_LINE_RE.sub(repl, inner)
        if linked == inner:
            return match.group(0)
        return f"<code>{linked}</code>"

    content = re.sub(r"<code>([^<]+)</code>", code_repl, content)
    return content


_STUDY_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       background: #0d1117; color: #e6edf3; line-height: 1.5; }
header { padding: 24px 32px; border-bottom: 1px solid #30363d; }
h1 { font-size: 22px; margin-bottom: 8px; }
.tabs { display: flex; gap: 8px; padding: 16px 32px; border-bottom: 1px solid #21262d; }
.tab { padding: 8px 16px; border-radius: 8px; border: 1px solid #30363d;
       background: transparent; color: #8b949e; cursor: pointer; font-size: 14px; }
.tab.active { background: #21262d; border-color: #58a6ff; color: #79c0ff; font-weight: 600; }
main { max-width: 720px; margin: 0 auto; padding: 24px 32px 48px; }
.panel { display: none; }
.panel.active { display: block; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 12px;
        padding: 28px; min-height: 200px; cursor: pointer; user-select: none;
        display: flex; align-items: center; justify-content: center; text-align: center;
        font-size: 18px; transition: border-color .15s; }
.card:hover { border-color: #58a6ff; }
.card.back { color: #8b949e; font-size: 16px; }
.meta { display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 16px; color: #8b949e; font-size: 13px; flex-wrap: wrap; gap: 8px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 999px;
       background: #21262d; border: 1px solid #30363d; margin-left: 4px; }
.controls { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
button { padding: 8px 14px; border-radius: 8px; border: 1px solid #30363d;
         background: #21262d; color: #e6edf3; cursor: pointer; font-size: 14px; }
button:hover { border-color: #58a6ff; }
button.primary { background: #1f3a5f; border-color: #388bfd; color: #79c0ff; }
.q-text { font-size: 18px; margin-bottom: 20px; font-weight: 500; }
.choices { display: flex; flex-direction: column; gap: 10px; }
.choice { text-align: left; padding: 12px 16px; border-radius: 8px;
          border: 1px solid #30363d; background: #161b22; cursor: pointer; }
.choice:hover { border-color: #58a6ff; }
.choice.correct { border-color: #238636; background: #1a4f2a; }
.choice.wrong { border-color: #da3633; background: #5a1a1a; }
.choice.disabled { pointer-events: none; opacity: 0.85; }
.explanation { margin-top: 16px; padding: 12px; border-radius: 8px;
               background: #21262d; color: #8b949e; font-size: 14px; }
.snippet { margin-top: 12px; padding: 12px; border-radius: 8px; font-size: 12px;
           font-family: ui-monospace, monospace; background: #0d1117; color: #e6edf3;
           border: 1px solid #30363d; overflow-x: auto; white-space: pre-wrap; text-align: left; }
.refs { margin-top: 10px; font-size: 12px; }
.refs a { color: #79c0ff; text-decoration: none; }
.refs a:hover { text-decoration: underline; }
.card-back-wrap { width: 100%; text-align: left; }
.score { font-size: 20px; font-weight: 600; margin: 16px 0; color: #79c0ff; }
.filter { margin-bottom: 12px; }
select { background: #21262d; color: #e6edf3; border: 1px solid #30363d;
         padding: 6px 10px; border-radius: 6px; }
</style>
</head>
<body>
<header><h1>__TITLE__</h1><p style="color:#8b949e;font-size:14px">Flashcards & quiz — /kon:understand-codebase</p></header>
<div class="tabs">
  <button class="tab active" data-panel="flashcards">Flashcards</button>
  <button class="tab" data-panel="quiz">Quiz</button>
</div>
<main>
  <section id="flashcards" class="panel active">
    <div class="filter">
      <label>Filter: <select id="fc-filter">
        <option value="all">All</option>
        <option value="concept">Concept</option>
        <option value="implementation">Implementation</option>
      </select></label>
    </div>
    <div class="meta"><span id="fc-progress"></span><span id="fc-tags"></span></div>
    <div id="fc-card" class="card">Loading…</div>
    <div class="controls">
      <button type="button" id="fc-prev">← Prev</button>
      <button type="button" id="fc-flip">Flip</button>
      <button type="button" id="fc-next">Next →</button>
      <button type="button" id="fc-shuffle">Shuffle</button>
    </div>
  </section>
  <section id="quiz" class="panel">
    <div class="meta"><span id="qz-progress"></span></div>
    <div id="qz-body"></div>
    <div class="controls">
      <button type="button" id="qz-next" class="primary" style="display:none">Next →</button>
      <button type="button" id="qz-restart" style="display:none">Restart quiz</button>
    </div>
  </section>
</main>
<script>
const DATA = __DATA_JSON__;
const PROJECT_ROOT = DATA.project_path || null;

function ideUrl(path, line) {
  if (!PROJECT_ROOT || !path || !line) return '#';
  const abs = PROJECT_ROOT.replace(/\\/$/, '') + '/' + path.replace(/^\\/+/, '');
  return 'vscode://file/' + abs + ':' + line + ':1';
}

function refLabel(r) {
  return r.path + ':' + r.line + (r.endLine ? '-' + r.endLine : '');
}

function renderRefs(refs) {
  if (!refs || !refs.length) return '';
  return '<div class="refs">' + refs.map(r =>
    '<a href="' + ideUrl(r.path, r.line) + '" target="_blank" rel="noopener">' + refLabel(r) + '</a>'
  ).join(' · ') + '</div>';
}

function renderCode(code) {
  if (!code) return '';
  return '<pre class="snippet">' + code.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</pre>';
}

const cards = DATA.flashcards || [];
let fcList = [...cards];
let fcIdx = 0;
let fcFlipped = false;

function fcFiltered() {
  const f = document.getElementById('fc-filter').value;
  if (f === 'all') return fcList;
  return fcList.filter(c => (c.tags || []).includes(f));
}

function renderFc() {
  const list = fcFiltered();
  if (!list.length) {
    document.getElementById('fc-card').textContent = 'No flashcards match filter.';
    return;
  }
  fcIdx = Math.min(fcIdx, list.length - 1);
  const c = list[fcIdx];
  const el = document.getElementById('fc-card');
  el.className = 'card' + (fcFlipped ? ' back' : '');
  if (fcFlipped) {
    el.innerHTML = '<div class="card-back-wrap"><div>' + c.back + '</div>'
      + renderRefs(c.refs) + renderCode(c.code) + '</div>';
    el.style.cursor = 'default';
  } else {
    el.textContent = c.front;
    el.style.cursor = 'pointer';
  }
  document.getElementById('fc-progress').textContent = (fcIdx + 1) + ' / ' + list.length;
  document.getElementById('fc-tags').innerHTML = (c.tags || []).map(t =>
    '<span class="tag">' + t + '</span>').join('');
}

document.getElementById('fc-card').onclick = () => { fcFlipped = !fcFlipped; renderFc(); };
document.getElementById('fc-flip').onclick = () => { fcFlipped = !fcFlipped; renderFc(); };
document.getElementById('fc-prev').onclick = () => {
  fcFlipped = false; fcIdx = (fcIdx - 1 + fcFiltered().length) % fcFiltered().length; renderFc();
};
document.getElementById('fc-next').onclick = () => {
  fcFlipped = false; fcIdx = (fcIdx + 1) % fcFiltered().length; renderFc();
};
document.getElementById('fc-shuffle').onclick = () => {
  fcList = fcList.sort(() => Math.random() - 0.5); fcIdx = 0; fcFlipped = false; renderFc();
};
document.getElementById('fc-filter').onchange = () => { fcIdx = 0; fcFlipped = false; renderFc(); };

const quiz = DATA.quiz || [];
let qIdx = 0;
let qScore = 0;
let qDone = false;

function renderQuiz() {
  const body = document.getElementById('qz-body');
  document.getElementById('qz-next').style.display = 'none';
  document.getElementById('qz-restart').style.display = qDone ? 'inline-block' : 'none';
  if (qDone) {
    body.innerHTML = '<div class="score">Score: ' + qScore + ' / ' + quiz.length + '</div>' +
      '<p style="color:#8b949e">Review flashcards for missed topics.</p>';
    return;
  }
  const q = quiz[qIdx];
  document.getElementById('qz-progress').textContent = 'Question ' + (qIdx + 1) + ' / ' + quiz.length;
  let html = '<div class="q-text">' + q.question + '</div><div class="choices">';
  q.choices.forEach((ch, i) => {
    html += '<div class="choice" data-i="' + i + '">' + ch + '</div>';
  });
  html += '</div><div id="qz-explain" class="explanation" style="display:none"></div>';
  body.innerHTML = html;
  body.querySelectorAll('.choice').forEach(el => {
    el.onclick = () => {
      if (body.querySelector('.choice.disabled')) return;
      const pick = +el.dataset.i;
      const correct = pick === q.answer;
      if (correct) qScore++;
      body.querySelectorAll('.choice').forEach(c => {
        c.classList.add('disabled');
        if (+c.dataset.i === q.answer) c.classList.add('correct');
        else if (+c.dataset.i === pick) c.classList.add('wrong');
      });
      const ex = document.getElementById('qz-explain');
      ex.style.display = 'block';
      ex.innerHTML = (q.explanation || (correct ? 'Correct.' : 'Incorrect.'))
        + renderRefs(q.refs) + renderCode(q.code);
      document.getElementById('qz-next').style.display = 'inline-block';
    };
  });
}

document.getElementById('qz-next').onclick = () => {
  qIdx++;
  if (qIdx >= quiz.length) qDone = true;
  renderQuiz();
};
document.getElementById('qz-restart').onclick = () => {
  qIdx = 0; qScore = 0; qDone = false; renderQuiz();
};

document.querySelectorAll('.tab').forEach(tab => {
  tab.onclick = () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.panel).classList.add('active');
  };
});

renderFc();
renderQuiz();
</script>
</body>
</html>
"""

_GUIDE_HTML_WRAP = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
:root {
  --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
  --muted: #8b949e; --accent: #58a6ff; --accent-soft: #1f3a5f;
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
}
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 360px; min-height: 100vh; }
@media (max-width: 960px) {
  .layout { grid-template-columns: 1fr; }
  .aside { position: fixed; inset: auto 0 0 0; max-height: 55vh; z-index: 20;
           border-left: none; border-top: 1px solid var(--border);
           transform: translateY(100%); transition: transform .2s; }
  .aside.open { transform: translateY(0); }
  .aside-backdrop { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 19; }
  .aside-backdrop.open { display: block; }
}
.main { padding: 28px 32px 80px; max-width: 880px; }
.aside {
  border-left: 1px solid var(--border); background: var(--panel);
  padding: 20px 20px 32px; position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.aside-empty { color: var(--muted); font-size: 14px; }
.aside h2 { font-size: 18px; margin: 0 0 12px; }
.aside .label { font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
                color: var(--muted); margin: 16px 0 4px; }
.aside .value { font-size: 14px; }
.aside pre { background: #0d1117; border: 1px solid var(--border); border-radius: 8px;
             padding: 12px; overflow-x: auto; font-size: 12px; white-space: pre-wrap; }
.aside .close { float: right; border: 1px solid var(--border); background: transparent;
                color: var(--muted); border-radius: 6px; cursor: pointer; padding: 2px 8px; }
.hint { color: var(--muted); font-size: 13px; margin: 0 0 16px; }
.term-index { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 20px; }
.term-chip, button.term, h3.term-heading {
  cursor: pointer; border: 1px solid var(--border); background: #21262d; color: #79c0ff;
  border-radius: 999px; padding: 4px 10px; font-size: 12px;
}
h3.term-heading {
  display: inline-block; border-radius: 8px; padding: 6px 10px; font-size: 18px;
  margin: 20px 0 8px; color: var(--text); background: transparent;
}
h3.term-heading:hover, .term-chip:hover, button.term:hover,
.mermaid .node { outline: none; }
h3.term-heading:hover, .term-chip:hover, button.term:hover {
  border-color: var(--accent); background: var(--accent-soft);
}
button.term { font: inherit; display: inline; padding: 0 4px; border-radius: 4px; }
.mermaid { margin: 16px 0; cursor: default; }
.mermaid .node { cursor: pointer; }
.mermaid .node:hover rect, .mermaid .node:hover polygon, .mermaid .node:hover circle {
  stroke: var(--accent) !important; stroke-width: 2px !important;
}
h1 { font-size: 28px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
h2 { font-size: 22px; margin-top: 32px; }
h3 { font-size: 18px; margin-top: 24px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
th, td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
th { background: #21262d; }
code { background: #21262d; padding: 2px 6px; border-radius: 4px; font-size: 90%; }
pre { background: #161b22; padding: 16px; overflow-x: auto; border-radius: 8px;
      border-left: 3px solid var(--accent); }
pre code { background: none; padding: 0; }
a, a.code-ref { color: #79c0ff; text-decoration: none; }
a:hover, a.code-ref:hover { text-decoration: underline; }
@media print {
  .layout { display: block; }
  .aside, .hint, .term-index, .aside-backdrop { display: none !important; }
  .main { max-width: none; color: #000; background: #fff; }
  body { background: #fff; color: #000; }
}
</style>
</head>
<body>
<div class="aside-backdrop" id="aside-backdrop"></div>
<div class="layout">
  <main class="main">
    <p class="hint">Click a <strong>term</strong>, glossary heading, or <strong>diagram node</strong>
    to open details in the side panel.</p>
    <div class="term-index" id="term-index"></div>
    __BODY__
  </main>
  <aside class="aside" id="aside" aria-live="polite">
    <button type="button" class="close" id="aside-close" hidden>Close</button>
    <div id="aside-body" class="aside-empty">Select a term or diagram node to see details here.</div>
  </aside>
</div>
<script>
const GLOSSARY = __GLOSSARY_JSON__;
const BY_ID = Object.fromEntries(GLOSSARY.map(e => [e.id, e]));
const BY_TITLE = Object.fromEntries(GLOSSARY.map(e => [e.title.toLowerCase(), e]));

function escapeHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function openEntry(entry) {
  if (!entry) return;
  const aside = document.getElementById('aside');
  const body = document.getElementById('aside-body');
  const close = document.getElementById('aside-close');
  const backdrop = document.getElementById('aside-backdrop');
  close.hidden = false;
  aside.classList.add('open');
  backdrop.classList.add('open');
  let html = '<h2>' + escapeHtml(entry.title) + '</h2>';
  if (entry.kind) html += '<div class="label">Kind</div><div class="value">' + escapeHtml(entry.kind) + '</div>';
  if (entry.definition) {
    html += '<div class="label">Definition</div><div class="value">' + escapeHtml(entry.definition) + '</div>';
  }
  if (entry.usage) {
    html += '<div class="label">Usage</div><div class="value">' + escapeHtml(entry.usage) + '</div>';
  }
  if (entry.answer) {
    html += '<div class="label">Answer</div><div class="value">' + escapeHtml(entry.answer) + '</div>';
  }
  if (entry.source) {
    html += '<div class="label">Source</div><div class="value">' + entry.source_html + '</div>';
  }
  if (entry.code) {
    html += '<div class="label">Reference code</div><pre><code>' + escapeHtml(entry.code) + '</code></pre>';
  }
  if (entry.body) {
    html += '<div class="label">Detail</div><div class="value">' + escapeHtml(entry.body) + '</div>';
  }
  body.innerHTML = html;
  body.classList.remove('aside-empty');
}

function closeAside() {
  document.getElementById('aside').classList.remove('open');
  document.getElementById('aside-backdrop').classList.remove('open');
  document.getElementById('aside-close').hidden = true;
}

function resolveTitle(text) {
  const t = (text || '').trim().toLowerCase().replace(/^q:\\s*/i, '');
  if (BY_TITLE[t]) return BY_TITLE[t];
  // Fuzzy: node label contained in title or vice versa
  for (const e of GLOSSARY) {
    const title = e.title.toLowerCase();
    if (title.includes(t) || t.includes(title)) return e;
  }
  return null;
}

document.getElementById('aside-close').onclick = closeAside;
document.getElementById('aside-backdrop').onclick = closeAside;

const index = document.getElementById('term-index');
GLOSSARY.forEach(e => {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'term-chip';
  b.textContent = e.title;
  b.onclick = () => openEntry(e);
  index.appendChild(b);
});

document.querySelectorAll('[data-term-id]').forEach(el => {
  el.addEventListener('click', (ev) => {
    ev.preventDefault();
    openEntry(BY_ID[el.getAttribute('data-term-id')]);
  });
});

function bindMermaidClicks(root) {
  root.querySelectorAll('.node').forEach(node => {
    const label = (node.textContent || '').replace(/\\s+/g, ' ').trim();
    const entry = resolveTitle(label);
    if (!entry) return;
    node.style.cursor = 'pointer';
    node.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openEntry(entry);
    });
  });
}

mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
Promise.all([...document.querySelectorAll('pre.mermaid')].map(async (el, i) => {
  const id = 'mmd-' + i;
  const graph = el.textContent;
  try {
    const { svg } = await mermaid.render(id, graph);
    el.outerHTML = '<div class="mermaid">' + svg + '</div>';
  } catch (err) {
    el.insertAdjacentHTML('afterend', '<p class="hint">Mermaid render failed.</p>');
  }
})).then(() => {
  document.querySelectorAll('div.mermaid').forEach(bindMermaidClicks);
});
</script>
</body>
</html>
"""


def _extract_title(md: str, fallback: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "term"


def _table_field(block: str, field: str) -> str:
    """Pull a Definition/Usage/Source cell from a markdown table block."""
    pattern = re.compile(
        rf"\|\s*\*\*{re.escape(field)}\*\*\s*\|\s*(.*?)\s*\|",
        re.IGNORECASE,
    )
    match = pattern.search(block)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _fence_code(block: str) -> str:
    match = re.search(r"```[^\n]*\n(.*?)```", block, re.DOTALL)
    return match.group(1).rstrip() if match else ""


def extract_glossary(md: str) -> list[dict[str, str]]:
    """Extract clickable glossary entries from guide markdown."""
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    section = ""
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip().lower()
            i += 1
            continue
        if not line.startswith("### "):
            i += 1
            continue
        title = line[4:].strip()
        if title.lower().startswith("q:"):
            title = title[2:].strip()
        i += 1
        body_lines: list[str] = []
        while i < len(lines) and not lines[i].startswith("##") and not lines[i].startswith("### "):
            body_lines.append(lines[i])
            i += 1
        block = "\n".join(body_lines).strip()
        kind = "concept"
        if "faq" in section:
            kind = "faq"
        elif "architecture" in section:
            kind = "architecture"
        elif "concept" in section:
            kind = "concept"
        else:
            kind = section or "section"

        entry: dict[str, str] = {
            "id": _slugify(title),
            "title": title,
            "kind": kind,
            "definition": _table_field(block, "Definition"),
            "usage": _table_field(block, "Usage"),
            "source": _table_field(block, "Source"),
            "code": _fence_code(block),
            "body": "",
            "answer": "",
        }
        if kind == "faq":
            # Strip trailing Source / code fences from the answer body.
            answer = re.sub(r"\*\*Source:\*\*.*", "", block, flags=re.DOTALL)
            answer = re.sub(r"```.*?```", "", answer, flags=re.DOTALL).strip()
            entry["answer"] = re.sub(r"\s+", " ", answer)
        elif not entry["definition"] and block:
            entry["body"] = re.sub(r"\s+", " ", block[:500])

        base = entry["id"]
        n = 2
        while entry["id"] in seen:
            entry["id"] = f"{base}-{n}"
            n += 1
        seen.add(entry["id"])
        entries.append(entry)
    return entries


def _source_html(source: str) -> str:
    """Keep existing markdown/HTML links; escape plain text."""
    if not source:
        return ""
    if "<a " in source or "](" in source:
        # Already linkified markdown may still be present — escape then restore
        # simple backtick/code remnants for panel display.
        return html.escape(source)
    return html.escape(source)


def decorate_guide_body(body: str, glossary: list[dict[str, str]]) -> str:
    """Mark concept/FAQ headings and inline term mentions as clickable."""
    for entry in glossary:
        title = entry["title"]
        esc_title = html.escape(title)
        # Match h3 from pandoc or simple converter.
        patterns = [
            rf"<h3>(?:Q:\s*)?{re.escape(esc_title)}</h3>",
            rf"<h3>(?:Q:\s*)?{re.escape(title)}</h3>",
        ]
        replacement = (
            f'<h3 class="term-heading" data-term-id="{html.escape(entry["id"], quote=True)}"'
            f' title="Show details">{esc_title}</h3>'
        )
        for pattern in patterns:
            body = re.sub(pattern, replacement, body, count=1, flags=re.IGNORECASE)

    # Inline term chips for glossary titles appearing as <strong>Term</strong>.
    # Longest titles first to avoid partial overlaps.
    for entry in sorted(glossary, key=lambda e: len(e["title"]), reverse=True):
        title = entry["title"]
        if len(title) < 3:
            continue
        chip = (
            f'<button type="button" class="term" data-term-id="'
            f'{html.escape(entry["id"], quote=True)}">{html.escape(title)}</button>'
        )
        body = re.sub(
            rf"(?<![\\w-])<strong>{re.escape(html.escape(title))}</strong>(?![\\w-])",
            chip,
            body,
            flags=re.IGNORECASE,
        )
        body = re.sub(
            rf"(?<![\\w-])<strong>{re.escape(title)}</strong>(?![\\w-])",
            chip,
            body,
            flags=re.IGNORECASE,
        )
    return body


def _glossary_for_js(glossary: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for entry in glossary:
        item = dict(entry)
        item["source_html"] = _source_html(entry.get("source", ""))
        out.append(item)
    return out


def _md_to_html_simple(md: str) -> str:
    """Minimal markdown → HTML when pandoc is unavailable."""
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    table_rows: list[str] = []

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        out.append("<table>")
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            out.append(
                "<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>"
            )
        out.append("</table>")
        table_rows = []

    for line in md.splitlines():
        if line.strip().startswith("|") and "|" in line[1:]:
            if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                continue
            flush_table() if in_code else None
            table_rows.append(line)
            continue
        flush_table()

        if line.strip().startswith("```"):
            if in_code:
                body = html.escape("\n".join(code_buf))
                if code_lang == "mermaid":
                    out.append(f'<pre class="mermaid">{body}</pre>')
                else:
                    out.append(f"<pre><code>{body}</code></pre>")
                code_buf = []
                in_code = False
                code_lang = ""
            else:
                in_code = True
                code_lang = line.strip()[3:].strip()
            continue
        if in_code:
            code_buf.append(line)
            continue
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.strip() == "":
            out.append("")
        elif line.strip().startswith("- "):
            out.append(f"<li>{html.escape(line.strip()[2:])}</li>")
        else:
            text = html.escape(line)
            text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
            out.append(f"<p>{text}</p>")

    flush_table()
    if in_code and code_buf:
        body = html.escape("\n".join(code_buf))
        out.append(f"<pre><code>{body}</code></pre>")
    return "\n".join(out)


def _pandoc_html_body(md_path: Path) -> str | None:
    """Convert markdown to an HTML fragment (no standalone chrome)."""
    if not shutil.which("pandoc"):
        return None
    result = subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-t",
            "html",
            "--from",
            "markdown",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    content = result.stdout
    content = re.sub(
        r'<pre class="([^"]*)"><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\2</pre>',
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r'<div class="sourceCode"[^>]*>\s*<pre class="sourceCode mermaid">'
        r'<code class="sourceCode mermaid">(.*?)</code></pre>\s*</div>',
        r'<pre class="mermaid">\1</pre>',
        content,
        flags=re.DOTALL,
    )
    return content


def _pandoc_pdf(md_path: Path, pdf_path: Path, title: str) -> bool:
    if not shutil.which("pandoc"):
        return False
    engines = ["pdflatex", "xelatex", "lualatex"]
    for engine in engines:
        if not shutil.which(engine):
            continue
        result = subprocess.run(
            [
                "pandoc",
                str(md_path),
                "-o",
                str(pdf_path),
                "--pdf-engine",
                engine,
                "--metadata",
                f"title={title}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and pdf_path.is_file():
            return True
    return False


def build_study_html(study_path: Path, out_path: Path, project_root: Path | None) -> None:
    data = json.loads(study_path.read_text(encoding="utf-8"))
    title = str(data.get("title") or "Codebase study")
    if project_root is not None:
        data["project_path"] = str(project_root)
    for card in data.get("flashcards") or []:
        if "front" not in card or "back" not in card:
            raise SystemExit(f"flashcard missing front/back: {card!r}")
    for q in data.get("quiz") or []:
        for key in ("question", "choices", "answer"):
            if key not in q:
                raise SystemExit(f"quiz item missing {key}: {q!r}")
        if not isinstance(q["choices"], list) or len(q["choices"]) < 2:
            raise SystemExit(f"quiz choices invalid: {q!r}")
    payload = json.dumps(data, ensure_ascii=False)
    page = _STUDY_HTML_TEMPLATE.replace("__TITLE__", html.escape(title)).replace(
        "__DATA_JSON__", payload
    )
    out_path.write_text(page, encoding="utf-8")


def build_guide_html(md_path: Path, out_path: Path, project_root: Path | None) -> str:
    raw_md = md_path.read_text(encoding="utf-8")
    md = linkify_markdown_refs(enrich_markdown_snippets(raw_md, project_root), project_root)
    enriched_path = md_path.parent / "understand-guide.enriched.md"
    enriched_path.write_text(md, encoding="utf-8")
    title = _extract_title(md, "Codebase guide")
    glossary = extract_glossary(md)

    body = _pandoc_html_body(enriched_path)
    if body is None:
        body = _md_to_html_simple(md)
    body = linkify_html_refs(body, project_root)
    body = decorate_guide_body(body, glossary)

    page = (
        _GUIDE_HTML_WRAP.replace("__TITLE__", html.escape(title))
        .replace("__BODY__", body)
        .replace(
            "__GLOSSARY_JSON__",
            json.dumps(_glossary_for_js(glossary), ensure_ascii=False),
        )
    )
    out_path.write_text(page, encoding="utf-8")
    return title


def build(session_directory: Path) -> dict[str, Path | None]:
    session_directory = session_directory.resolve()
    project_root = _project_root_from_session(session_directory)
    guide_md = session_directory / GUIDE_MD
    study_json = session_directory / STUDY_JSON
    if not guide_md.is_file():
        raise SystemExit(f"missing {guide_md} — run Jun author step first")
    if not study_json.is_file():
        raise SystemExit(f"missing {study_json} — run Jun author step first")

    guide_html = session_directory / GUIDE_HTML
    guide_pdf = session_directory / GUIDE_PDF
    study_html = session_directory / STUDY_HTML

    title = build_guide_html(guide_md, guide_html, project_root)
    build_study_html(study_json, study_html, project_root)
    enriched_md = session_directory / "understand-guide.enriched.md"
    pdf_source = enriched_md if enriched_md.is_file() else guide_md
    pdf_ok = _pandoc_pdf(pdf_source, guide_pdf, title)

    return {
        "guide_md": guide_md,
        "guide_html": guide_html,
        "guide_pdf": guide_pdf if pdf_ok else None,
        "study_html": study_html,
        "study_json": study_json,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build understand-codebase interactive HTML (+ optional PDF)"
    )
    parser.add_argument("--id", help="Session id")
    parser.add_argument("--project", default=None, help="Project path for session lookup")
    parser.add_argument("--session-dir", help="Direct path to session artifact directory")
    args = parser.parse_args()

    if args.session_dir:
        directory = Path(args.session_dir)
    elif args.id:
        if not resolve_session_json(args.project, args.id):
            raise SystemExit(f"session not found: {args.id}")
        directory = session_dir(args.project, args.id)
    else:
        raise SystemExit("provide --id or --session-dir")

    outputs = build(directory)
    print(json.dumps({k: str(v) if v else None for k, v in outputs.items()}, indent=2))
    if outputs["guide_pdf"] is None:
        print(
            "\nNote: PDF not generated (install pandoc + a LaTeX engine, "
            "or open understand-guide.html → Print → Save as PDF).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
