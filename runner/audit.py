"""Rotating audit log. Time, command name, project, outcome - nothing else.

Message bodies, task text, output contents and secrets are structurally
impossible here: log() accepts only the four fixed fields.
"""
import logging
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path


class Auditor:
    def __init__(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)
        self._handler = RotatingFileHandler(log_dir / "audit.log",
                                            maxBytes=200_000, backupCount=3,
                                            encoding="utf-8")
        self._handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self._log = logging.getLogger("lya-runner-audit")
        self._log.addHandler(self._handler)
        self._log.setLevel(logging.INFO)
        self._propagate = False
        self._lock = threading.Lock()

    def log(self, command: str, project: str, outcome: str):
        with self._lock:
            self._log.info("%s project=%s outcome=%s",
                           command, project or "-", outcome or "-")
