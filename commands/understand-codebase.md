---
description: Learn a codebase — Azusa maps it, Jun writes a PDF guide (concepts + architecture) and local HTML (flashcards + quiz).
---

# /kon:understand-codebase

Build **study materials** from a repository: glossary, architecture, flashcards, and a quiz.

**Outputs:**

| File | Format | Contents |
|------|--------|----------|
| `understand-guide.pdf` | PDF | Key concepts + architecture + **FAQ** |
| `understand-study.html` | Local HTML | Flashcards + quiz (open in browser) |
| `understand-guide.html` | Local HTML | Guide with mermaid diagrams |

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
5. Present paths to PDF + HTML. `complete-agent` for Jun → `status=completed`.

Pass `SESSION_DIR` (from `kon_session.py session-dir --id "$SID"`) to both agents.

## Read-only hard floor (application source)

| Action | Allowed? |
|--------|----------|
| Read / Grep / Glob codebase | ✅ |
| Write session artifacts (`understand-*.md/json`) | ✅ (Jun only) |
| Edit application source | ❌ |
| `git commit` / `git push` | ❌ |

## PDF note

Build uses **pandoc** when installed (`brew install pandoc basictex`). Without pandoc, open `understand-guide.html` → Print → Save as PDF.

## Comparison

| Item | `/kon:understand-codebase` | `/kon:ask` | `/kon:research` |
|------|---------------------------|------------|-----------------|
| Purpose | Learning pack | Q&A | External docs |
| Agents | Azusa → Jun | Azusa | Jun |
| PDF / HTML | ✅ | ❌ | ❌ |
| Repo writes | session only | ❌ | `.kon/research.md` |

## After

- Re-run with a narrower scope to deepen one area
- `/kon:team` to implement changes once you understand the code
