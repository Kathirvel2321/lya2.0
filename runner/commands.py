"""Telegram command handlers. Owner-filtered; confirmations for danger verbs.

Unknown senders are dropped silently. Every outgoing message passes through
runner.security.redact/truncate.
"""
from __future__ import annotations

import re
import threading
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from runner import config as cfg
from runner import jobs as jobs_mod
from runner.security import (PathOutsideAllowlist, is_owner, redact,
                             resolve_inside, truncate)

DANGEROUS = re.compile(r"\b(undo|delete|push|deploy|install|format|rm)\b", re.I)
HELP_TEXT = ("/status - runner uptime and job state\n"
             "/projects - allowlisted projects\n"
             "/run <project> <task text> - start one coding task\n"
             "/stop - kill the running job\n"
             "/diff <project> - what changed\n"
             "/undo <project> - revert to the pre-job checkpoint (confirm)")


class Handlers:
    def __init__(self, local_cfg, manager, auditor):
        self.local = local_cfg
        self.manager = manager
        self.auditor = auditor
        self.started_at = time.time()
        self.projects = cfg.projects(local_cfg)
        self.owner_chat_id = None          # bound in bind_owner()
        self._rate: dict[int, list[float]] = {}
        self._rate_lock = threading.Lock()
        self._pending: dict[str, tuple[str, float]] = {}   # confirm id -> (project, ts)
        self._network_note = None

    def bind_owner(self, chat_id):
        self.owner_chat_id = chat_id

    # ---- guards ----------------------------------------------------------
    def _allow(self, update) -> bool:
        if not is_owner(update, self.owner_chat_id):
            self.auditor.log("ignored", "-", "sender-not-owner")
            return False
        if self._rate_limited():
            self.auditor.log("ratelimit", "-", "blocked")
            return False
        return True

    def _rate_limited(self):
        now = time.time()
        with self._rate_lock:
            window = self._rate.setdefault(0, [])
            window[:] = [t for t in window if now - t < 60]
            if len(window) >= cfg.rate_limit(self.local):
                return True
            window.append(now)
        return False

    async def _reply(self, update, text, **kw):
        # Every outbound line is redacted then truncated.
        from runner.security import truncate as _tr
        return await update.effective_message.reply_text(_tr(text), **kw)

    def note_network_drop(self):
        self._network_note = time.time()

    # ---- commands ---------------------------------------------------------
    async def cmd_start(self, update, context):
        if not self._allow(update):
            return
        await self._reply(update, "LYA runner online.\n" + HELP_TEXT)

    async def cmd_help(self, update, context):
        if not self._allow(update):
            return
        await self._reply(update, HELP_TEXT)

    async def cmd_status(self, update, context):
        if not self._allow(update):
            return
        import time as _t
        up = _t.time() - self.started_at
        hours, rem = divmod(int(up), 3600)
        mins = rem // 60
        state = self.manager.status_line()
        last = self.manager.last_result()
        parts = [f"Uptime: {hours}h {mins}m."]
        if state:
            parts.append(f"Running: {state['project']} ({state['elapsed']}s elapsed).")
        else:
            parts.append("No job running.")
        if last:
            parts.append(f"Last job: {last.outcome}, {last.changed_files} files changed, "
                         f"{last.elapsed}s.")
        if self._network_note:
            parts.append("(Recovered from a network drop earlier.)")
            self._network_note = None
        self.auditor.log("status", "-", "ok")
        await self._reply(update, "\n".join(parts))

    async def cmd_projects(self, update, context):
        if not self._allow(update):
            return
        self.auditor.log("projects", "-", "ok")
        await self._reply(update, "Projects: " + ", ".join(sorted(self.projects)))

    # ---- confirmations ----------------------------------------------------
    def _confirm_keyboard(self, request_id):
        kb = [[InlineKeyboardButton("Confirm", callback_data=f"confirm:{request_id}"),
               InlineKeyboardButton("Cancel", callback_data=f"cancel:{request_id}")]]
        return InlineKeyboardMarkup(kb)

    def _pending_pop(self, request_id):
        entry = self._pending.pop(request_id, None)
        if entry is None:
            return None
        project, ts = entry
        if time.time() - ts > 60:
            return None                       # expired
        return project

    # ---- run ---------------------------------------------------------------
    async def cmd_run(self, update, context):
        if not self._allow(update):
            return
        if self._rate_limited():
            await self._reply(update, "Rate limit hit; wait a moment.")
            return
        args = (context.args or [])
        if len(args) < 2:
            await self._reply(update, "Use: /run <project> <task text>")
            return
        name, task = args[0], " ".join(args[1:])
        try:
            root = self.projects[name]
        except KeyError:
            await self._reply(update, f"Unknown project. Allowed: {', '.join(sorted(self.projects))}")
            return
        try:
            resolve_inside(root)              # containment proof before launch
        except PathOutsideAllowlist:
            await self._reply(update, "That task path is outside the allowlisted project; refused.")
            return
        if DANGEROUS.search(task):
            request_id = f"{int(time.time())}"
            self._pending[request_id] = (name, time.time())
            await self._reply(update, "That task mentions a destructive verb. Confirm to run:",
                        reply_markup=self._confirm_keyboard(request_id))
            self.auditor.log("run-confirm", name, "requested")
            return
        await self._launch(update, name, task)

    async def _launch(self, update, name, task):
        try:
            self.manager.start(name, self.projects[name], task)
        except jobs_mod.JobError as exc:
            await self._reply(update, f"Could not start: {redact(str(exc))}")
            return
        await self._reply(update, f"Started on {name}. I'll report when it finishes.")

    async def cmd_stop(self, update, context):
        if not self._allow(update):
            return
        project = self.manager.stop()
        self.auditor.log("stop", project or "-", "ok")
        await self._reply(update, f"Stopped {project}." if project else "Nothing is running.")

    async def cmd_diff(self, update, context):
        if not self._allow(update):
            return
        name = (context.args or [""])[0]
        root = self.projects.get(name)
        if root is None:
            await self._reply(update, f"Unknown project. Allowed: {', '.join(sorted(self.projects))}")
            return
        from runner.jobs import git_run
        stat = git_run(root, "diff", "--stat")
        names = git_run(root, "diff", "--name-only")
        body = stat.stdout.strip() or "(no unstaged changes)"
        files = "\n".join(n for n in names.stdout.splitlines() if n.strip())
        self.auditor.log("diff", name, "ok")
        await self._reply(update, truncate(body + ("\n\n" + files if files else "")))

    async def cmd_undo(self, update, context):
        if not self._allow(update):
            return
        name = (context.args or [""])[0]
        if name not in self.projects:
            await self._reply(update, f"Unknown project. Allowed: {', '.join(sorted(self.projects))}")
            return
        request_id = f"undo{int(time.time())}"
        self._pending[request_id] = (name, time.time())
        self.auditor.log("undo-confirm", name, "requested")
        await self._reply(update, "Revert that project to its checkpoint?",
                    reply_markup=self._confirm_keyboard(request_id))

    # ---- callbacks (inline buttons) ----------------------------------------
    async def on_callback(self, update, context):
        query = update.callback_query
        if not self._allow(update):
            return
        action, _, request_id = (query.data or "").partition(":")
        project = self._pending_pop(request_id)
        if project is None:
            await query.answer(text="That confirmation expired. Run the command again.")
            self.auditor.log("confirm", "-", "expired")
            return
        if action == "cancel":
            await query.answer(text="Cancelled.")
            self.auditor.log("confirm", project, "cancelled")
            return
        await query.answer(text="Confirmed.")
        if request_id.startswith("undo"):
            try:
                message = self.manager.undo(project, self.projects[project])
            except jobs_mod.JobError as exc:
                await self._reply(update, f"Undo failed: {redact(str(exc))}")
                return
            await self._reply(update, message)
            return
        # run-confirmations fall through here
        task = self._run_task_after_confirm.pop(request_id, None)
        if task is None:
            await self._reply(update, "That request expired; send /run again.")
            return
        await self._launch(update, project, task)

    _run_task_after_confirm: dict = {}

    async def stranger(self, update, context):
        """Non-owner update: dropped silently. Logged with NO content."""
        self.auditor.log("ignored", "-", "sender-not-owner")

    async def unknown(self, update, context):
        if not self._allow(update):
            return
        self.auditor.log("unknown", "-", "hint")
        await self._reply(update, "Unknown command. " + HELP_TEXT.splitlines()[0])

    # ---- job completion ----------------------------------------------------
    def on_job_finish(self, job):
        result = job.result
        if result is None:
            return
        summary = (f"Job on {job.project}: {result.outcome} in {result.elapsed}s.\n"
                   f"Files changed: {result.changed_files}\n"
                   + redact("\n".join(result.output.splitlines()[-8:]))[:800])
        self._final_reply(summary)

    def _final_reply(self, text):
        if self._send_fn is None:
            return
        try:
            self._send_fn(truncate(text))
        except Exception:
            self.note_network_drop()

    _send_fn = None

    def bind_sender(self, send_fn):
        self._send_fn = send_fn
