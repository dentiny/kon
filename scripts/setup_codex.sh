#!/usr/bin/env bash
# Install the kon skill for the OpenAI Codex desktop app.
# Creates a symlink: ~/.codex/skills/kon → <kon-root>/adapters/codex/skill
#
# Usage:
#   bash scripts/setup_codex.sh
#   KON_ROOT=/path/to/kon bash scripts/setup_codex.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KON_ROOT="${KON_ROOT:-$(dirname "$SCRIPT_DIR")}"
SKILL_SRC="$KON_ROOT/adapters/codex/skill"
SKILL_DEST="${CODEX_HOME:-$HOME/.codex}/skills/kon"

if [[ ! -d "$SKILL_SRC" ]]; then
  echo "error: skill source not found: $SKILL_SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$SKILL_DEST")"

if [[ -L "$SKILL_DEST" ]]; then
  current="$(readlink "$SKILL_DEST")"
  if [[ "$current" == "$SKILL_SRC" ]]; then
    echo "already installed: $SKILL_DEST -> $SKILL_SRC"
    exit 0
  fi
  echo "updating symlink: $SKILL_DEST"
  rm "$SKILL_DEST"
elif [[ -e "$SKILL_DEST" ]]; then
  echo "error: $SKILL_DEST exists and is not a symlink — remove it manually first" >&2
  exit 1
fi

ln -s "$SKILL_SRC" "$SKILL_DEST"
echo "installed: $SKILL_DEST -> $SKILL_SRC"
echo "Restart Codex for the skill to take effect."
