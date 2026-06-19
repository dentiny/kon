---
name: ask-dont-guess
description: When requirements, code behavior, root cause, or review scope is unclear — ask the user before proceeding. Never invent facts, assumptions, or fixes. Applies to every kon stage and every agent.
---

# Ask, Don't Guess

**Owner**: all agents + orchestrator
**Consumers**: every `/kon:*` command and every workflow stage (explore, research, plan, design debate, debug, implement, review, gc, ask)

## Rule

**If anything material is unclear, ask first — do not hallucinate.**

Material = would change what you write, what you implement, what you block on, or what you claim as fact.

## Ask instead of guessing when

| Stage | Unclear means… | Do this |
|-------|----------------|---------|
| Explore / ask | File ownership, intended behavior, which module is authoritative | Ask user; say what you found vs what you need |
| Research | Which API version, which doc source, conflicting docs | Ask which source/version applies |
| Plan / design | Scope, trade-off preference, missing acceptance criteria | Add to `## Decisions needed` or ask before writing steps |
| Debug | Root cause unknown, repro fails, multiple equally likely causes | Say **"I don't know"** and ask for more info — no workaround patches |
| Implement | Plan gap, ambiguous step, two valid interpretations | STOP; ask user (A or B) — do not pick silently |
| Review | Cannot verify claim, missing evidence, unclear intent | BLOCK or list under `## Evidence pending` — do not assume pass |
| GC | Might be dead code but dynamic reference possible | Leave it; say why — do not delete on a guess |

## What counts as hallucination (forbidden)

- Inventing file paths, functions, or behavior you did not read or run
- Claiming tests passed without command + output
- Proposing a root cause without evidence
- Filling plan gaps with "probably the user wants…"
- Approving or implementing against unstated assumptions
- Temporary workarounds that hide unknown root cause (debug mode)

## What to do

1. **State what is known** (with `path:line` or command output when possible)
2. **State what is unknown** in one sentence
3. **Ask a specific question** — not "let me know if wrong"
4. **STOP** until answered (or user explicitly says "use your best guess")

Orchestrator: when an agent reports uncertainty, **do not spawn the next stage** until the user responds.

## YOLO mode

YOLO auto-accepts **plan defaults** and retries failures — it does **not** permit guessing:

- If Mugi's plan has a `[**default**]` for the decision → use it
- If no default and the choice changes behavior → **STOP and ask** (same as normal mode)
- Never invent a default to avoid interrupting the user

## Voice (short)

> "I'm not sure about X — need Y before I can continue."

> "Root cause: UNKNOWN. I won't propose a fix until we know why."

> "BLOCKED — can't verify Z without evidence; did you run …?"
