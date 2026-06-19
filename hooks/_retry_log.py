"""Shared JSONL retry-log helper used by kon hooks.

Both `teammate_quality_check.py` (Mio must-fix counts) and
`teammate_quality_check.py` (Mio must-fix retry tracking) needs to record and count
append a timestamped entry to a JSONL file, then return how many times each
key has been recorded across history. This module is the single source of
truth for that shape.

Failures (OSError, PermissionError) → return empty dict (fail-open, hooks
must continue). Corrupted JSON lines in the log are skipped, not raised.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path


def retry_limit_warning(
    over_limit: dict[str, int], limit: int, actor: str, items_description: str
) -> str:
    """Format a human-readable retry-limit warning string."""
    lines = "\n".join(f"  - {k} ({c} times)" for k, c in sorted(over_limit.items()))
    return (
        f"WARNING: RETRY LIMIT REACHED{actor}: the following {items_description} "
        f">= {limit} consecutive times — "
        f"consider stopping and asking the user:\n"
        f"{lines}\n"
        f"See skills/failure-handling for the infinite-loop protection rule."
    )


def record_and_count(log_path: Path, keys: set[str], entry_key: str) -> dict[str, int]:
    """Append `keys` to the JSONL `log_path`; return total count per key.

    `entry_key` is the JSON field name used for the list of keys in each
    entry (e.g. `"must_fix_keys"` for Mio, `"failures"` for Stop hook). Keeping
    the field name configurable preserves backward compatibility with
    existing on-disk logs written by either hook.
    """
    counts: dict[str, int] = {}
    try:
        if log_path.is_file():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    for k in entry.get(entry_key, []):
                        counts[k] = counts.get(k, 0) + 1
                except json.JSONDecodeError:
                    pass  # corrupted line — skip, don't crash
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_entry = json.dumps({"ts": ts, entry_key: sorted(keys)}, ensure_ascii=False)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(new_entry + "\n")
        for k in keys:
            counts[k] = counts.get(k, 0) + 1
    except (OSError, PermissionError):
        return {}
    return counts
