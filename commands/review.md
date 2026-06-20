---
description: Code review only — Mio runs strict-review on uncommitted or staged diff. No implementation.
---

# /kon:review

Review code changes without implementing. 📝 Mio applies the full 7-item golden checklist from
[`skills/strict-review`](../skills/strict-review/SKILL.md) on the current diff.

**Highest priority in every review:** first-principles grounding and simplicity — see checklist item 1 and the skill's opening section.

**Unclear scope or intent?** Ask the user — do not assume or invent context. Follow [`skills/ask-dont-guess`](../skills/ask-dont-guess/SKILL.md).

**Default scope:** uncommitted changes (`git diff HEAD` + untracked files listed in summary).
Use flags to narrow scope.

## Usage

```
/kon:review                          # review all uncommitted changes
/kon:review --staged                 # staged only (git diff --cached)
/kon:review --mode=design-preview    # checklist items 1 + 4 only
/kon:review --mode=compliance-only   # items 4–8 only
```

With an optional rubric (🍰 Mugi writes criteria first):

```
/kon:review --rubric <what to check>
```

## Scope boundary

- **Review only** — verdict + must-fix. Do not edit code.
- **No unit tests** — automated testing does not run. Review is code analysis only.
- If the user wants fixes, offer `/kon:quick` or `/kon:team` after Mio finishes.
- Commit/staging cleanliness is not a checklist item — review the diff content only.

## Flow

1. **Orchestrator** — create session: `command: "/kon:review"`, `steps_pending: ["Mio"]`
   (add `"Mugi"` before `"Mio"` when `--rubric` is used).
2. **`--rubric` only:** spawn **🍰 Mugi** in review-rubric mode → `sessions/<SESSION_ID>/review-rubric.md`.
3. **📝 Mio** — read diff and optional rubric; follow `agents/Mio.md` + `skills/strict-review`.
   - `git diff HEAD` (default) or `git diff --cached` (`--staged`)
   - List untracked files relevant to the task so Mio knows what to read
4. **Orchestrator** — run quality check (`teammate_role: Mio`), update session (`complete-agent` → `completed`), present verdict.
   - Full review is saved to **`sessions/<SESSION_ID>/review.md`** (subagentStop hook — open locally in your browser/editor).
5. No automated testing. No Nodoka unless `/kon:summarize`.

## Orchestrator rules

- **Do not review yourself** — spawn Mio via Task tool
- **Model inheritance:** Do NOT pass `model` parameter when spawning Mio — let subagent inherit parent's model
- **Narration:** 🌸 Ui opening/closing per [`skills/narration`](../skills/narration/SKILL.md)
- **Do not run `git commit` or `git push`**
- Skip [`skills/teammate-flow`](../skills/teammate-flow/SKILL.md) — review is Mio-only (optional Mugi rubric pass)

## Comparison

| Item | `/kon:review` | `/kon:quick` | `/kon:team` |
|------|---------------|--------------|-----------|
| Mio review | ✅ full (or mode subset) | ✅ 3-item | ✅ full (7 items) per milestone |
| Yui implement | ❌ | ✅ | ✅ |
| Testing | ❌ | Manual | Manual |
| Writes code | ❌ | ✅ | ✅ |
