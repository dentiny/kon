---
name: interactive-session
description: Route plain-text user messages while a /kon:begin session is open. Reuse the same session JSON — never init a second session for sub-turns.
---

# Interactive Session

**Owner**: orchestrator
**Consumers**: `/kon:begin` — all follow-up messages **without** a `/kon:` prefix

**Core principles (always):** follow [`skills/core-principles`](core-principles/SKILL.md) — first principles (don't hide the issue); simplest, most concise correct solution.

## Detect active session

```bash
python3 $KON_ROOT/scripts/kon_session.py active
# prints session id, or nothing
```

Active = most recent `command: "/kon:begin"` with `status` in `in_progress` | `waiting` for this project.

If `active` prints an id → user is in interactive mode unless they sent an explicit `/kon:*` command.

## Golden rule

**Never call `init` for sub-turns inside a begin session.**

Append work to the existing session:

```bash
python3 $KON_ROOT/scripts/kon_session.py log-turn \
  --id <begin-sid> --agent User --summary "<one line paraphrase>"

python3 $KON_ROOT/scripts/kon_session.py complete-agent \
  --id <begin-sid> --agent Azusa --summary "<one sentence>"
```

Begin sessions stay `in_progress` after each agent — only `/kon:finish` closes them.

## Intent routing (plain text)

| Signal | Route | Agent(s) |
|--------|-------|----------|
| Question about **our code** / "where is…" / "how does X work" | ask | 🎸 Azusa read-only |
| **External** docs / API / "look up…" | research | 📚 Jun |
| **Review** diff / "check my changes" | review | 📝 Mio |
| **Review PR** / holistic PR check / "review this PR" | review-pr | 📝 Mio |
| **Summarize issue** / GitHub issue thread | describe-issue | 📚 Jun |
| **Bug** / failing test / regression / "X is broken" | debug | 🎸 Azusa → 🍰 Mugi → User → 🎶 Yui → 🧹 Sawako → 📝 Mio |
| **Small** fix, typo, one file | quick | 🎶 Yui → 📝 Mio |
| **Feature**, multi-file, unclear scope | team | Azusa → pre-plan gate → Mugi → … |
| **Design** first, no code yet | design | Azusa → pre-plan gate → Mugi → debate |
| **Todo** / "remind me to…" / add to list | todo | run `kon_todo.py add` (no agent) |
| Greeting / meta / "what can you do" | orchestrator | no agent spawn — reply + `log-turn` User |

When unsure between go and quick, ask once in prose — do not widget.

## YOLO

If the begin session was started with `--yolo`, append `--yolo` to any routed pipeline (go/team/design/quick/debug).

## Explicit `/kon:*` during begin

Allowed — route in-place on the **same begin session id**. `/kon:finish` closes the session.

**Never call `init`** while `kon_session.py active` prints an id (hook and CLI both refuse).
Use `log-turn --agent User` for the command, then run the workflow on that session id.

## Logging

Hooks auto-record `/kon:begin` turns — no manual CLI needed for ordinary chat:

- `log_begin_prompt.py` (`beforeSubmitPrompt`) → User line from each message
- `log_begin_response.py` (`afterAgentResponse`) → Assistant line from each reply
- `on_subagent_stop.py` → named agent line when a Task subagent finishes

Orchestrators may still call `complete-agent` for explicit pipeline steps; hooks dedupe identical back-to-back entries.

User message paraphrase → optional `log-turn --agent User` (hook already logs the raw prompt).

## What not to do

- Do not create a second session JSON for ask/research/review inside begin
- Do not auto-run `/kon:finish` after each sub-turn
- Do not skip Mio on code changes (quick/go paths)
