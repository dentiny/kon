"""Per-session directory layout under ~/.kon/projects/<repo>/sessions/<id>/.

All artifacts for one run live in one folder so delete removes everything.

Layout::

    sessions/<session-id>/
        session.json
        summary.md
        plan.md
        explore.md
        review.md
        pr-review.md
        issue-summary.md
        debug.md
        design-debate.md
        review-rubric.md
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from _kon_paths import iter_sessions_dirs, project_kon_dir, sessions_dir

SESSION_JSON = "session.json"
ARTIFACT_PLAN = "plan.md"
ARTIFACT_EXPLORE = "explore.md"
ARTIFACT_REVIEW = "review.md"
ARTIFACT_PR_REVIEW = "pr-review.md"
ARTIFACT_ISSUE_SUMMARY = "issue-summary.md"


def session_dir(project: Path | str | None, session_id: str) -> Path:
    return sessions_dir(project) / session_id


def ensure_session_dir(project: Path | str | None, session_id: str) -> Path:
    directory = session_dir(project, session_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def session_json_path(project: Path | str | None, session_id: str) -> Path:
    return session_dir(project, session_id) / SESSION_JSON


def session_artifact_path(project: Path | str | None, session_id: str, name: str) -> Path:
    return session_dir(project, session_id) / name


def resolve_session_json(project: Path | str | None, session_id: str) -> Path | None:
    """New layout first, then legacy flat ``<id>.json``."""
    for directory in iter_sessions_dirs(project):
        canonical = directory / session_id / SESSION_JSON
        if canonical.is_file():
            return canonical
        legacy = directory / f"{session_id}.json"
        if legacy.is_file():
            return legacy
    return None


def iter_session_json_paths(directory: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(session_id, path)`` for every session JSON under *directory*."""
    if not directory.is_dir():
        return

    seen: set[str] = set()
    for sub in sorted(directory.iterdir()):
        if not sub.is_dir():
            continue
        path = sub / SESSION_JSON
        if path.is_file():
            seen.add(sub.name)
            yield sub.name, path

    for path in sorted(directory.glob("*.json")):
        sid = path.stem
        if sid not in seen:
            yield sid, path


def legacy_project_artifact_paths(project_path: str, session_id: str) -> list[Path]:
    """Old scattered files under ``<project>/.kon/`` (pre-directory layout)."""
    kon_dir = project_kon_dir(project_path)
    return [
        kon_dir / f"plan-{session_id}.md",
        kon_dir / f"review-{session_id}.md",
        kon_dir / f"debug-{session_id}.md",
        kon_dir / f"design-debate-{session_id}.md",
        kon_dir / "sessions" / f"{session_id}.json",
        kon_dir / "sessions" / f"{session_id}-summary.md",
        kon_dir / "sessions" / session_id,
    ]


def all_session_delete_paths(
    session_id: str,
    project_path: str | None = None,
) -> list[Path]:
    """Every path to remove when deleting a session (dirs removed recursively)."""
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            paths.append(path)

    for directory in iter_sessions_dirs(None):
        add(directory / session_id)
        add(directory / f"{session_id}.json")
        add(directory / f"{session_id}-summary.md")

    if project_path:
        for path in legacy_project_artifact_paths(project_path, session_id):
            add(path)

    return paths
