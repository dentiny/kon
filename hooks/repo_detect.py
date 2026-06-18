#!/usr/bin/env python3
"""kon SessionStart hook: detect the current repo and inject project-aware knowledge.

On a match → emit systemMessage asking the agent to load the corresponding skill.
No match → silent approve (empty systemMessage).
Any exception → fail-open approve + stderr line.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit  # noqa: E402

REPO_RULES: list[dict] = [
    # Add project-specific rules here following the pattern:
    # {
    #     "name": "<project-name>",
    #     "skill": "<skill-name>",
    #     "detectors": [
    #         {"type": "git_remote", "pattern": "<owner/repo>"},
    #         {"type": "file_structure", "all_of": ["<required-file>"], "any_of": ["<any-file>"]},
    #     ],
    # },
]

GIT_TIMEOUT_SEC = 3


def check_git_remote(cwd: str, pattern: str) -> bool:
    """Return True if git remote.origin.url contains *pattern*."""
    result = subprocess.run(
        ["git", "-C", cwd, "config", "--get", "remote.origin.url"],
        capture_output=True,
        timeout=GIT_TIMEOUT_SEC,
        check=False,
    )
    url = result.stdout.decode("utf-8", errors="replace").strip()
    return pattern in url


def check_file_structure(cwd: str, all_of: list[str], any_of: list[str]) -> bool:
    """Return True if all files in *all_of* exist AND at least one in *any_of* exists."""
    root = Path(cwd)
    if not all((root / f).is_file() for f in all_of):
        return False
    if any_of and not any((root / f).is_file() for f in any_of):
        return False
    return True


def run_detector(cwd: str, detector: dict) -> tuple[bool, str]:
    """Run one detector; return (matched, description_for_message)."""
    dtype = detector.get("type")
    if dtype == "git_remote":
        pattern = detector["pattern"]
        matched = check_git_remote(cwd, pattern)
        return matched, f"git remote contains {pattern!r}"
    if dtype == "file_structure":
        all_of = detector.get("all_of", [])
        any_of = detector.get("any_of", [])
        matched = check_file_structure(cwd, all_of, any_of)
        return matched, f"file structure ({', '.join(all_of + any_of)})"
    return False, f"unknown detector type: {dtype!r}"


def match_rule(cwd: str, rule: dict) -> tuple[bool, str]:
    """Return (matched, matched_detector_description).

    Any detector matching triggers the rule (current only strategy).
    """
    for detector in rule.get("detectors", []):
        try:
            matched, desc = run_detector(cwd, detector)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        if matched:
            return True, desc
    return False, ""


def seed_claude_config(cwd: str, seeds: dict[str, str]) -> list[str]:
    """Write seed files into .claude/ if absent. Return list of newly-written filenames.

    Never overwrites — once a file exists it is treated as authoritative.
    """
    written: list[str] = []
    if not seeds:
        return written
    claude_dir = Path(cwd) / ".claude"
    try:
        claude_dir.mkdir(exist_ok=True)
    except OSError:
        return written
    for name, content in seeds.items():
        target = claude_dir / name
        if target.exists():
            continue
        try:
            target.write_text(content, encoding="utf-8")
            written.append(name)
        except OSError:
            continue
    return written


def ensure_kon_ignored(cwd: str) -> None:
    """Make `.kon/` git-ignored locally without touching a tracked .gitignore.

    kon writes working artifacts (plan.md, review-rubric.md, retry logs) into
    `.kon/` at the repo root; those must never be committed. We append the rule
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


def main() -> None:
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            data = {}

        cwd = (data.get("cwd") or os.getcwd()).strip()

        ensure_kon_ignored(cwd)

        for rule in REPO_RULES:
            try:
                matched, detector_desc = match_rule(cwd, rule)
            except Exception:
                continue
            if matched:
                name = rule["name"]
                skill = rule["skill"]
                written = seed_claude_config(cwd, rule.get("claude_config_seeds", {}))
                msg = (
                    f"Detected {name} repo (via {detector_desc}). "
                    f"Please read skills/{skill}/SKILL.md and apply its conventions "
                    f"for all skills executed in this session."
                )
                if written:
                    files = ", ".join(f".claude/{f}" for f in written)
                    msg += f" Wrote {files} (edit manually to override)."
                emit("approve", msg)

        emit("approve", "")

    except Exception as exc:  # noqa: BLE001
        print(f"repo_detect: unexpected error: {exc}", file=sys.stderr)
        emit("approve", "")


if __name__ == "__main__":
    main()
