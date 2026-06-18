#!/usr/bin/env bash
# Install kon Cursor hooks into ~/.cursor/hooks.json (merges sessionStart hook).
set -euo pipefail

KON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURSOR_DIR="${HOME}/.cursor"
HOOKS_JSON="${CURSOR_DIR}/hooks.json"
ENSURE_HOOK="python3 ${KON_ROOT}/hooks/ensure_project_dir.py"

mkdir -p "${CURSOR_DIR}"

if [[ ! -f "${HOOKS_JSON}" ]]; then
  cat > "${HOOKS_JSON}" <<EOF
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": "${ENSURE_HOOK}"
      }
    ]
  }
}
EOF
  echo "Created ${HOOKS_JSON}"
  exit 0
fi

python3 - "${HOOKS_JSON}" "${ENSURE_HOOK}" <<'PY'
import json
import sys
from pathlib import Path

hooks_path = Path(sys.argv[1])
ensure_cmd = sys.argv[2]
data = json.loads(hooks_path.read_text(encoding="utf-8"))
if data.get("version") != 1:
    data["version"] = 1
hooks = data.setdefault("hooks", {})
starts = hooks.setdefault("sessionStart", [])
if any(h.get("command") == ensure_cmd for h in starts):
    print(f"sessionStart hook already present in {hooks_path}")
    sys.exit(0)
starts.append({"command": ensure_cmd})
hooks_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Added kon sessionStart hook to {hooks_path}")
PY
