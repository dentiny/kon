"""Orchestrator model slug from Cursor hooks — Task subagents need an explicit ``model``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from _context_profile import context_profile_path, load_context_profile, save_context_profile
from _kon_paths import kon_config_path

_PROFILE_MODEL_KEY = "orchestrator_model"
_PROFILE_MODEL_ID_KEY = "orchestrator_model_id"
_PROFILE_MODEL_PARAMS_KEY = "orchestrator_model_params"


def extract_orchestrator_model(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return orchestrator model fields from a Cursor hook payload, if present."""
    model = payload.get("model")
    if not isinstance(model, str) or not model.strip():
        return None
    snap: dict[str, Any] = {_PROFILE_MODEL_KEY: model.strip()}
    model_id = payload.get("model_id")
    if isinstance(model_id, str) and model_id.strip():
        snap[_PROFILE_MODEL_ID_KEY] = model_id.strip()
    params = payload.get("model_params")
    if isinstance(params, list) and params:
        snap[_PROFILE_MODEL_PARAMS_KEY] = params
    return snap


def record_orchestrator_model(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Persist latest orchestrator model to ``~/.kon/context_profile.json``."""
    snap = extract_orchestrator_model(payload)
    if snap is None:
        return None
    snap["orchestrator_model_updated_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return save_context_profile(snap)


def resolve_orchestrator_model(session: dict[str, Any] | None = None) -> str | None:
    """Resolve Task ``model`` slug: session → profile → env/config."""
    data = session or {}
    for key in (_PROFILE_MODEL_KEY, "model"):
        raw = data.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    profile = load_context_profile()
    raw = profile.get(_PROFILE_MODEL_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    import os

    env = os.environ.get("KON_ORCHESTRATOR_MODEL", "").strip()
    if env:
        return env
    cfg_path = kon_config_path()
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            raw = cfg.get(_PROFILE_MODEL_KEY) if isinstance(cfg, dict) else None
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        except (json.JSONDecodeError, OSError):
            pass
    return None


def session_model_patch(snap: dict[str, Any]) -> dict[str, Any]:
    """Fields to merge into session JSON from a hook snapshot."""
    patch: dict[str, Any] = {}
    model = snap.get(_PROFILE_MODEL_KEY)
    if isinstance(model, str) and model.strip():
        patch[_PROFILE_MODEL_KEY] = model.strip()
    model_id = snap.get(_PROFILE_MODEL_ID_KEY)
    if isinstance(model_id, str) and model_id.strip():
        patch[_PROFILE_MODEL_ID_KEY] = model_id.strip()
    params = snap.get(_PROFILE_MODEL_PARAMS_KEY)
    if isinstance(params, list) and params:
        patch[_PROFILE_MODEL_PARAMS_KEY] = params
    updated = snap.get("orchestrator_model_updated_at")
    if isinstance(updated, str):
        patch["orchestrator_model_updated_at"] = updated
    return patch
