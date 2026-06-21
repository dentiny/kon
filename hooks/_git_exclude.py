"""Git exclude helpers for project-local kon artifacts."""

from __future__ import annotations

import subprocess
from pathlib import Path

from _kon_paths import GIT_TIMEOUT_SEC


def ensure_kon_ignored(cwd: str) -> None:
    """Make `.kon/` git-ignored locally without touching a tracked .gitignore.

    kon writes project-local working artifacts (plan-<session-id>.md, review-rubric.md,
    retry logs) into
    ``<project>/.kon/``; those must never be committed. Session history lives in
    ``~/.kon/projects/<repo-name>/`` outside the repo. We append the rule
    to the repo's `info/exclude` — resolved via `git rev-parse --git-path` so
    it lands in the shared git dir even from a linked worktree.

    Idempotent and fail-open.
    """
    try:
        already = subprocess.run(
            ["git", "-C", cwd, "check-ignore", "-q", ".kon/"],
            timeout=GIT_TIMEOUT_SEC,
            check=False,
        )
        if already.returncode == 0:
            return

        resolved = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--git-path", "info/exclude"],
            capture_output=True,
            timeout=GIT_TIMEOUT_SEC,
            check=False,
        )
        if resolved.returncode != 0:
            return

        exclude = Path(resolved.stdout.decode("utf-8", errors="replace").strip())
        if not exclude.is_absolute():
            exclude = Path(cwd) / exclude

        existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        if ".kon/" in existing.split():
            return

        exclude.parent.mkdir(parents=True, exist_ok=True)
        prefix = "" if (not existing or existing.endswith("\n")) else "\n"
        with exclude.open("a", encoding="utf-8") as fh:
            fh.write(f"{prefix}# kon working artifacts (auto-added)\n.kon/\n")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return
