#!/usr/bin/env bash
# Create ~/.kon/public/memory/ and per-repo memory under ~/.kon/projects/<repo>/memory/.
set -euo pipefail

KON_ROOT="${KON_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

public_dir="$(python3 "${KON_ROOT}/hooks/_kon_paths.py" public-memory)"
echo "Public memory: ${public_dir}"

if [[ -n "${1:-}" ]]; then
  repo_dir="$(cd "$1" && python3 "${KON_ROOT}/hooks/_kon_paths.py" project-memory)"
  echo "Repo memory: ${repo_dir}"
fi

legacy="${HOME}/.config/kon/memory"
if [[ -d "${legacy}" ]]; then
  echo "Note: legacy ${legacy} was merged into ${public_dir} on first ensure (if any entries existed)."
fi

echo "Agents load via skills/memory-loading; saves via memory-propose-confirm and session retro."
