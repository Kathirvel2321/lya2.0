"""Job manager: one at a time, git checkpoint before, tree-kill on timeout.

The agent is launched with shell=False and the owner's task text travels as
exactly one argv element (`--task`). Nothing the user sends is ever
interpreted by a shell. The working directory is confined to the allowlisted
project root resolved by runner.security.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from runner.security import PathOutsideAllowlist, resolve_inside


class JobError(RuntimeError):
    pass


@dataclass
class JobResult:
    ok: bool
    outcome: str                  # success | failed | timeout | stopped
    output: str
    changed_files: int = 0
    elapsed: float = 0.0


@dataclass
class Job:
    project: str
    root: Path
    task: str
    checkpoint: str | None = None
    process: subprocess.Popen | None = None
    started: float = 0.0
    result: JobResult | None = None


def git_run(root: Path, *args, timeout=30):
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, shell=False)


class JobManager:
    def __init__(self, agent_command, timeout_seconds, on_finish=None,
                 auditor=None):
        self.agent_command = list(agent_command)
        self.timeout_seconds = timeout_seconds
        self.on_finish = on_finish          # callable(Job) in a worker thread
        self.auditor = auditor
        self._lock = threading.Lock()
        self._job: Job | None = None
        self._last: JobResult | None = None

    # ---- introspection ------------------------------------------------
    def status_line(self):
        with self._lock:
            if self._job is None:
                return None
            return {"project": self._job.project,
                    "elapsed": round(time.time() - self._job.started, 1),
                    "task_len": len(self._job.task)}

    def last_result(self):
        with self._lock:
            return getattr(self, "_last", None)

    # ---- git checkpoint ------------------------------------------------
    def _checkpoint(self, root: Path, job: Job):
        probe = git_run(root, "rev-parse", "--is-inside-work-tree")
        if probe.returncode != 0 or probe.stdout.strip() != "true":
            raise JobError("The project folder is not a git repository; refusing to run.")
        status = git_run(root, "status", "--porcelain")
        dirty = bool((status.stdout or "").strip())
        if dirty:
            git_run(root, "add", "-A")
            commit = git_run(root, "commit", "-m",
                             f"LYA runner checkpoint before task ({job.project})")
            if commit.returncode != 0:
                raise JobError("Could not create the git checkpoint commit.")
            job.checkpoint = "HEAD"
        else:
            job.checkpoint = git_run(root, "rev-parse", "HEAD").stdout.strip()
        git_run(root, "branch", "-f", "lya-runner-backup", "HEAD")

    # ---- lifecycle -------------------------------------------------------
    def start(self, project_name: str, root: Path, task: str) -> Job:
        with self._lock:
            if self._job is not None:
                raise JobError("A job is already running. Use /stop first.")
            job = Job(project=project_name, root=root, task=task)
            try:
                self._checkpoint(root, job)
            except (JobError, subprocess.SubprocessError, OSError) as exc:
                raise JobError(f"Git checkpoint failed: {exc}") from None
            self._job = job
            job.started = time.time()
            thread = threading.Thread(target=self._run, args=(job,), daemon=True)
            thread.start()
            if self.auditor:
                self.auditor.log("run", project_name, "started")
            return job

    def stop(self):
        with self._lock:
            job = self._job
            if job is None:
                return None
            self._kill(job)
            return job.project

    def _kill(self, job: Job):
        proc = job.process
        if proc is None or proc.poll() is not None:
            return
        if os.name == "nt":
            # taskkill /T kills the whole tree, which plain terminate() misses
            # when the agent spawns children.
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, shell=False)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    # ---- worker ----------------------------------------------------------
    def _run(self, job: Job):
        argv = [*self.agent_command, "--task", job.task]
        try:
            proc = subprocess.Popen(argv, cwd=str(job.root), shell=False,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            job.process = proc
            try:
                out, _ = proc.communicate(timeout=self.timeout_seconds)
                code = proc.returncode
                outcome = "success" if code == 0 else "failed"
                ok = code == 0
            except subprocess.TimeoutExpired:
                self._kill(job)
                out, _ = proc.communicate()
                outcome, ok = "timeout", False
            text = out.decode("utf-8", errors="replace") if isinstance(out, bytes) else (out or "")
            try:
                changed = git_run(job.root, "status", "--porcelain")
                n_changed = len([line for line in (changed.stdout or "").splitlines()
                                 if line.strip()])
            except Exception:
                n_changed = 0
            job.result = JobResult(ok=ok, outcome=outcome, output=text,
                                   changed_files=n_changed,
                                   elapsed=round(time.time() - job.started, 1))
        except Exception as exc:            # noqa: BLE001 - must never crash the thread
            job.result = JobResult(ok=False, outcome="failed",
                                   output=f"runner error: {type(exc).__name__}")
        finally:
            # status_line() clears as soon as the job ends, even on error.
            if self.auditor:
                self.auditor.log("run", job.project, job.result.outcome)
            with self._lock:
                self._last = job.result
                self._job = None
            if self.on_finish:
                try:
                    self.on_finish(job)
                except Exception:
                    pass

    def undo(self, project_name: str, root: Path) -> str:
        """Revert to the pre-job checkpoint of the most recent job for root."""
        with self._lock:
            job = self._job
        if job is not None and job.project == project_name:
            raise JobError("Cannot undo while that project's job is running.")
        probe = git_run(root, "rev-parse", "--verify", "lya-runner-backup")
        if probe.returncode != 0:
            raise JobError("No LYA checkpoint branch exists for this project.")
        reset = git_run(root, "reset", "--hard", "lya-runner-backup")
        clean = git_run(root, "clean", "-fd")
        if reset.returncode != 0:
            raise JobError("git reset failed; the checkpoint branch is untouched.")
        if self.auditor:
            self.auditor.log("undo", project_name, "ok")
        return "Reverted to the checkpoint taken before the last runner task."
