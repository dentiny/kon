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
import re
import sys
from pathlib import Path

hooks_path = Path(sys.argv[1])
kon_root = Path(sys.argv[2]).resolve()

# Canonical kon Cursor hooks (keep in sync with hooks/ and README).
KON_HOOK_SCRIPTS = [
    "ensure_project_dir.py",
    "init_kon_session.py",
    "log_begin_prompt.py",
    "no_git_write.py",
    "log_begin_response.py",
    "on_subagent_stop.py",
]

# Removed hooks — stripped from ~/.cursor/hooks.json on every install/upgrade.
DEPRECATED_HOOK_SCRIPTS = [
    "verify_completion.py",
    "repo_detect.py",
]

MANAGED = KON_HOOK_SCRIPTS + DEPRECATED_HOOK_SCRIPTS
managed_res = [re.compile(rf"/hooks/{re.escape(name)}(?:\s|$)") for name in MANAGED]

entries = [
    ("sessionStart", "ensure_project_dir.py"),
    ("beforeSubmitPrompt", "init_kon_session.py"),
    ("beforeSubmitPrompt", "log_begin_prompt.py"),
    ("beforeShellExecution", "no_git_write.py"),
    ("afterAgentResponse", "log_begin_response.py"),
    ("subagentStop", "on_subagent_stop.py"),
]

if hooks_path.is_file():
    data = json.loads(hooks_path.read_text(encoding="utf-8"))
else:
    data = {"version": 1, "hooks": {}}

if data.get("version") != 1:
    data["version"] = 1

hooks = data.setdefault("hooks", {})
removed = 0

for event, bucket in list(hooks.items()):
    if not isinstance(bucket, list):
        continue
    kept = []
    for spec in bucket:
        cmd = spec.get("command", "") if isinstance(spec, dict) else ""
        if any(r.search(cmd) for r in managed_res):
            removed += 1
            continue
        kept.append(spec)
    hooks[event] = kept

added = 0
for event, script in entries:
    bucket = hooks.setdefault(event, [])
    spec = {"command": f"python3 {kon_root}/hooks/{script}"}
    bucket.append(spec)
    added += 1

hooks_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(
    f"Updated {hooks_path}: installed {added} kon hook(s), "
    f"removed {removed} stale/deprecated kon hook(s)"
)
PY
