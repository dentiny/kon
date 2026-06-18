#!/usr/bin/env python3
"""kon Stop hook: force-run tests before a task is declared complete.

Detects project type → runs the appropriate test command → blocks on failure.
Even if the orchestrator skipped Ritsu, this hook still runs as a backstop.

Supported config files (place in the user project's ``<project>/.kon/`` directory):
- `skip-test-verification` — first non-empty, non-comment line is the skip reason
- `test-command` — override the test command (first non-empty, non-comment line)
- `known-test-failures` — known-failing test IDs (one per line), not blocked
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hook_io import emit, resolve_hook_cwd, set_hook_event  # noqa: E402
from _retry_log import record_and_count  # noqa: E402

TEST_TIMEOUT_SEC = 90
GIT_TIMEOUT_SEC = 5
OUTPUT_TAIL_CHARS = 500
RETRY_LIMIT = 2
_RETRY_LOG_BASE = Path(".kon")

FATAL_MARKER_RE = re.compile(r"\b(ImportError|ModuleNotFoundError|SyntaxError):")

BUILD_ENV_ERROR_RE = re.compile(
    r"CMake configuration failed"
    r"|Failed building wheel for \S+"
    r"|Failed to build [`'\"]?\S+"
    r"|error: linker `[^`]+` not found"
    r"|error: linker \S+ failed"
    r"|error: failed to run custom build command for"
    r"|gyp ERR! (?:stack|build error)"
    r"|node-gyp.+failed"
    r"|cgo: C compiler \S+ not found"
    r"|# runtime/cgo"
    r"|JAVA_HOME is not set"
    r"|FindJava"
    r"|(?:gcc|cc|clang|cl): command not found"
    r"|No such file or directory: ['\"]?(?:gcc|cc|clang|make|cmake)['\"]?",
)


def has_git_modifications(cwd: Path) -> bool:
    """Return True if there are uncommitted changes (staged, unstaged, or untracked).

    Fail-open: returns True on any error so tests still run when uncertain.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd),
            capture_output=True,
            timeout=GIT_TIMEOUT_SEC,
            check=False,
        )
        if result.returncode != 0:
            return True
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True


