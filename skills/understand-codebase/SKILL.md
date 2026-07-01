---
name: understand-codebase
description: Map a codebase for learning — glossary, architecture, flashcards, and quiz. Produces a PDF guide and local HTML study pack.
---

# Understand Codebase

**Consumers**: `/kon:understand-codebase`

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — teach from what the repo actually contains; simplest path through the concepts.

Turn a repository into study materials: **key concepts**, **architecture**, **flashcards**, and a **quiz**.

## Deliverables (after build step)

| Output | Contents |
|--------|----------|
| `understand-guide.pdf` | Key concepts + **reference code** + architecture + FAQ (links in PDF when pandoc) |
| `understand-study.html` | Flashcards + quiz with **snippets** + **clickable source links** |
| `understand-guide.html` | Same as PDF; mermaid + **`vscode://` / `cursor://` links** open files in IDE |

All files live under `sessions/<session-id>/`. Orchestrator runs `build_understand_codebase.py` after Jun finishes.

## Pipeline

1. **🎸 Azusa (explore)** — read-only codebase map → hook saves `understand-explore.md`
2. **📚 Jun (author)** — reads explore artifact, writes `understand-guide.md` + `understand-study.json`
3. **Orchestrator** — `python3 $KON_ROOT/scripts/build_understand_codebase.py --id "$SID"`

## Azusa — explore mode

Read [`agents/Azusa.md`](../../agents/Azusa.md). **Read-only** — no Write/Edit on application source.

Pass `SESSION_DIR`, `EXPLORE_FILE: understand-explore.md`.

### Required sections (hook persists full output)

```markdown
## Loaded memory entries
…

## Scope
<what was explored; optional user focus from command>

## Code map
| Area | Key paths | One-line role |
|------|-----------|---------------|

## Concepts spotted (raw)
For each term you see in code/docs — name, where found (`path:line`), rough meaning from evidence:

### <Term>
- **Seen in**: `path:line`, …
- **Notes**: …

## Architecture notes (raw)
- **Deployment shape**: single-node / distributed / hybrid — evidence
- **Major components**: …
- **Data flow**: …
- **External deps**: …

## Implementation anchors
Concrete `path:line` pairs worth flashcard/quiz treatment later.

## Gaps
What could not be determined from the repo alone.
```

Do not invent behaviour — cite paths. Unknown → `## Gaps`.

## Jun — author mode

Read [`agents/Jun.md`](../../agents/Jun.md). **Write only** to `SESSION_DIR`:

- `understand-guide.md` — PDF/HTML source
- `understand-study.json` — flashcards + quiz

Read `understand-explore.md` first. Do not web-search unless explore gaps require external docs.

### `understand-guide.md` schema

Follow [`templates/understand-guide.md`](../../templates/understand-guide.md).

Must include:

- `## Key concepts` — each entry: **Definition**, **Usage**, **Source** (`path:line` link), **Reference code** (fenced block — copy real source, ≤ 30 lines)
- Use citation fences exactly: ` ```startLine:endLine:relative/path` ` (content pasted from Read output)
- Mermaid diagram(s) when relationships are non-obvious (component map, request flow, state machine)
- `## Architecture` — explicit **Topology**: `single-node` | `distributed` | `hybrid` with evidence; include **Source** + snippet for key entry points where helpful
- Subsections: Components, Data flow, Boundaries, Operational notes
- `## FAQ` — 5–10 Q&A pairs; optional **Source** + snippet per answer

**Reference code rules:** Read the file, paste the actual lines — do not paraphrase code. Snippet must match the cited `path:line` range.

### `understand-study.json` schema

Follow [`templates/understand-study.json`](../../templates/understand-study.json).

| Field | Rules |
|-------|--------|
| `flashcards` | ≥ 8 cards; mix `concept` and `implementation` tags |
| `flashcards[].refs` | **Required** for `implementation` cards; optional for concept — `{path, line, endLine?}` repo-relative |
| `flashcards[].code` | **Required** for `implementation` cards when a short snippet helps (≤ 20 lines) |
| `quiz` | ≥ 6 questions; mix concept + code; 4 choices each; `answer` is 0-based index |
| `quiz[].refs` | At least one ref on implementation-tagged questions |
| `quiz[].code` | Optional snippet shown in quiz review |

Build script injects `project_path` from session JSON and turns refs into **clickable IDE links** (`vscode://` / `cursor://`).

## Orchestrator rules

- Spawn Azusa then Jun — do not self-analyze
- After Jun: run build script; report paths to PDF + HTML
- `--yolo` has no effect (no auto-skip)
- Skip [`skills/teammate-flow`](../teammate-flow/SKILL.md)
- Read-only on **application source**; session artifacts only

## Quality bar

- **Concepts**: precise definitions a new contributor can use in conversation
- **Architecture**: answer "single laptop CLI" vs "multi-service" explicitly
- **FAQ**: practical questions with short, grounded answers — not a repeat of the glossary verbatim
- **Flashcards**: front = prompt; back = concise answer; **`refs` + `code`** for implementation cards
- **Quiz**: plausible distractors; `explanation` + optional **`refs` / `code`**
