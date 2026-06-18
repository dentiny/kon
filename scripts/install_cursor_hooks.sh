#!/usr/bin/env bash
# Install kon Cursor hooks into ~/.cursor/hooks.json (merges all kon hooks idempotently).
# Also writes ~/.kon/config.json (kon_root) and ~/.kon/lib/_kon_paths.py for path resolution.
set -euo pipefail

KON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURSOR_DIR="${HOME}/.cursor"
HOOKS_JSON="${CURSOR_DIR}/hooks.json"

mkdir -p "${CURSOR_DIR}"

python3 "${KON_ROOT}/hooks/_kon_paths.py" write-config "${KON_ROOT}"
python3 - <<PY
from pathlib import Path
import sys
sys.path.insert(0, "${KON_ROOT}/hooks")
from _kon_paths import install_bundled_paths_module
dest = install_bundled_paths_module(Path("${KON_ROOT}/hooks/_kon_paths.py"))
print(f"Wrote {dest}")
PY

python3 - "${HOOKS_JSON}" "${KON_ROOT}" <<'PY'
import json
import sys
from pathlib import Path

hooks_path = Path(sys.argv[1])
kon_root = Path(sys.argv[2]).resolve()

entries = [
    (
        "sessionStart",
        {"command": f"python3 {kon_root}/hooks/ensure_project_dir.py"},
    ),
    (
        "beforeSubmitPrompt",
        {"command": f"python3 {kon_root}/hooks/init_kon_session.py"},
    ),
    (
        "beforeShellExecution",
        {"command": f"python3 {kon_root}/hooks/no_git_write.py"},
    ),
    (
        "subagentStop",
        {"command": f"python3 {kon_root}/hooks/on_subagent_stop.py"},
    ),
    (
        "stop",
        {
            "command": f"python3 {kon_root}/hooks/verify_completion.py",
            "loop_limit": 3,
        },
    ),
]

if hooks_path.is_file():
    data = json.loads(hooks_path.read_text(encoding="utf-8"))
else:
    data = {"version": 1, "hooks": {}}

if data.get("version") != 1:
    data["version"] = 1

hooks = data.setdefault("hooks", {})
added = 0
already = 0

for event, spec in entries:
    bucket = hooks.setdefault(event, [])
    command = spec["command"]
    if any(h.get("command") == command for h in bucket):
        already += 1
        continue
    bucket.append(spec)
    added += 1

hooks_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Updated {hooks_path}: added {added} hook(s), {already} already present")
PY
