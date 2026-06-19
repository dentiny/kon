---
description: Bug investigation pipeline — reproduce with runtime evidence before fixing. Azusa traces the bug, Yui reproduces and applies a minimal fix, Mio reviews.
---

# /kon:debug

Systematic bug investigation. Gather **runtime evidence** (repro, logs, exit codes)
before changing code. Skips Mugi planning — writes `.kon/debug-<session-id>.md` instead
of a full implementation plan.

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
   No fixes — exploration only.
2. **Orchestrator** — write `.kon/debug-<SESSION_ID>.md` from Azusa's findings:
   - **Symptoms** — what the user sees
   - **Repro steps** — concrete commands or UI steps
   - **Hypotheses** — ranked suspects with file:line pointers
   - **Acceptance** — how we know it's fixed (test name, expected output, log line)
3. **🎶 Yui** — **reproduce first** (mandatory), document evidence, then minimal fix.
   - Run repro steps; capture command + exit code + relevant output
   - Only then edit code — smallest diff that addresses the root cause
   - No drive-by refactors or scope expansion
4. **📝 Mio** — full 9-item strict-review (same as `/kon:team`)
5. **Manual testing** — After Mio approves, user verifies the fix works
6. **📋 Nodoka** — session summary (auto via [`/kon:summarize`](summarize.md)).

Pass `DEBUG_FILE: .kon/debug-<SESSION_ID>.md` to Azusa and Yui in task prompts.

## Evidence rules (hard)

- **No fix without repro evidence** — Yui must show failing repro (or explain why repro is impossible and what proxy evidence was used).
- **Minimal diff** — debug fixes only what is broken; no "while I'm here" cleanup.
- **Root cause over symptom** — prefer fixing the cause; if only a symptom patch is possible, say so in the debug file.
- **Do not skip Mio** — even one-line fixes get full review.

## Debug notes template

Orchestrator writes this after Azusa, before Yui:

```markdown
# Debug: <one-line symptom>

**Session**: <session-id>
**Command**: /kon:debug

## Symptoms
<what fails, for whom, since when>

## Repro steps
1. ...
2. ...

## Hypotheses
1. [likely] `path/file.py:42` — ...
2. [possible] ...

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

On create: `command: "/kon:debug"`, `steps_pending: ["Azusa", "Yui", "Mio", "Nodoka"]`.

## Orchestrator rules

- **Narration:** use 🌸 Ui for opening, closing, stuck-point beats. Follow [`skills/narration`](https://github.com/dentiny/kon/blob/main/skills/narration/SKILL.md).
- **Model inheritance:** Do NOT pass `model` parameter when spawning subagents — let them inherit parent's model
- **The orchestrator does not implement or debug** — spawn agents via Task tool.
- After Mio approves, draft a commit message per [`skills/commit-message`](https://github.com/dentiny/kon/blob/main/skills/commit-message/SKILL.md). **Do not `git commit`.**
- Remind user to test the fix manually.

## Comparison

| Item | `/kon:debug` | `/kon:quick` | `/kon:team` |
|------|-------------|-------------|-----------|
| Azusa explore | ✅ bug trace | ❌ | ✅ |
| Mugi plan | ❌ (debug notes) | ❌ | ✅ |
| Repro before fix | ✅ mandatory | ❌ | ❌ |
| Yui implement | ✅ minimal | ✅ | ✅ |
| Mio review | ✅ full (9) | ✅ quick (4) | ✅ full |
| Testing | Manual | Manual | Manual |
| Best for | bugs / regressions | tiny tweaks | features |
