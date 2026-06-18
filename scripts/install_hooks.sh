#!/usr/bin/env bash
# Configure git to use hooks from scripts/hooks/ directly.
# Run once after cloning. No files are copied.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR"

if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "kon install_hooks: hooks directory not found: $HOOKS_DIR" >&2
  exit 1
fi

git config core.hooksPath "$HOOKS_DIR"
echo "Done. Git will use hooks from: $HOOKS_DIR"
echo "To uninstall: git config --unset core.hooksPath"
