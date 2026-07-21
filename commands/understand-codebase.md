---
description: Learn a codebase — Azusa maps it, Jun writes an interactive HTML guide (concepts + architecture) and study pack (flashcards + quiz).
---

# /kon:understand-codebase

Build **study materials** from a repository: glossary, architecture, flashcards, and a quiz.

**Outputs:**

| File | Format | Contents |
|------|--------|----------|
| `understand-guide.html` | Interactive HTML | Key concepts + architecture + FAQ — **click term / diagram node → side-panel detail**; mermaid + `vscode://` source links |
| `understand-study.html` | Local HTML | Flashcards + quiz with snippets + **clickable `vscode://` source links** |
| `understand-guide.pdf` | PDF (optional) | Print export when pandoc + LaTeX are installed |

Artifacts: `~/.kon/projects/<repo>/sessions/<session-id>/`

## Usage

```
/kon:understand-codebase
/kon:understand-codebase hooks and session tracking
/kon:understand-codebase --yolo   # yolo has no effect on this command
```

Optional text narrows Azusa's exploration scope (still read-only).

## Flow

1. **Orchestrator** — `init --command "/kon:understand-codebase"`, `steps_pending: ["Azusa", "Jun"]`.
2. **🎸 Azusa** — [`agents/Azusa.md`](../agents/Azusa.md) + [`skills/understand-codebase`](../skills/understand-codebase/SKILL.md) **explore mode**.
   - Read-only on app source
   - Hook writes `understand-explore.md`
3. **📚 Jun** — [`agents/Jun.md`](../agents/Jun.md) + same skill **author mode**.
   - Reads `understand-explore.md`
   - Writes `understand-guide.md` + `understand-study.json` under `SESSION_DIR`
4. **Orchestrator** — build products:
   ```bash
   python3 $KON_ROOT/scripts/build_understand_codebase.py --id "$SID"
   ```
5. Present paths to **interactive HTML** first (PDF only if generated). `complete-agent` for Jun → `status=completed`.

Pass `SESSION_DIR` (from `kon_session.py session-dir --id "$SID"`) to both agents.

## Read-only hard floor (application source)

| Action | Allowed? |
|--------|----------|
| Read / Grep / Glob codebase | ✅ |
| Write session artifacts (`understand-*.md/json`) | ✅ (Jun only) |
| Edit application source | ❌ |
| `git commit` / `git push` | ❌ |

## Interactive guide

`understand-guide.html` is the primary deliverable:

- Click a **glossary heading**, **term chip**, or **mermaid diagram node** → detail opens in the **side panel** (definition, usage, source, reference code).
- Source links use `vscode://file/...:line:1` (opens in Cursor/VS Code). Requires `project_path` in session JSON (set on `init`).
- Optional PDF: install pandoc + a LaTeX engine (`brew install pandoc basictex`), or Print → Save as PDF from the HTML.

## Comparison

| Item | `/kon:understand-codebase` | `/kon:ask` | `/kon:research` |
|------|---------------------------|------------|-----------------|
| Purpose | Learning pack | Q&A | External docs |
| Agents | Azusa → Jun | Azusa | Jun |
| Interactive HTML | ✅ | ❌ | ❌ |
| Repo writes | session only | ❌ | `.kon/research.md` |

## After

- Re-run with a narrower scope to deepen one area
- `/kon:team` to implement changes once you understand the code