def read_config_line(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def detect_test_command(cwd: Path) -> list[str] | None:
    """Return the test command for the first matching project type, or None."""
    if (cwd / "uv.lock").is_file():
        if shutil.which("uv"):
            return ["uv", "run", "pytest", "-x"]
    if (cwd / "pyproject.toml").is_file() or (cwd / "setup.py").is_file():
        if (cwd / "tests").is_dir() or (cwd / "test").is_dir():
            if shutil.which("pytest"):
                return ["pytest", "-x"]
    pkg = cwd / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "test" in (data.get("scripts") or {}):
                if shutil.which("npm"):
                    return ["npm", "test", "--silent"]
        except json.JSONDecodeError:
            pass
    if (cwd / "Cargo.toml").is_file():
        if shutil.which("cargo"):
            return ["cargo", "test", "--quiet"]
    if (cwd / "go.mod").is_file():
        if shutil.which("go"):
            return ["go", "test", "-failfast", "./..."]
    return None


def run_command(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            timeout=TEST_TIMEOUT_SEC,
            check=False,
        )
        out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
        return proc.returncode, out
    except FileNotFoundError:
        return -1, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, f"timeout after {TEST_TIMEOUT_SEC}s: {' '.join(cmd)}"


def extract_failures(output: str) -> set[str]:
    """Heuristic extraction of failed test names from common test runner output."""
    failures: set[str] = set()
    failures.update(re.findall(r"FAILED (\S+)", output))
    failures.update(re.findall(r"(\S+::\S+)\s+FAILED", output))
    failures.update(re.findall(r"FAIL\s+(\S+\.(?:test|spec)\.[jt]sx?)", output))
    failures.update(re.findall(r"test (\S+) \.\.\. FAILED", output))
    failures.update(re.findall(r"---\s+FAIL:\s+(\S+)", output))
    return failures


def read_known_failures(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def _retry_log_path(cwd: Path) -> Path:
    log_dir = cwd / _RETRY_LOG_BASE
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "test-failures.jsonl"


def _record_and_count(log_path: Path, failures: set[str]) -> dict[str, int]:
    return record_and_count(log_path, failures, "failures")


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    set_hook_event(data.get("hook_event_name"))

    status = str(data.get("status") or "completed")
    if status != "completed":
        emit("approve", f"agent status={status} — skipping test verification")

    cwd = Path(resolve_hook_cwd(data)).resolve()
    kon_dir = cwd / ".kon"

    if not has_git_modifications(cwd):
        emit(
            "approve",
            "Ritsu (Verifier): no uncommitted changes — skipping test verification",
        )

    skip_reason = read_config_line(kon_dir / "skip-test-verification")
    if skip_reason is not None:
        emit("approve", f"verify_completion skipped: {skip_reason}")

    custom_cmd = read_config_line(kon_dir / "test-command")
    cmd = shlex.split(custom_cmd) if custom_cmd else detect_test_command(cwd)

    if cmd is None:
        emit("approve", "Ritsu (Verifier): no test setup detected — skipping (no-op)")
        return

    known = read_known_failures(kon_dir / "known-test-failures")
    exit_code, output = run_command(cmd, cwd)

    if exit_code == 0:
        emit("approve", f"Ritsu (Verifier): `{' '.join(cmd)}` passed")

    build_env_match = BUILD_ENV_ERROR_RE.search(output)
    if build_env_match:
        emit(
            "approve",
            f"Ritsu (Verifier): `{' '.join(cmd)}` failed due to host build env "
            f"({build_env_match.group(0)!r}), not a test failure — skipping. "
            "Fix the host build env, or set `.kon/test-command` to a runnable command, "
            "or add a reason to `.kon/skip-test-verification`.",
        )

    fatal_match = FATAL_MARKER_RE.search(output)
    if fatal_match:
        emit(
            "block",
            f"Ritsu (Verifier): `{' '.join(cmd)}` hit {fatal_match.group(1)} "
            "(import/collection error, not a test failure). Fix this first.",
        )

    actual = extract_failures(output)
    new_failures = actual - known

    if new_failures:
        counts = _record_and_count(_retry_log_path(cwd), new_failures)
        over_limit = {
            tid: c for tid, c in counts.items() if tid in new_failures and c >= RETRY_LIMIT
        }
        warning = ""
        if over_limit:
            lines = "\n".join(f"  - {tid} ({c} times)" for tid, c in sorted(over_limit.items()))
            warning = (
                f"WARNING: RETRY LIMIT REACHED: the following tests have failed "
                f">= {RETRY_LIMIT} consecutive times — consider stopping and asking the user:\n"
                f"{lines}\n"
                f"See skills/failure-handling for the infinite-loop protection rule.\n\n"
            )
        details = "\n".join(f"  - {f}" for f in sorted(new_failures))
        emit(
            "block",
            f"{warning}Ritsu (Verifier): `{' '.join(cmd)}` exit {exit_code}, "
            f"{len(new_failures)} new failure(s):\n{details}\n\n"
            "(Known failures are ignored; to suppress a new failure, "
            "add its test ID to .kon/known-test-failures)",
        )

    if actual and not new_failures:
        emit(
            "approve",
            f"Ritsu (Verifier): {len(actual)} failure(s) all in known-test-failures — passing",
        )

    tail = output[-OUTPUT_TAIL_CHARS:] if len(output) > OUTPUT_TAIL_CHARS else output
    emit(
        "block",
        f"Ritsu (Verifier): `{' '.join(cmd)}` exit {exit_code} — "
        f"could not parse failure names. Raw tail:\n{tail}",
    )


if __name__ == "__main__":
    main()
