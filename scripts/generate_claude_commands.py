#!/usr/bin/env python3
"""Generate Claude Code plugin command stubs from harness-agnostic commands/*.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = ROOT / "commands"
OUT_DIR = ROOT / "adapters" / "claude-code" / "commands"

# Commands shipped in the Claude Code plugin (exclude internal/experimental).
SHIPPED = {
    "address-comments",
    "ask",
    "begin",
    "debug",
    "describe-issue",
    "design",
    "finish",
    "gc",
    "hunt",
    "quick",
    "research",
    "retro",
    "review",
    "review-pr",
    "summarize",
    "team",
    "todo",
    "understand-codebase",
}

ARG_HINTS: dict[str, str] = {
    "team": "<task>",
    "design": "<task>",
    "quick": "<task>",
    "debug": "<bug>",
    "hunt": "<bug>",
    "ask": "<question>",
    "research": "<question>",
    "gc": "[target]",
    "todo": "<task>",
    "describe-issue": "<#>",
    "understand-codebase": "[scope]",
    "begin": "[goal]",
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)


def _parse_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return f"kon workflow — /kon:{path.stem}"
    desc_match = DESCRIPTION_RE.search(match.group(1))
    if not desc_match:
        return f"kon workflow — /kon:{path.stem}"
    return desc_match.group(1).strip()


def _render(name: str, description: str) -> str:
    hint = ARG_HINTS.get(name, "")
    hint_line = f"argument-hint: {hint}\n" if hint else ""
    return f"""---
description: {description}
{hint_line}disable-model-invocation: true
---

User invoked `/kon:{name}` with arguments: $ARGUMENTS

Resolve once:

```bash
export KON_ROOT="$(python3 "$HOME/.kon/lib/_kon_paths.py" root)"
```

Follow `$KON_ROOT/adapters/claude-code/ORCHESTRATION.md` for command `/kon:{name}`.
Read `$KON_ROOT/commands/{name}.md` and run the full orchestration flow. Do not answer directly.
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    for path in sorted(COMMANDS_DIR.glob("*.md")):
        name = path.stem
        if name not in SHIPPED:
            continue
        description = _parse_description(path)
        out_path = OUT_DIR / f"{name}.md"
        out_path.write_text(_render(name, description), encoding="utf-8")
        generated.append(name)

    # Remove stale generated commands.
    for stale in OUT_DIR.glob("*.md"):
        if stale.stem not in generated:
            stale.unlink()

    print(f"Generated {len(generated)} command stub(s) in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
