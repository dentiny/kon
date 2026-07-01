---
name: core-principles
description: Kon's two highest-priority principles for design, implementation, and review — first principles (don't hide the issue) and the simplest, most concise correct solution. Applies to every agent, skill, and workflow stage.
---

# Core Principles

**Owner**: all agents + orchestrator
**Consumers**: every agent, every skill, every `/kon:*` stage (explore, research, plan, design, debug, implement, review, gc, summarize)

These two principles rank **above** conventions, completeness, clever architecture, and "how we always do it."

## 1. Think from first principles — don't hide the issue

- Restate the **actual** problem in plain language before choosing an approach.
- Every decision, step, and changed line must trace back to that problem — or it is inherited complexity / cargo-cult.
- **Don't hide the issue:** unclear intent, missing evidence, or unverified claims → ask or stop — never assume, paper over, or defer with "we'll fix it later."
- Follow [`skills/ask-dont-guess`](ask-dont-guess/SKILL.md).

## 2. Simplest, most concise correct solution

- Among all ways that **correctly** solve the problem, choose the one with the fewest moving parts.
- Minimum that satisfies acceptance criteria — not a generalized version "for later."
- When trade-offs are close, **simplicity wins**. Reject layers, abstractions, and defensive bloat unless a concrete requirement demands them.

## By stage

| Stage | First principles | Simplicity |
|-------|------------------|------------|
| Explore / research | Report what is provable; unknown stays unknown | Report only what downstream needs — no encyclopedic dumps |
| Plan / design | Restate problem; use `## Decisions needed` instead of inventing scope | Default tie-breaker: fewer files, fewer steps, flat over layered |
| Implement | Code only what the step requires | Smallest correct diff |
| Review | Default BLOCKED until the change proves it solves the real problem | Block complexity without first-principles justification |
| GC / cleanup | Remove only verified dead weight | Simplify without changing behavior |
| Summarize | Record what happened — no invented outcomes | Concise; no padding |

## Related skills

- Unclear? Ask: [`skills/ask-dont-guess`](ask-dont-guess/SKILL.md)
- Plan stress-test: [`skills/design-debate`](design-debate/SKILL.md)
- Review checklist: [`skills/strict-review`](strict-review/SKILL.md) (item 1: simplest correct implementation)
- Team pipeline: [`skills/teammate-flow`](teammate-flow/SKILL.md)
