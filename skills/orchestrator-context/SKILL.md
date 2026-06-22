---
name: orchestrator-context
description: Keep orchestrator chat lean — artifacts hold full agent output; orchestrator routes by file pointer only. Applies to all /kon:* commands that spawn Task subagents.
---

# Orchestrator Context Contract

**Owner**: orchestrator
**Consumers**: all `/kon:*` commands that spawn Task subagents (team, design, quick, debug, ask, research, review, begin routing, …)

Subagent Task returns enter the orchestrator's context window. **Do not amplify bloat** by quoting, restating, or forwarding that output in chat or in later spawn/resume prompts.

**Full output lives in artifacts. Orchestrator holds pointers only.**

## Artifact map

| Agent | Full output artifact | When |
|-------|---------------------|------|
| 🎸 Azusa | `sessions/<SID>/explore.md` | `/kon:team`, `/kon:design` (subagentStop hook) |
| 🎸 Azusa | `sessions/<SID>/debug.md` | `/kon:debug` (orchestrator writes once after Azusa) |
| 📚 Jun | `.kon/research.md` | external research steps |
| 🍰 Mugi | `PLAN_FILE` (`.kon/plan-<SID>.md` or session plan) | after plan step |
| 📝 Mio | `sessions/<SID>/review.md` | team, quick, review, debug (subagentStop hook) |
| 📝 Mio | `sessions/<SID>/pr-review.md` | `/kon:review-pr` |
| 📚 Jun | `sessions/<SID>/issue-summary.md` | `/kon:describe-issue` |
| 📋 Nodoka | `sessions/<SID>/summary.md` | `/kon:summarize` |

Resolve paths:

```bash
SID="<session-id>"
SESSION_DIR=$(python3 $KON_ROOT/scripts/kon_session.py session-dir --id "$SID")
REVIEW_FILE=$(python3 $KON_ROOT/scripts/kon_session.py artifact-path --id "$SID" --name review.md)
EXPLORE_FILE=$(python3 $KON_ROOT/scripts/kon_session.py artifact-path --id "$SID" --name explore.md)
```

## Orchestrator rules

1. **User-facing messages** — one line per agent step (verdict + artifact path). Never paste subagent output into assistant messages.
2. **Next spawn / resume prompts** — file pointers + milestone/delta only. Never forward must-fix lists, explore findings, or review bodies through the orchestrator.
3. **Impl-loop handoffs** — Yui and Mio **resume** and read `review.md` directly. See [`skills/failure-handling`](../failure-handling/SKILL.md).
4. **Plan approval** — present goal + step/milestone count + `## Decisions needed` bullets; do not dump the full plan into chat (user opens `PLAN_FILE`).
5. **After Task returns** — call `complete-agent` with a **one-sentence** summary; do not copy the Task body into the summary field.

## Spawn prompt templates (pointers only)

**Mugi (after Azusa on team/design):**

```text
PLAN_FILE: .kon/plan-<SID>.md
EXPLORE_FILE: sessions/<SID>/explore.md
Read EXPLORE_FILE and .kon/research.md (if present). Write the plan. No implementation.
```

**Yui resume (after Mio block):**

```text
Resume. Read must-fix from sessions/<SID>/review.md — fix each by number.
PLAN_FILE: …  Milestone: N. Report files changed only.
```

**Mio resume:**

```text
Resume. Re-review milestone N. Prior must-fix: sessions/<SID>/review.md.
Verify each item with git diff evidence. Full hook-compliant output.
```

## Subagent handoff block

Every subagent ends with **`## Orchestrator handoff`** (≤5 lines) so the orchestrator can route without re-reading the full body:

```markdown
## Orchestrator handoff
- **Verdict**: APPROVED | BLOCKED | done | …
- **Artifact**: `sessions/<SID>/review.md` (or other path)
- **Next**: resume Yui | spawn Mugi | wait for user | …
- **Note**: one sentence only
```

Hooks persist the **full** output to artifacts; the handoff block is for orchestrator routing only.

## Long sessions (`/kon:begin`)

When a begin session routes into team/design/debug, the same rules apply.

For **design → implement**, prefer a **new chat** + `/kon:team` with existing `PLAN_FILE` to drop explore/plan debate from orchestrator context.

## Related

- Task resume: [`skills/teammate-flow`](../teammate-flow/SKILL.md)
- Mio blocks: [`skills/failure-handling`](../failure-handling/SKILL.md)
- Session artifacts: [`skills/session-tracking`](../session-tracking/SKILL.md)
