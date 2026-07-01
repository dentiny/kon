#!/usr/bin/env python3
"""Record orchestrator model from Cursor beforeSubmitPrompt for Task subagent spawns."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _begin_log import hook_log, kon_session_script  # noqa: E402
from _hook_io import read_hook_stdin  # noqa: E402
from _orchestrator_model import record_orchestrator_model, session_model_patch  # noqa: E402
from _workspace import resolve_workspace  # noqa: E402


def _patch_open_session(project: str, snap: dict) -> None:
    patch = session_model_patch(snap)
    if not patch:
        return
    script = kon_session_script()
    if script is None:
        return
    proc = subprocess.run(
        [sys.executable, str(script), "--project", project, "open"],
        capture_output=True,
        text=True,
        check=False,
    )
    sid = proc.stdout.strip()
    if not sid:
        return
    cmd = [
        sys.executable,
        str(script),
        "--project",
        project,
        "patch-orchestrator-model",
        "--id",
        sid,
    ]
    model = patch.get("orchestrator_model")
    if model:
        cmd += ["--model", model]
    model_id = patch.get("orchestrator_model_id")
    if model_id:
        cmd += ["--model-id", model_id]
    params = patch.get("orchestrator_model_params")
    if params:
        cmd += ["--model-params", json.dumps(params)]
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> None:
    try:
        data = read_hook_stdin()
        snap = record_orchestrator_model(data)
        if snap is None:
            print(json.dumps({"continue": True}))
            return
        workspace, source = resolve_workspace(data)
        if workspace:
            _patch_open_session(workspace, snap)
            hook_log(
                f"orchestrator_model={snap.get('orchestrator_model')!r} "
                f"workspace={workspace} source={source}"
            )
        print(json.dumps({"continue": True}))
    except Exception as exc:  # noqa: BLE001
        hook_log(f"unexpected error: {exc}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
