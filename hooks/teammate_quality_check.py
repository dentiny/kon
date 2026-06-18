#!/usr/bin/env python3
"""kon TeammateIdle hook: per-agent output spec check.

Blocks when output is non-compliant; fail-open on malformed input or unknown role.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit  # noqa: E402
from _retry_log import record_and_count  # noqa: E402

MIO_RETRY_LIMIT = 2
_RETRY_LOG_BASE = Path(".kon")
_MUST_FIX_FILE_RE = re.compile(r"`([\w./-]+\.\w+)(?::\d+)?`")
_MUST_FIX_LINE_RE = re.compile(
    r"^\s*(?:[-*]|\d+\.)\s+(.+)$",
    re.MULTILINE,
)

_MUST_FIX_HEADING_RE = re.compile(
    r"##\s+(?:must[-\s]?fix)",
    re.IGNORECASE,
)
_NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def _extract_mio_must_fix_keys(out: str) -> set[str]:
    """Extract must-fix keys from Mio output.

    Strategy:
    1. If a '## Must-fix' section exists, extract bullet items from that section only.
    2. Otherwise, fall back to lines containing the 'must-fix' keyword.
    For each item: backtick file path (with :line stripped) is the key;
    if none, use normalized text (lowercase, whitespace collapsed, max 80 chars).
    """
    heading_match = _MUST_FIX_HEADING_RE.search(out)
    if heading_match:
        section_start = heading_match.end()
        next_heading = _NEXT_HEADING_RE.search(out, section_start)
        section_text = (
            out[section_start : next_heading.start()] if next_heading else out[section_start:]
        )
        items = _MUST_FIX_LINE_RE.findall(section_text)
    else:
        items = [
            line.strip()
            for line in out.splitlines()
            if re.search(r"must[-\s]?fix", line, re.IGNORECASE)
        ]

    keys: set[str] = set()
    for item in items:
        file_match = _MUST_FIX_FILE_RE.search(item)
        if file_match:
            keys.add(file_match.group(1))
        else:
            normalized = re.sub(r"\s+", " ", item).strip().lower()[:80]
            if normalized:
                keys.add(normalized)
    return keys


def _mio_log_path(cwd: Path) -> Path:
    log_dir = cwd / _RETRY_LOG_BASE
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "mio-must-fix.jsonl"


def _mio_record_and_count(log_path: Path, keys: set[str]) -> dict[str, int]:
    return record_and_count(log_path, keys, "must_fix_keys")


MEMORY_HEADER_RE = re.compile(r"##\s+Loaded memory entries", re.IGNORECASE)


def require_memory_header(out: str, role: str) -> None:
    """Memory-reader agents must include a `## Loaded memory entries` section.

    Even if there are no relevant entries, the section must be present —
    prevents silent skipping of the cross-project memory layer.
    """
    if not MEMORY_HEADER_RE.search(out):
        emit(
            "block",
            f"{role} output is missing the `## Loaded memory entries` section. "
            "Even with no relevant entries, explicitly write '(no relevant entries)' — "
            "do not silently skip the memory layer.",
        )


def check_azusa(out: str) -> None:
    require_memory_header(out, "Azusa (Explorer)")
    emit("approve", "Azusa (Explorer) output includes memory load report")


PR_DRAFT_RE = re.compile(r"##\s+Suggested PR title", re.IGNORECASE)


def check_mugi(out: str) -> None:
    require_memory_header(out, "Mugi (Planner)")

    # describe-pr mode: Mugi produces a PR draft, not plan.md
    if PR_DRAFT_RE.search(out):
        if not re.search(r"##\s+Suggested PR description", out, re.IGNORECASE):
            emit(
                "block",
                "Mugi (Planner) PR draft is missing `## Suggested PR description`. "
                "describe-pr mode requires both `## Suggested PR title` and "
                "`## Suggested PR description`.",
            )
        emit("approve", "Mugi (Planner) PR draft structure is complete")

    # plan / review / triage mode: output written to .kon/ files
    if not re.search(r"\.kon/(plan|review-rubric|triage-rubric)\.md", out):
        emit(
            "block",
            "Mugi (Planner) output does not reference "
            ".kon/plan.md / .kon/review-rubric.md / .kon/triage-rubric.md. "
            "Write the plan / rubric to that file and report it.",
        )
    if not re.search(
        r"##\s+(Goal|Steps|Rubric|Acceptance|Category)",
        out,
    ):
        emit(
            "block",
            "Mugi (Planner) output is missing required structure "
            "(## Goal / ## Steps / ## Rubric / ## Acceptance / ## Category).",
        )
    emit("approve", "Mugi (Planner) output structure is complete")


CHALLENGE_ID_RE = re.compile(r"^###\s+C\d+:", re.MULTILINE)


def check_azusa_challenge(out: str) -> None:
    require_memory_header(out, "Azusa (Challenge)")
    if not re.search(r"\.kon/design-debate\.md", out):
        emit(
            "block",
            "Azusa (Challenge) output must reference `.kon/design-debate.md`. "
            "Write challenges there under `## Round N — Azusa challenges`.",
        )
    challenges = CHALLENGE_ID_RE.findall(out)
    if len(challenges) < 3:
        emit(
            "block",
            "Azusa (Challenge) must raise at least 3 concrete challenges (C1, C2, C3…). "
            f"Found {len(challenges)}.",
        )
    if re.search(r"\.kon/plan\.md", out) and re.search(
        r"(edit|update|rewrite).+\.kon/plan\.md", out, re.IGNORECASE
    ):
        emit(
            "block",
            "Azusa (Challenge) must not edit `.kon/plan.md` — challenges only.",
        )
    emit("approve", "Azusa (Challenge) output structure is complete")


def check_mugi_revise(out: str) -> None:
    require_memory_header(out, "Mugi (Revise)")
    if not re.search(r"\.kon/plan\.md", out):
        emit(
            "block",
            "Mugi (Revise) must update `.kon/plan.md` and reference it in output.",
        )
    if not re.search(r"\.kon/design-debate\.md", out):
        emit(
            "block",
            "Mugi (Revise) must fill the response table in `.kon/design-debate.md`.",
        )
    if not re.search(r"\|\s*C\d+\s*\|", out):
        emit(
            "block",
            "Mugi (Revise) response table must include a row per challenge ID (| C1 | … |).",
        )
    emit("approve", "Mugi (Revise) output structure is complete")


def check_mio(out: str) -> None:
    require_memory_header(out, "Mio (Reviewer)")
    verdict_match = re.search(r"\b(APPROVED|NEEDS_CHANGES|BLOCKED)\b", out)
    if not verdict_match:
        emit(
            "block",
            "Mio (Reviewer) output has no verdict (APPROVED / NEEDS_CHANGES / BLOCKED). "
            "Default is BLOCKED — every review must state a verdict explicitly.",
        )
        return
    verdict = verdict_match.group(1)

    if not re.search(r"\[[xX ]\]", out):
        emit(
            "block",
            "Mio (Reviewer) output is missing a checklist ([x] / [ ] items). "
            "All 9 mandatory checks must be marked.",
        )

    if verdict != "APPROVED":
        if not re.search(r"(must[-\s]?fix|fix:|evidence|pending)", out, re.IGNORECASE):
            emit(
                "block",
                f"Mio (Reviewer) issued {verdict} but listed no must-fix items or "
                "pending evidence. If blocking, state what needs to change and how.",
            )

        cwd = Path(os.getcwd()).resolve()
        keys = _extract_mio_must_fix_keys(out)
        if keys:
            counts = _mio_record_and_count(_mio_log_path(cwd), keys)
            over_limit = {k: c for k, c in counts.items() if k in keys and c >= MIO_RETRY_LIMIT}
            if over_limit:
                lines = "\n".join(f"  - {k} ({c} times)" for k, c in sorted(over_limit.items()))
                emit(
                    "block",
                    f"WARNING: RETRY LIMIT REACHED (Mio): the following must-fix items "
                    f"have been flagged >= {MIO_RETRY_LIMIT} consecutive times — "
                    f"consider stopping and asking the user:\n"
                    f"{lines}\n"
                    f"See skills/failure-handling for the infinite-loop protection rule.",
                )

    emit("approve", f"Mio (Reviewer) output is compliant (verdict={verdict})")


_URL_RE = re.compile(r"https?://\S+")
_FILE_PATH_EXTS = (
    "py",
    "pyi",
    "js",
    "jsx",
    "mjs",
    "cjs",
    "ts",
    "tsx",
    "vue",
    "svelte",
    "astro",
    "java",
    "kt",
    "kts",
    "scala",
    "groovy",
    "rs",
    "go",
    "c",
    "cc",
    "cpp",
    "cxx",
    "h",
    "hh",
    "hpp",
    "hxx",
    "rb",
    "php",
    "swift",
    "m",
    "mm",
    "cs",
    "fs",
    "fsx",
    "ex",
    "exs",
    "erl",
    "hs",
    "lua",
    "pl",
    "r",
    "jl",
    "dart",
    "clj",
    "cljs",
    "zig",
    "nim",
    "html",
    "htm",
    "css",
    "scss",
    "sass",
    "less",
    "md",
    "mdx",
    "rst",
    "txt",
    "adoc",
    "json",
    "yml",
    "yaml",
    "toml",
    "ini",
    "conf",
    "cfg",
    "env",
    "xml",
    "csv",
    "tsv",
    "lock",
    "properties",
    "sh",
    "bash",
    "zsh",
    "fish",
    "ps1",
    "bat",
    "cmd",
    "mk",
    "bzl",
    "bazel",
    "gradle",
    "sbt",
    "cmake",
    "tf",
    "tfvars",
    "dockerfile",
    "sql",
    "proto",
    "graphql",
    "gql",
    "ipynb",
)
FILE_PATH_RE = re.compile(
    r"[\w./-]+\.(?:" + "|".join(_FILE_PATH_EXTS) + r")\b",
    re.IGNORECASE,
)


def check_yui(out: str) -> None:
    stripped = _URL_RE.sub("", out)
    if not FILE_PATH_RE.search(stripped):
        emit(
            "block",
            "Yui (Implementer) output contains no file path references. "
            "The implementer must explicitly name which files were changed — "
            "'done' without a file path is not enough. "
            "Example: `hooks/teammate_quality_check.py`, `tests/test_auth.py`.",
        )
    emit("approve", "Yui (Implementer) output contains file path references")


def check_ritsu(out: str) -> None:
    if not re.search(r"exit\s+[0-9]+", out):
        emit(
            "block",
            "Ritsu (Verifier) reported no exit code. "
            "Run the actual command and report exit code — PASS/FAIL based on vibes is not acceptable.",
        )

    verdict_match = re.search(r"\b(PASS|FAIL)\b", out)
    if not verdict_match:
        emit("block", "Ritsu (Verifier) gave no final verdict (PASS / FAIL).")
        return
    verdict = verdict_match.group(1)

    hedge_patterns = [
        r"should\s+work",
        r"looks?\s+good",
        r"probably\s+fine",
        r"seems\s+ok",
    ]
    for pattern in hedge_patterns:
        if re.search(pattern, out, re.IGNORECASE):
            emit(
                "block",
                "Ritsu (Verifier) used hedging language ('should work' / 'looks good' etc.). "
                "Only exit codes speak — run the command.",
            )

    emit("approve", f"Ritsu (Verifier) verification result is complete (verdict={verdict})")


def check_sawako(out: str) -> None:
    stripped = _URL_RE.sub("", out)
    if not FILE_PATH_RE.search(stripped):
        emit(
            "block",
            "Sawako (Cleaner) output contains no file path references. "
            "The cleanup report must explicitly name which files were changed.",
        )
    if not re.search(
        r"(no behavior|behavior unchanged|no functional|purely (removal|cleanup|simplification)|no logic (was )?changed)",
        out,
        re.IGNORECASE,
    ):
        emit(
            "block",
            "Sawako (Cleaner) output must include an explicit statement that no behavior was changed. "
            "End the report with a line like 'No behavior changes — purely removal and simplification.'",
        )
    emit("approve", "Sawako (Cleaner) output is compliant")


def check_nodoka(out: str) -> None:
    if not re.search(r"##\s+(What was done|Summary|Changes)", out, re.IGNORECASE):
        emit(
            "block",
            "Nodoka (Summarizer) output is missing required sections. "
            "The summary must include at least ## What was done and ## Changes.",
        )
    stripped = _URL_RE.sub("", out)
    if not FILE_PATH_RE.search(stripped):
        emit(
            "block",
            "Nodoka (Summarizer) output contains no file path references. "
            "The summary must list which files were changed.",
        )
    emit("approve", "Nodoka (Summarizer) output is compliant")


ROLE_HANDLERS = {
    "Azusa": check_azusa,
    "explorer": check_azusa,
    "Explorer": check_azusa,
    "Mugi": check_mugi,
    "planner": check_mugi,
    "Planner": check_mugi,
    "Azusa-challenge": check_azusa_challenge,
    "Mugi-revise": check_mugi_revise,
    "Mio": check_mio,
    "reviewer": check_mio,
    "Reviewer": check_mio,
    "Ritsu": check_ritsu,
    "verifier": check_ritsu,
    "Verifier": check_ritsu,
    "Yui": check_yui,
    "implementer": check_yui,
    "Implementer": check_yui,
    "Sawako": check_sawako,
    "cleaner": check_sawako,
    "Cleaner": check_sawako,
    "Nodoka": check_nodoka,
    "summarizer": check_nodoka,
    "Summarizer": check_nodoka,
}


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit("approve", "Input is not valid JSON — kon teammate check skipped")

    role = (data.get("teammate_role") or "").strip()
    output = data.get("teammate_output") or ""

    if not role or not output:
        emit("approve", "Input missing teammate_role or teammate_output — skipping")

    handler = ROLE_HANDLERS.get(role)
    if handler is None:
        emit("approve", f"{role}: no spec defined, passing by default")
        return

    handler(output)


if __name__ == "__main__":
    main()
