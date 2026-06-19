---
description: Bug investigation pipeline — reproduce with runtime evidence before fixing. Azusa investigates, Mugi proposes multiple fixes, user approves, then Yui implements. Mio reviews.
---

# /kon:debug

Systematic bug investigation. Gather **runtime evidence** (repro, logs, exit codes),
analyze root cause, propose **multiple fix approaches**, get user approval, then fix.

Use when something is **broken** (failing test, wrong output, crash, regression).
For "how does X work?" use [`/kon:ask`](ask.md). For new features use [`/kon:team`](team.md).

## Usage

```
/kon:debug <bug description>
/kon:debug --yolo <bug description>
```

Examples:

```
/kon:debug dashboard renderSession shows undefined for session dots
/kon:debug pytest test_kon_session.py::test_supersede fails after last commit
/kon:debug API returns 500 when email field is empty
```

## Flow

1. **🎸 Azusa** — investigate: symptoms → suspect code paths, related files, repro hints.
   - No fixes — exploration only.
   - **If root cause cannot be determined, say "I don't know" and stop** — do not guess or propose workarounds.
2. **Orchestrator** — write `.kon/debug-<SESSION_ID>.md` from Azusa's findings:
   - **Symptoms** — what the user sees
   - **Repro steps** — concrete commands or UI steps
   - **Root cause analysis** — why this is happening
   - **Related code** — key files and functions involved
3. **🍰 Mugi** — propose multiple fix approaches:
   - Read Azusa's investigation and debug file
   - **If Azusa couldn't find root cause: say "Cannot propose fixes without understanding root cause" and stop**
   - Otherwise: Propose 2-3 different fix approaches with trade-offs
   - Compare: complexity, risk, maintainability, scope
   - Recommend one approach with reasoning
   - Write proposals to debug file under `## Fix Proposals` section
4. **User confirms fix approach** (MANDATORY):
   - Orchestrator presents Mugi's proposals
   - **STOP and wait for user to select approach** (or suggest alternative)
   - Update session: set `steps_waiting: ["User"]`, `status=waiting`
   - Only proceed after user approval (even in `--yolo` mode)
5. **🎶 Yui** — **reproduce first** (mandatory), document evidence, then implement approved fix.
   - Run repro steps; capture command + exit code + relevant output
   - Implement the user-approved approach only
   - Smallest diff that addresses the root cause
   - No drive-by refactors or scope expansion
6. **📝 Mio** — full 9-item strict-review (same as `/kon:team`)
7. **Manual testing** — After Mio approves, user verifies the fix works
8. **📋 Nodoka** — session summary (auto via [`/kon:summarize`](summarize.md)).

Pass `DEBUG_FILE: .kon/debug-<SESSION_ID>.md` to Azusa, Mugi, and Yui in task prompts.

## Evidence rules (hard)

- **No fix without repro evidence** — Yui must show failing repro (or explain why repro is impossible and what proxy evidence was used).
- **Multiple fix proposals required** — Mugi must propose at least 2 approaches before user decides.
- **User approval required** — Cannot proceed to implementation without user selecting a fix approach.
- **CRITICAL: Honesty over workarounds** — If root cause is not found, say "I don't know" and stop. **Never** propose temporary workarounds or band-aid fixes that hide the problem. A symptom patch without understanding the root cause is worse than no fix.
- **Minimal diff** — debug fixes only what is broken; no "while I'm here" cleanup.
- **Root cause over symptom** — prefer fixing the cause; if only a symptom patch is possible, say so in the debug file and explain why the root cause cannot be addressed.
- **Do not skip Mio** — even one-line fixes get full review.

## Debug notes template

Orchestrator writes this after Azusa, before Mugi:

```markdown
# Debug: <one-line symptom>

**Session**: <session-id>
**Command**: /kon:debug

## Symptoms
<what fails, for whom, since when>

## Repro steps
1. ...
2. ...

## Root cause analysis
<why this is happening — the actual cause, not just symptoms>

**CRITICAL**: If root cause cannot be determined after investigation, write:
```
Root cause: UNKNOWN

