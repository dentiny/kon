---
name: interactive-session
description: Route plain-text user messages while a /kon:begin session is open. Reuse the same session JSON — never init a second session for sub-turns.
---

# Interactive Session

**Owner**: orchestrator
**Consumers**: `/kon:begin` — all follow-up messages **without** a `/kon:` prefix

## Detect active session

```bash
python3 ~/Desktop/kon/scripts/kon_session.py active
# prints session id, or nothing
```

Active = most recent `command: "/kon:begin"` with `status` in `in_progress` | `waiting` for this project.

If `active` prints an id → user is in interactive mode unless they sent an explicit `/kon:*` command.

## Golden rule

**Never call `init` for sub-turns inside a begin session.**

Append work to the existing session:

```bash
python3 ~/Desktop/kon/scripts/kon_session.py log-turn \
  --id <begin-sid> --agent User --summary "<one line paraphrase>"

python3 ~/Desktop/kon/scripts/kon_session.py complete-agent \
  --id <begin-sid> --agent Azusa --summary "<one sentence>"
```

Begin sessions stay `in_progress` after each agent — only `/kon:finish` closes them.

## Intent routing (plain text)

| Signal | Route | Agent(s) |
|--------|-------|----------|
| Question about **our code** / "where is…" / "how does X work" | ask | 🎸 Azusa read-only |
| **External** docs / API / "look up…" | research | 📚 Jun |
| **Review** diff / "check my changes" | review | 📝 Mio |
| **Small** fix, typo, one file | quick | 🎶 Yui → 📝 Mio |
| **Feature**, multi-file, unclear scope | go or team | full pipeline |
| **Design** first, no code yet | design | Azusa → Mugi → debate |
| Greeting / meta / "what can you do" | orchestrator | no agent spawn — reply + `log-turn` User |

When unsure between go and quick, ask once in prose — do not widget.

## YOLO

If the begin session was started with `--yolo`, append `--yolo` to any routed pipeline (go/team/design/quick).

## Explicit `/kon:*` during begin

Allowed as escape hatch. `/kon:finish` closes the begin session.

Running `/kon:go` etc. **may** supersede begin (new `init`) — prefer plain text routing instead.

## Logging

Every routed agent step → `complete-agent` on the **begin session id**.

User message paraphrase → `log-turn --agent User` before spawning agents.

## What not to do

- Do not create a second session JSON for ask/research/review inside begin
- Do not auto-run `/kon:finish` after each sub-turn
- Do not skip Mio on code changes (quick/go paths)
