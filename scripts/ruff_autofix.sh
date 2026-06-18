#!/bin/sh
# Shared ruff autofix: format Python. Used by pre-commit and pre-push.
# Usage: ruff_autofix.sh [--restage]

REPO_ROOT="$(git rev-parse --show-toplevel)"
RUFF="$REPO_ROOT/.venv/bin/ruff"
if [ ! -x "$RUFF" ]; then
  RUFF="$(command -v ruff 2>/dev/null)"
fi
if [ -z "$RUFF" ]; then
  echo "kon: ruff not found. Run: bash scripts/install_hooks.sh" >&2
  exit 1
fi

cd "$REPO_ROOT" || exit 1
"$RUFF" format .

if [ "$1" = "--restage" ]; then
  for f in $(git diff --name-only); do
    if git diff --cached --name-only | grep -Fxq "$f"; then
      git add "$f"
    fi
  done
fi

exit 0