The investigation found the symptoms but could not identify the underlying cause.
Do not proceed with implementation. Recommend:
1. Gather more information: <what's needed>
2. Reproduce in isolation: <how>
3. Consult domain expert: <who/what>
```

Do NOT propose workarounds when root cause is unknown. Hiding problems is worse than admitting uncertainty.

## Related code
- `path/file.py:42` — <relevance>
- `path/other.py:10` — <relevance>

## Hypotheses
1. [likely] `path/file.py:42` — ...
2. [possible] ...

## Fix Proposals
<Mugi fills this section — multiple approaches with trade-offs>

| Aspect | Approach 1: <name> | Approach 2: <name> | Approach 3: <name> |
|--------|-------------------|-------------------|-------------------|
| **Changes** | <what needs to change> | <what needs to change> | <what needs to change> |
| **Pros** | • <advantage 1><br>• <advantage 2> | • <advantage 1><br>• <advantage 2> | • <advantage 1><br>• <advantage 2> |
| **Cons** | • <disadvantage 1><br>• <disadvantage 2> | • <disadvantage 1><br>• <disadvantage 2> | • <disadvantage 1><br>• <disadvantage 2> |
| **Risk** | Low/Medium/High | Low/Medium/High | Low/Medium/High |
| **Complexity** | Low/Medium/High | Low/Medium/High | Low/Medium/High |

### Recommended: Approach X
**Reasoning**: <why this approach is best given the context, risk tolerance, and maintainability goals>

## Acceptance
- [ ] `pytest path::test_name` passes
- [ ] <expected behavior in plain language>
```

## Failure handling

See [`skills/failure-handling`](https://github.com/dentiny/kon/blob/main/skills/failure-handling/SKILL.md) —
same 2-consecutive-same-issue limit applies to Mio's must-fix items.

## Session tracking

Pipeline command — set `status=waiting` when agents finish (not auto-completed).
Follow [`skills/session-tracking`](https://github.com/dentiny/kon/blob/main/skills/session-tracking/SKILL.md).

On create: `command: "/kon:debug"`, `steps_pending: ["Azusa", "Mugi", "User", "Yui", "Mio", "Nodoka"]`.

## Orchestrator rules

- **Narration:** use 🌸 Ui for opening, closing, stuck-point beats. Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
- **Model inheritance:** Do NOT pass `model` parameter when spawning subagents — let them inherit parent's model
- **The orchestrator does not implement or debug** — spawn agents via Task tool.
- **MANDATORY user confirmation:** After Mugi proposes fixes, STOP and wait for user to select approach before spawning Yui (even in `--yolo` mode)
- **Stop if root cause unknown:** If Azusa or Mugi indicate root cause cannot be determined, do NOT proceed to Yui. Present the uncertainty to user and ask for guidance.
- After Mio approves, draft a commit message per [`skills/commit-message`](https://github.com/dentiny/kon/blob/main/skills/commit-message/SKILL.md). **Do not `git commit`.**
- Remind user to test the fix manually.

## Comparison

| Item | `/kon:debug` | `/kon:quick` | `/kon:team` |
|------|-------------|-------------|-----------|
| Azusa explore | ✅ bug trace | ❌ | ✅ |
| Mugi plan | ✅ multiple fix proposals | ❌ | ✅ |
| User confirm fix | ✅ mandatory | ❌ | ✅ mandatory (plan) |
| Repro before fix | ✅ mandatory | ❌ | ❌ |
| Yui implement | ✅ minimal (approved fix) | ✅ | ✅ |
| Mio review | ✅ full (9) | ✅ quick (4) | ✅ full |
| Testing | Manual | Manual | Manual |
| Best for | bugs / regressions | tiny tweaks | features |
