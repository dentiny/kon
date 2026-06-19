#!/usr/bin/env python3
"""kon TeammateIdle / subagentStop quality check: per-agent output spec check.

Called directly by the orchestrator (stdin JSON with ``teammate_role`` /
``teammate_output``) or via ``on_subagent_stop.py`` on Cursor ``subagentStop``.

Blocks when output is non-compliant; fail-open on malformed input or unknown role.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit, read_hook_stdin  # noqa: E402
from _retry_log import record_and_count, retry_limit_warning  # noqa: E402

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
_EVIDENCE_PENDING_HEADING_RE = re.compile(
    r"##\s+evidence\s+pending",
    re.IGNORECASE,
)
_CHECKLIST_HEADING_RE = re.compile(r"##\s+checklist\b", re.IGNORECASE)
_CHECKLIST_ITEM_RE = re.compile(r"^\s*-\s*\[([ xX—\-])\]\s*(.+)$", re.MULTILINE)

_MIO_REQUIRED_CHECKLIST: list[tuple[str, re.Pattern[str]]] = [
    ("acceptance match", re.compile(r"acceptance\s+match", re.IGNORECASE)),
    ("evidence per function", re.compile(r"evidence\s+per\s+function", re.IGNORECASE)),
    ("edge case coverage", re.compile(r"edge\s+case\s+coverage", re.IGNORECASE)),
    ("convention conformance", re.compile(r"convention\s+conformance", re.IGNORECASE)),
    ("no unsafe pattern", re.compile(r"no\s+unsafe\s+pattern", re.IGNORECASE)),
    ("no unexplained magic", re.compile(r"no\s+unexplained\s+magic", re.IGNORECASE)),
    ("no TODO evasion", re.compile(r"no\s+todo\s+evasion", re.IGNORECASE)),
    ("no defensive bloat", re.compile(r"no\s+defensive\s+bloat", re.IGNORECASE)),
    ("no completeness theatre", re.compile(r"no\s+completeness\s+theatre", re.IGNORECASE)),
]
_NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def _extract_mio_must_fix_keys(out: str) -> set[str]:
    """Extract unique keys from Mio's must-fix items."""
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


