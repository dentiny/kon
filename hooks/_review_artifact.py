"""Write agent markdown artifacts under sessions/<session-id>/ for browser review."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from _kon_paths import iter_sessions_dirs, resolve_project_path
from _session_paths import (
    ARTIFACT_EXPLORE,
    ARTIFACT_ISSUE_SUMMARY,
    ARTIFACT_PR_REVIEW,
    ARTIFACT_REVIEW,
    ensure_session_dir,
    iter_session_json_paths,
    session_artifact_path,
)

MIO_REVIEW_COMMANDS = frozenset({
    "/kon:review",
    "/kon:debug",
    "/kon:review-pr",
    "/kon:team",
    "/kon:quick",
})
AZUSA_EXPLORE_COMMANDS = frozenset({"/kon:team", "/kon:design"})


def _review_append_mode(command: str) -> bool:
    return command in ("/kon:debug", "/kon:team", "/kon:quick")


def review_artifact_path(project: str | Path | None, session_id: str) -> Path:
    return session_artifact_path(project, session_id, ARTIFACT_REVIEW)


def pr_review_artifact_path(project: str | Path | None, session_id: str) -> Path:
    return session_artifact_path(project, session_id, ARTIFACT_PR_REVIEW)


def issue_summary_artifact_path(project: str | Path | None, session_id: str) -> Path:
    return session_artifact_path(project, session_id, ARTIFACT_ISSUE_SUMMARY)


def _artifact_path_for_command(project: str | Path | None, session_id: str, command: str) -> Path:
    if command == "/kon:review-pr":
        return pr_review_artifact_path(project, session_id)
    if command == "/kon:describe-issue":
        return issue_summary_artifact_path(project, session_id)
    return review_artifact_path(project, session_id)


def _title_for_command(command: str) -> str:
    if command == "/kon:review-pr":
        return "PR review"
    if command == "/kon:describe-issue":
        return "Issue summary"
    return "Code review"


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(str(block["text"]))
                else:
                    parts.append(json.dumps(block, ensure_ascii=False))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    if content is None:
        return ""
    return json.dumps(content, ensure_ascii=False)


def _assistant_parts_from_jsonl(text: str) -> list[str]:
    parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("role") != "assistant":
            continue
        message = row.get("message") or {}
        body = _content_text(message.get("content")).strip()
        if body:
            parts.append(body)
    return parts


def extract_assistant_markdown(output: str, transcript_path: str | Path | None = None) -> str:
    """Best-effort full assistant text from hook summary and/or transcript JSONL."""
    candidates: list[str] = []

    summary = output.strip()
    if summary:
        candidates.append(summary)

    if transcript_path is not None:
        path = Path(transcript_path)
        if path.is_file():
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                raw = ""
            if raw.strip():
                parts = _assistant_parts_from_jsonl(raw)
                if parts:
                    candidates.append("\n\n".join(parts))
                elif not summary:
                    candidates.append(raw.strip())

    if not candidates:
        return ""

    return max(candidates, key=len)


def find_open_session(project: str | Path | None) -> tuple[str, dict] | None:
    """Most recent open session for this project."""
    project_path = str(resolve_project_path(project))
    best_id = ""
    best_data: dict | None = None
    for directory in iter_sessions_dirs(project):
        for _sid, path in iter_session_json_paths(directory):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("project_path") != project_path:
                continue
            if data.get("status") not in {"in_progress", "waiting"}:
                continue
            key = data.get("started_at") or data.get("id") or ""
            if key >= best_id:
                best_id = key
                best_data = data
    if best_data is None:
        return None
    return str(best_data.get("id") or ""), best_data


def _format_artifact_markdown(
    *,
    session_id: str,
    command: str,
    task: str,
    body: str,
    section_ts: str | None = None,
) -> str:
    ts = section_ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = _title_for_command(command)
    header = (
        f"# {title}\n\n"
        f"**Session**: `{session_id}`  \n"
        f"**Command**: `{command}`  \n"
        f"**Task**: {task.strip() or '—'}  \n"
        f"**Written**: {ts}\n\n"
        f"---\n\n"
    )
    return header + body.strip() + "\n"


def write_session_artifact(
    project: str | Path | None,
    session_id: str,
    *,
    command: str,
    task: str,
    body: str,
    append: bool = False,
) -> Path | None:
    text = body.strip()
    if not text:
        return None

    ensure_session_dir(project, session_id)
    path = _artifact_path_for_command(project, session_id, command)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if append and path.is_file():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError:
            existing = ""
        section = f"\n\n---\n\n## Update — {ts}\n\n{text}\n"
        path.write_text(existing.rstrip() + section, encoding="utf-8")
        return path

    path.write_text(
        _format_artifact_markdown(
            session_id=session_id,
            command=command,
            task=task,
            body=text,
            section_ts=ts,
        ),
        encoding="utf-8",
    )
    return path


def write_review_artifact(
    project: str | Path | None,
    session_id: str,
    *,
    command: str,
    task: str,
    body: str,
    append: bool = False,
) -> Path | None:
    """Backward-compatible alias for Mio review artifacts."""
    return write_session_artifact(
        project,
        session_id,
        command=command,
        task=task,
        body=body,
        append=append,
    )


def maybe_write_review_from_hook(
    project: str | Path | None,
    *,
    agent: str,
    output: str,
    transcript_path: str | Path | None = None,
) -> Path | None:
    """Persist Mio output for review / review-pr / debug sessions."""
    if agent != "Mio":
        return None

    found = find_open_session(project)
    if found is None:
        return None
    session_id, data = found
    command = str(data.get("command") or "")
    if command not in MIO_REVIEW_COMMANDS:
        return None

    body = extract_assistant_markdown(output, transcript_path)
    if not body:
        return None

    return write_session_artifact(
        project,
        session_id,
        command=command,
        task=str(data.get("task") or ""),
        body=body,
        append=_review_append_mode(command),
    )


def maybe_write_explore_from_hook(
    project: str | Path | None,
    *,
    agent: str,
    output: str,
    transcript_path: str | Path | None = None,
) -> Path | None:
    """Persist Azusa exploration for team/design sessions."""
    if agent != "Azusa":
        return None

    found = find_open_session(project)
    if found is None:
        return None
    session_id, data = found
    command = str(data.get("command") or "")
    if command not in AZUSA_EXPLORE_COMMANDS:
        return None

    body = extract_assistant_markdown(output, transcript_path)
    if not body:
        return None

    ensure_session_dir(project, session_id)
    path = session_artifact_path(project, session_id, ARTIFACT_EXPLORE)
    path.write_text(
        _format_artifact_markdown(
            session_id=session_id,
            command=command,
            task=str(data.get("task") or ""),
            body=body,
        ),
        encoding="utf-8",
    )
    return path


def maybe_write_issue_from_hook(
    project: str | Path | None,
    *,
    agent: str,
    output: str,
    transcript_path: str | Path | None = None,
) -> Path | None:
    """Persist Jun output for describe-issue sessions."""
    if agent != "Jun":
        return None

    found = find_open_session(project)
    if found is None:
        return None
    session_id, data = found
    if str(data.get("command") or "") != "/kon:describe-issue":
        return None

    body = extract_assistant_markdown(output, transcript_path)
    if not body:
        return None

    return write_session_artifact(
        project,
        session_id,
        command="/kon:describe-issue",
        task=str(data.get("task") or ""),
        body=body,
    )
