#!/usr/bin/env bash
# Print absolute kon plugin root (respects KON_ROOT, ~/.kon/config.json, clone location).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLED="${HOME}/.kon/lib/_kon_paths.py"
LOCAL="${SCRIPT_DIR}/../hooks/_kon_paths.py"

if [[ -n "${KON_ROOT:-}" ]]; then
  python3 -c 'import os, pathlib; print(pathlib.Path(os.environ["KON_ROOT"]).expanduser().resolve())'
elif [[ -f "$BUNDLED" ]]; then
  python3 "$BUNDLED" root
elif [[ -f "$LOCAL" ]]; then
  python3 "$LOCAL" root
else
  echo "kon: cannot resolve KON_ROOT — run bash scripts/install_cursor_hooks.sh" >&2
  exit 1
fi
