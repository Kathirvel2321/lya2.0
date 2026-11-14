# LYA Remote Runner

Send coding tasks to this Windows laptop from your iPhone via Telegram, get
results back. Long polling only — no inbound ports, no webhooks, nothing to
expose.

**Library choice: python-telegram-bot v21.6** (pinned). Chosen over aiogram 3
because its `Application` lifecycle + `CallbackQueryHandler` map directly onto
this bot's confirmation-button flow with less glue code, and `run_polling`
handles reconnection/backoff internally.

## Setup (one time)

```powershell
cd runner
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.json config.local.json
notepad config.local.json     # real project paths + agent command
notepad .env                  # TELEGRAM_BOT_TOKEN, OWNER_CHAT_ID (already present)
```

Then start it (leave the window open):

```powershell
cd runner
.venv\Scripts\python.exe main.py
```

You'll get "LYA runner online" in Telegram.

## Commands

| Command                   | What it does                                                  |
| ------------------------- | ------------------------------------------------------------- |
| /status                   | uptime, current job, last result                              |
| /projects                 | allowlisted project names (never paths)                       |
| /run \<project\> \<task\> | start one coding task (agent command runs inside the project) |
| /stop                     | kill the running job (whole process tree)                     |
| /diff \<project\>         | git diff --stat + changed file names                          |
| /undo \<project\>         | inline-button confirm, then revert to the pre-job checkpoint  |

Tasks mentioning destructive verbs (delete/undo/push/deploy/install) require a
confirmation button. Buttons expire after 60 seconds.

## Security model (summary)

1. Owner-only: sender id AND chat id must both equal OWNER_CHAT_ID; everyone
   else is dropped silently.
2. Allowlist: tasks run only inside configured project roots. Real paths are
   resolved; `..`, symlinks, junctions, UNC and cross-drive escapes are refused.
3. No shell: user text is one argv element (`--task <text>`) passed with
   `shell=False`. It is never interpreted by a shell.
4. One job at a time; 20-minute default hard timeout kills the whole tree
   (taskkill /T on Windows).
5. Git checkpoint before every job; non-git projects are refused. /undo
   resets to the `lya-runner-backup` branch.
6. Destructive verbs need a fresh inline-button confirmation (60 s TTL).
7. Rate limit (default 10/min) against runaway loops.
8. Output is ANSI-stripped, secret-redacted and truncated to Telegram limits.
9. Audit log (logs/audit.log, rotating): command name, project, outcome only —
   never message bodies or output.

## Real-device checklist (run these yourself)

1. `/status` from your iPhone → uptime shown.
2. `/run alpha add a comment to f.txt` on a throwaway test repo → "Started",
   then a completion summary.
3. `/stop` mid-job → confirms kill; job shows outcome `stopped`/`failed`.
4. `/diff alpha` → changed files; `/undo alpha` → press Confirm → checkpoint
   restored.
5. From a second Telegram account, send any command → nothing happens at all.
6. Turn Wi-Fi off mid-job → polling retries with backoff (library-handled);
   when connection returns the next message notes the recovery. Note: a job
   killed by losing network cannot be resumed; check with /status.

## Honest limits

- If the laptop is off/asleep, the bot is simply silent — there is no server
  anywhere; Telegram just queues nothing. Messages sent while offline are
  dropped (drop_pending_updates=True) by design.
- The agent command is a placeholder until you tell me which coding tool to
  launch; /run will not work until `agent_command` in config.local.json is set.
- Security items 1-3, 5-9 are mock-tested only until you run the real-device
  checklist above; item 4's tree-kill is unit-mocked plus a real taskkill
  invocation path on Windows.
- I have not run the bot against the real Telegram API with your token; that
  is deliberately left for you, on your phone, per the checklist.
