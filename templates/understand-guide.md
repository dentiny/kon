# Codebase guide: <project name>

**Session**: <session-id>
**Generated**: /kon:understand-codebase

## Key concepts

Glossary of domain and technical terms used in this codebase.

### <Concept name>

| | |
|---|---|
| **Definition** | <precise meaning in this repo> |
| **Usage** | <where/how it appears in practice> |
| **See also** | `path:line`, related terms |

*(Repeat for each concept — aim for 6–15 entries.)*

## Concept map

```mermaid
flowchart TB
  A[Concept A] --> B[Concept B]
  B --> C[Concept C]
```

## Architecture

| | |
|---|---|
| **Topology** | `single-node` \| `distributed` \| `hybrid` |
| **Summary** | <one paragraph: what runs where> |

### Components

| Component | Role | Key paths |
|-----------|------|-----------|
| | | |

### Data flow

```mermaid
sequenceDiagram
  participant User
  participant App
  User->>App: example request
  App-->>User: response
```

### Boundaries

- **In scope**: …
- **External systems**: …
- **Persistence**: …

### Operational notes

- How to run locally
- Config / env vars
- Extension points

## FAQ

Common questions a new contributor would ask — **concepts and architecture only** (implementation how-tos belong in flashcards/quiz, not here).

*(Aim for 5–10 Q&A pairs.)*

### Q: <question a newcomer would ask>

<Answer in 2–4 sentences. Cite `path:line` or architecture evidence when helpful.>

### Q: <another question>

<Answer.>

*Good FAQ topics: naming that confuses people, "why is X separate from Y?", startup order, where state lives, what is *not* in this repo, single-node vs distributed implications.*

## Sources

Based on `understand-explore.md` from this session. Evidence paths cited inline.