def check_jun(out: str) -> None:
    require_memory_header(out, "Jun (Researcher)")
    if not re.search(r"\.kon/research\.md", out):
        emit(
            "block",
            "Jun (Researcher) output must reference `.kon/research.md` "
            "(write findings there and cite the path in output).",
        )
    if not re.search(r"##\s+(Findings|Research summary)", out, re.IGNORECASE):
        emit(
            "block",
            "Jun (Researcher) output is missing `## Findings` or `## Research summary`.",
        )
    if not _URL_RE.search(out) and not re.search(
        r"no web sources|no external sources|docs silent",
        out,
        re.IGNORECASE,
    ):
        emit(
            "block",
            "Jun (Researcher) must cite at least one URL in output, "
            "or state that no web sources were available.",
        )
    emit("approve", "Jun (Researcher) output is compliant")


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

    # plan / review mode: output written to .kon/ files
    # Accept session-scoped plan files (.kon/plan-<sid>.md) as well as the legacy .kon/plan.md
    if not re.search(r"\.kon/(plan(-[a-z0-9-]+)?|review-rubric)\.md", out):
        emit(
            "block",
            "Mugi (Planner) output does not reference "
            ".kon/plan-<session-id>.md or .kon/review-rubric.md. "
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
    if re.search(r"\.kon/plan(-[a-z0-9-]+)?\.md", out) and re.search(
        r"(edit|update|rewrite).+\.kon/plan(-[a-z0-9-]+)?\.md", out, re.IGNORECASE
    ):
        emit(
            "block",
            "Azusa (Challenge) must not edit the plan file — challenges only.",
        )
    emit("approve", "Azusa (Challenge) output structure is complete")


def check_mugi_revise(out: str) -> None:
    require_memory_header(out, "Mugi (Revise)")
    if not re.search(r"\.kon/plan(-[a-z0-9-]+)?\.md", out):
        emit(
            "block",
            "Mugi (Revise) must update the plan file and reference it in output.",
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


def _extract_section(out: str, heading_re: re.Pattern[str]) -> str:
    match = heading_re.search(out)
    if not match:
        return ""
    start = match.end()
    next_heading = _NEXT_HEADING_RE.search(out, start)
    return out[start : next_heading.start()] if next_heading else out[start:]


def _parse_mio_checklist_items(section: str) -> list[tuple[str, str]]:
    return [(mark, text.strip()) for mark, text in _CHECKLIST_ITEM_RE.findall(section)]


def _missing_mio_checklist_items(checklist_section: str) -> list[str]:
    if not checklist_section.strip():
        return [label for label, _ in _MIO_REQUIRED_CHECKLIST]
    items = _parse_mio_checklist_items(checklist_section)
    if not items:
        return [label for label, _ in _MIO_REQUIRED_CHECKLIST]
    missing: list[str] = []
    joined = "\n".join(text for _, text in items)
    for label, pattern in _MIO_REQUIRED_CHECKLIST:
        if not pattern.search(joined):
            missing.append(label)
    return missing


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

    checklist_section = _extract_section(out, _CHECKLIST_HEADING_RE)
    missing_items = _missing_mio_checklist_items(checklist_section)
    if missing_items:
        emit(
            "block",
            "Mio (Reviewer) checklist is incomplete — all 9 mandatory items from "
            "skills/strict-review must appear in `## Checklist`. "
            f"Missing: {', '.join(missing_items)}.",
        )

    if verdict == "APPROVED":
        if re.search(r"^\s*-\s*\[ \]", checklist_section, re.MULTILINE):
            emit(
                "block",
                "Mio (Reviewer) issued APPROVED but the checklist contains unchecked "
                "items ([ ]). APPROVED requires every mandatory item to be [x].",
            )
        if _MUST_FIX_HEADING_RE.search(out):
            emit(
                "block",
                "Mio (Reviewer) issued APPROVED but output includes a `## Must-fix` "
                "section. Remove must-fix items or change the verdict.",
            )
        if _EVIDENCE_PENDING_HEADING_RE.search(out):
            emit(
                "block",
                "Mio (Reviewer) issued APPROVED but output includes "
                "`## Evidence pending`. Resolve or change the verdict.",
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
            log_dir = cwd / _RETRY_LOG_BASE
            log_dir.mkdir(parents=True, exist_ok=True)
            counts = record_and_count(log_dir / "mio-must-fix.jsonl", keys, "must_fix_keys")
            over_limit = {k: c for k, c in counts.items() if k in keys and c >= MIO_RETRY_LIMIT}
            if over_limit:
                emit(
                    "block",
                    retry_limit_warning(
                        over_limit,
                        MIO_RETRY_LIMIT,
                        " (Mio)",
                        "must-fix items have been flagged",
                    ),
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


def _require_file_paths(out: str, role: str, purpose: str) -> None:
    if not FILE_PATH_RE.search(_URL_RE.sub("", out)):
        emit("block", f"{role} output contains no file path references. {purpose}")


def check_yui(out: str) -> None:
    _require_file_paths(
        out,
        "Yui (Implementer)",
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
    _require_file_paths(
        out,
        "Sawako (Cleaner)",
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
    _require_file_paths(
        out,
        "Nodoka (Summarizer)",
        "The summary must list which files were changed.",
    )
    emit("approve", "Nodoka (Summarizer) output is compliant")


ROLE_HANDLERS = {
    "Azusa": check_azusa,
    "explorer": check_azusa,
    "Explorer": check_azusa,
    "Jun": check_jun,
    "researcher": check_jun,
    "Researcher": check_jun,
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
    data = read_hook_stdin()
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
