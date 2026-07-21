#!/usr/bin/env bash
# Install kon as a Claude Code plugin (skills-dir auto-load).
#
# 1. Writes ~/.kon/config.json with this clone's path
# 2. Symlinks adapters/claude-code → ~/.claude/skills/kon
# 3. Regenerates plugin command stubs from commands/*.md
#
# Usage:
#   bash scripts/setup_claude_code.sh
#   KON_ROOT=/path/to/kon bash scripts/setup_claude_code.sh
#
# After install, in Claude Code:
#   /reload-plugins
#   /kon:team add email validation
#
# Marketplace install (alternative):
#   /plugin marketplace add dentiny/kon
#   /plugin install kon@dentiny-kon

set -euo pipefail

KON_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_SRC="$KON_ROOT/adapters/claude-code"
CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"
PLUGIN_DEST="$CLAUDE_DIR/skills/kon"

if [[ ! -d "$PLUGIN_SRC/.claude-plugin" ]]; then
  echo "error: plugin source not found: $PLUGIN_SRC" >&2
  exit 1
fi

python3 "$KON_ROOT/scripts/generate_claude_commands.py"

python3 "$KON_ROOT/hooks/_kon_paths.py" write-config "$KON_ROOT"
python3 - <<PY
from pathlib import Path
import sys
sys.path.insert(0, "${KON_ROOT}/hooks")
from _kon_paths import install_bundled_paths_module
dest = install_bundled_paths_module(Path("${KON_ROOT}/hooks/_kon_paths.py"))
print(f"Wrote {dest}")
PY

mkdir -p "$(dirname "$PLUGIN_DEST")"

if [[ -L "$PLUGIN_DEST" ]]; then
  current="$(readlink "$PLUGIN_DEST")"
  if [[ "$current" == "$PLUGIN_SRC" ]]; then
    echo "already installed: $PLUGIN_DEST -> $PLUGIN_SRC"
  else
    echo "updating symlink: $PLUGIN_DEST"
    rm "$PLUGIN_DEST"
    ln -s "$PLUGIN_SRC" "$PLUGIN_DEST"
  fi
elif [[ -e "$PLUGIN_DEST" ]]; then
  echo "error: $PLUGIN_DEST exists and is not a symlink — remove it manually first" >&2
  exit 1
else
  ln -s "$PLUGIN_SRC" "$PLUGIN_DEST"
  echo "installed: $PLUGIN_DEST -> $PLUGIN_SRC"
fi

echo ""
echo "kon Claude Code setup complete."
echo "  KON_ROOT=${KON_ROOT}"
echo "  Plugin:   ${PLUGIN_DEST}"
echo "  Config:   ~/.kon/config.json"
echo ""
echo "In Claude Code, run /reload-plugins then try: /kon:team <task>"
echo ""
echo "Marketplace alternative:"
echo "  /plugin marketplace add dentiny/kon"
echo "  /plugin install kon@dentiny-kon"
