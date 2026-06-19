#!/usr/bin/env bash
# One-time per-machine setup for kon in Cursor:
#   - copy global rule (kon.mdc)
#   - install hooks into ~/.cursor/hooks.json
#   - write ~/.kon/config.json with this clone's path
#
# Usage (from any kon clone):
#   bash scripts/setup_cursor.sh
#   bash scripts/setup_cursor.sh --project /path/to/your/repo   # also install project-local rule
set -euo pipefail

KON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURSOR_RULES="${HOME}/.cursor/rules"
PROJECT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="${2:?--project requires a path}"
      shift 2
      ;;
    -h | --help)
      echo "Usage: bash scripts/setup_cursor.sh [--project /path/to/repo]"
      echo ""
      echo "Installs kon for Cursor on this machine:"
      echo "  1. ~/.cursor/rules/kon.mdc          (global rule)"
      echo "  2. ~/.cursor/hooks.json             (merged, idempotent)"
      echo "  3. ~/.kon/config.json               (kon_root -> this clone)"
      echo ""
      echo "Re-run after kon updates, moving the clone, or adding/removing hooks."
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "${CURSOR_RULES}"
cp "${KON_ROOT}/adapters/cursor/kon.mdc" "${CURSOR_RULES}/kon.mdc"
echo "Wrote ${CURSOR_RULES}/kon.mdc"

if [[ -n "${PROJECT}" ]]; then
  proj_rule="${PROJECT}/.cursor/rules"
  mkdir -p "${proj_rule}"
  cp "${KON_ROOT}/adapters/cursor/kon.mdc" "${proj_rule}/kon.mdc"
  echo "Wrote ${proj_rule}/kon.mdc"
fi

bash "${KON_ROOT}/scripts/install_cursor_hooks.sh"

echo ""
echo "kon Cursor setup complete."
echo "  KON_ROOT=${KON_ROOT}"
echo "  Config:   ~/.kon/config.json"
echo "  Hooks:    ~/.cursor/hooks.json"
echo ""
echo "Try in Cursor chat: /kon:team <task>"
