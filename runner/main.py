"""LYA Remote Runner entry point.

Long polling only - no inbound ports, no webhooks. python-telegram-bot v21
was chosen over aiogram because its Application lifecycle matches this small
one-owner bot with less ceremony and its run_polling handles backoff
internally.

Run from the runner folder (inside its venv):
    .venv/Scripts/python.exe main.py
"""
from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT.parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

from runner import config as cfg                     # noqa: E402
from runner.audit import Auditor                     # noqa: E402
from runner.commands import Handlers                 # noqa: E402
from runner.jobs import JobManager                   # noqa: E402


def main():
    try:
        token, chat_id = cfg.owner_ids()
        local = cfg.load_local()
    except cfg.ConfigError as exc:
        # Variable names only; values are never echoed anywhere.
        print(f"[runner] configuration problem: {exc}", file=sys.stderr)
        return 2

    auditor = Auditor(HERE / "logs")
    manager = JobManager(cfg.agent_command(local), cfg.timeout_seconds(local),
                         auditor=auditor)
    handlers = Handlers(local, manager, auditor)
    handlers.bind_owner(chat_id)

    from telegram.ext import (Application, CallbackQueryHandler,
                              CommandHandler, MessageHandler, filters)

    app_holder = {}

    def send_sync(text):
        """Deliver a job summary from the manager's worker thread."""
        app = app_holder.get("app")
        if app is None:
            return
        try:
            coro = app.bot.send_message(chat_id=chat_id, text=text)
            fut = asyncio.run_coroutine_threadsafe(coro, app.bot._loop
                                                   if hasattr(app.bot, "_loop") else loop_ref["loop"])
            fut.result(timeout=20)
        except Exception:
            handlers.note_network_drop()

    handlers.bind_sender(send_sync)
    manager.on_finish = handlers.on_job_finish

    async def post_init(application):
        loop_ref["loop"] = asyncio.get_running_loop()
        await application.bot.send_message(chat_id=chat_id, text="LYA runner online")

    loop_ref = {}
    app = Application.builder().token(token).post_init(post_init).build()
    app_holder["app"] = app

    app.add_handler(CommandHandler(["start"], handlers.cmd_start))
    app.add_handler(CommandHandler(["help"], handlers.cmd_help))
    app.add_handler(CommandHandler(["status"], handlers.cmd_status))
    app.add_handler(CommandHandler(["projects"], handlers.cmd_projects))
    app.add_handler(CommandHandler(["run"], handlers.cmd_run))
    app.add_handler(CommandHandler(["stop"], handlers.cmd_stop))
    app.add_handler(CommandHandler(["diff"], handlers.cmd_diff))
    app.add_handler(CommandHandler(["undo"], handlers.cmd_undo))
    app.add_handler(CallbackQueryHandler(handlers.on_callback))
    # Strangers: drop silently. No reply, no echo of their text.
    app.add_handler(MessageHandler(filters.ALL & ~filters.User(user_id=chat_id),
                                   handlers.stranger))
    return app.run_polling(drop_pending_updates=True) or 0


if __name__ == "__main__":
    sys.exit(main())
