#!/usr/bin/env bash
# One-time setup: create venv with ruff, point git at scripts/ for hooks.
# Run after cloning: bash scripts/install_hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Setting up kon dev environment..."

# Create venv and install ruff if not already present
if [ ! -x "$REPO_ROOT/.venv/bin/ruff" ]; then
  echo "  Creating .venv and installing ruff..."
  python3 -m venv "$REPO_ROOT/.venv"
  "$REPO_ROOT/.venv/bin/pip" install ruff -q
fi
echo "  ruff: $("$REPO_ROOT/.venv/bin/ruff" --version)"

# Point git at scripts/ for hooks
git -C "$REPO_ROOT" config core.hooksPath "$SCRIPT_DIR"
echo "  git hooks: $SCRIPT_DIR"

echo "Done. To uninstall: git config --unset core.hooksPath"
