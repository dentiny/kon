#!/usr/bin/env bash
# Create ~/.config/kon/memory/ and an empty MEMORY.md index (one-time bootstrap).
set -euo pipefail

MEMORY_DIR="${HOME}/.config/kon/memory"
INDEX="${MEMORY_DIR}/MEMORY.md"

mkdir -p "${MEMORY_DIR}"

if [[ -f "${INDEX}" ]]; then
  echo "Memory index already exists: ${INDEX}"
  exit 0
fi

cat > "${INDEX}" <<'EOF'
# kon memory index

Cross-project preferences and conventions loaded by Azusa, Mugi, and Mio at startup.
See `skills/memory-loading/SKILL.md` in the kon repo.

Add entries below (one per line):

- [Title](slug.md) — one-line description

Entry files live in this directory with YAML frontmatter (`name`, `description`, `type`).
Types: `user`, `project`, `feedback`, `reference`.
EOF

echo "Created ${INDEX}"
echo "Agents load entries via skills/memory-loading; propose new ones via Memory propose flow."
