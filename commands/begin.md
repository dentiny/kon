---
description: Start an interactive kon session. Plain chat is routed by intent — no /kon: prefix needed until /kon:finish.
---

# /kon:begin

Enter **interactive mode** for this project. One dashboard session stays open; you talk normally;
the orchestrator picks agents and workflows from your message.

## Usage

```
/kon:begin
/kon:begin add rate limiting to the API
/kon:begin --yolo
```

Optional first argument is the **session goal** (shown on the dashboard). `--yolo` applies to routed pipelines.

## End the session

```
/kon:finish
```

Or click **✓** on the dashboard card. Same as closing any open session.

## Flow

1. **Orchestrator** — check for an existing begin session **before** calling `init`:
   ```bash
   python3 $KON_ROOT/scripts/kon_session.py active
   # prints session id if one is already open, else empty
   ```
   - If a session id is printed → **reuse it**. Do **not** call `init`. The `init_kon_session` hook
     already created the session on `beforeSubmitPrompt`; a second `init` would supersede it.
   - If empty → create one:
     ```bash
     python3 $KON_ROOT/scripts/kon_session.py init \
       --command "/kon:begin" --task "<goal or interactive session>"
     ```

   `steps_pending` is empty; `mode=interactive`; `status=in_progress` until `/kon:finish`.
   A `turns: []` list is also initialised — each User `log-turn` adds a dot to the dashboard bar.

2. **Orchestrator** — confirm: "Interactive session started. Talk normally — `/kon:finish` when done."

3. **Each user message (no `/kon:` prefix)** while a begin session is open:
   - Read [`skills/interactive-session`](../skills/interactive-session/SKILL.md)
   - **Do not** call `init` again — reuse the active begin session id
   - Route intent → spawn agents → `log-turn` / `complete-agent` on **same** session id

4. **Explicit `/kon:*` during begin** — still works (escape hatch). Prefer not to; `/kon:finish` always closes the begin session.

## Session rules

| Action | Allowed? |
|--------|----------|
| Plain text messages | ✅ routed by interactive-session |
| `log-turn` / `complete-agent` on begin session id | ✅ |
| Second `/kon:begin` while one is open | Supersedes the old begin session (new init) |
| `init` for ask/research/review during begin | ❌ — route in-place, same session |
| Auto-complete when an agent finishes | ❌ — begin stays `in_progress` until finish |

## Comparison

| Item | `/kon:begin` + plain chat | `/kon:go <task>` |
|------|-------------------------|------------------|
| Session count | One open session | One shot per command |
| User syntax | Natural language | Single task string |
| Dashboard | One card, many log lines | One card per command |
| Close | `/kon:finish` | `/kon:finish` or auto-supersede |

## Orchestrator rules

- **Narration:** 🌸 Ui opening/closing per [`skills/narration`](../skills/narration/SKILL.md)
- **Skip teammate-flow** for the begin command itself — read interactive-session for routing
- **Always** run `active` before `init` — the hook may have already created the session
- Each user message: `log-turn --agent User --summary "<paraphrase>"` — this auto-adds a turn dot to the dashboard bar
