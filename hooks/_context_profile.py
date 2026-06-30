"""Cursor context window observations (preCompact hook) and budget resolution."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _kon_paths import kon_config_path, kon_data_dir

_PROFILE_FILENAME = "context_profile.json"
_CONFIG_BUDGET_KEY = "task_context_budget"


def context_profile_path() -> Path:
    return kon_data_dir() / _PROFILE_FILENAME


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def load_context_profile() -> dict[str, Any]:
    return _read_json(context_profile_path())


def save_context_profile(update: dict[str, Any]) -> dict[str, Any]:
    """Merge *update* into ``~/.kon/context_profile.json`` and return the result."""
    path = context_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = load_context_profile()
    merged.update({k: v for k, v in update.items() if v is not None})
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return merged


def read_config_budget() -> int | None:
    data = _read_json(kon_config_path())
    raw = data.get(_CONFIG_BUDGET_KEY)
    if raw is None:
        return None
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return None


def _int_field(data: dict[str, Any], key: str) -> int | None:
    raw = data.get(key)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def update_from_pre_compact(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist context fields from a Cursor ``preCompact`` hook payload."""
    window = _int_field(payload, "context_window_size")
    tokens = _int_field(payload, "context_tokens")
    usage_pct = payload.get("context_usage_percent")
    update: dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "preCompact",
        "trigger": payload.get("trigger"),
    }
    if window is not None:
        update["context_window_size"] = window
    if tokens is not None:
        update["context_tokens"] = tokens
    if usage_pct is not None:
        try:
            update["context_usage_percent"] = float(usage_pct)
        except (TypeError, ValueError):
            pass
    return save_context_profile(update)


def resolve_context_window_size(
    session: dict[str, Any] | None = None,
    *,
    budget_override: int | None = None,
) -> int | None:
    """Resolve Task context window size (tokens) for budget comparisons.

    Order: CLI/env override → ``~/.kon/config.json`` → session snapshot →
    last ``preCompact`` observation in ``~/.kon/context_profile.json``.
    """
    if budget_override is not None:
        return max(1, int(budget_override))
    raw = os.environ.get("KON_TASK_CONTEXT_BUDGET", "").strip()
    if raw:
        return max(1, int(raw))
    cfg = read_config_budget()
    if cfg is not None:
        return cfg
    data = session or {}
    session_window = _int_field(data, "context_window_size")
    if session_window is not None:
        return session_window
    profile = load_context_profile()
    return _int_field(profile, "context_window_size")


def task_context_snapshot(
    *,
    tokens: int,
    window_size: int | None,
    source: str = "transcript",
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "tokens": max(0, int(tokens)),
        "source": source,
    }
    if window_size is not None and window_size > 0:
        entry["context_window_size"] = window_size
        entry["usage_percent"] = round(tokens / window_size * 100, 2)
    return entry
