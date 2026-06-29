#!/usr/bin/env python3
"""Build PDF + HTML study pack from /kon:understand-codebase session artifacts.

Reads:
  sessions/<id>/understand-guide.md
  sessions/<id>/understand-study.json

Writes:
  sessions/<id>/understand-guide.html
  sessions/<id>/understand-guide.pdf   (when pandoc is available)
  sessions/<id>/understand-study.html

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
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       max-width: 820px; margin: 0 auto; padding: 32px 24px 64px;
       line-height: 1.6; color: #1f2328; background: #fff; }
@media print { body { max-width: none; padding: 16px; } }
h1 { font-size: 28px; border-bottom: 1px solid #d0d7de; padding-bottom: 8px; }
h2 { font-size: 22px; margin-top: 32px; }
h3 { font-size: 18px; margin-top: 24px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
th { background: #f6f8fa; }
code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 90%; }
pre { background: #f6f8fa; padding: 16px; overflow-x: auto; border-radius: 8px;
     border-left: 3px solid #0969da; }
pre code { background: none; padding: 0; }
a.code-ref { color: #0969da; text-decoration: none; }
a.code-ref:hover { text-decoration: underline; }
.mermaid { margin: 16px 0; }
</style>
</head>
<body>
__BODY__
<script>mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});</script>
</body>
</html>
"""


def _extract_title(md: str, fallback: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


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


def _pandoc_html(md_path: Path, html_path: Path, title: str) -> bool:
    if not shutil.which("pandoc"):
        return False
    result = subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-o",
            str(html_path),
            "--standalone",
            "--metadata",
            f"title={title}",
            "--from",
            "markdown",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    # Inject mermaid for fenced blocks pandoc renders as code
    content = html_path.read_text(encoding="utf-8")
    content = re.sub(
        r'<pre class="([^"]*)"><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\2</pre>',
        content,
        flags=re.DOTALL,
    )
    if "mermaid.min.js" not in content:
        content = content.replace(
            "</head>",
            '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>\n</head>',
        )
        content = content.replace(
            "</body>",
            '<script>mermaid.initialize({startOnLoad:true,theme:"neutral"});</script>\n</body>',
        )
    html_path.write_text(content, encoding="utf-8")
    return True


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
    if not _pandoc_html(enriched_path, out_path, title):
        body = linkify_html_refs(_md_to_html_simple(md), project_root)
        page = _GUIDE_HTML_WRAP.replace("__TITLE__", html.escape(title)).replace("__BODY__", body)
        out_path.write_text(page, encoding="utf-8")
    else:
        content = linkify_html_refs(out_path.read_text(encoding="utf-8"), project_root)
        out_path.write_text(content, encoding="utf-8")
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
    parser = argparse.ArgumentParser(description="Build understand-codebase PDF + HTML")
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
