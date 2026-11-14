"""Hash-chained, append-only audit log for privileged changes.

Each record: time, request type, level, outcome, approver. No secret values,
no message content - structurally, the signature covers only those fields.

Chain: each entry commits the SHA-256 of the previous entry, so deleting or
altering any past entry breaks every subsequent link. The latest chain hash
is surfaced for periodic send to the owner's Telegram chat (deletion of the
whole file is then detectable because the next check reports a mismatching
or missing head against the last hash the owner saw).

Append-only discipline: the file is opened in append mode only. There is no
API to truncate, rewrite or delete entries; the only permitted operation is
verify(). Rotation is deliberate and re-anchors the chain with an explicit
rotation marker (so rotation is auditable, not a silent erase).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

GENESIS = "0" * 64


def _entry_hash(prev_hash: str, payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((prev_hash + blob).encode()).hexdigest()


class ChainedAudit:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._head = self._load_head()

    def _load_head(self):
        if not self.path.is_file():
            return GENESIS
        last = GENESIS
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                last = record.get("hash", last)
        except (json.JSONDecodeError, OSError):
            # A corrupt tail fails closed on the next verify(); the head is
            # still the last well-formed hash.
            pass
        return last

    def log(self, command: str, subject: str, outcome: str, approver: str = "-"):
        """One entry. command/subject/outcome/approver are short fixed-vocabulary
        strings; callers never pass message bodies or secret values here."""
        with self._lock:
            now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            payload = {"t": now, "command": command, "subject": subject,
                       "outcome": outcome, "approver": approver}
            entry_hash = _entry_hash(self._head, payload)
            record = {**payload, "hash": entry_hash}
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
            self._head = entry_hash
            return entry_hash

    @property
    def head(self):
        return self._head

    def verify(self):
        """Recompute the whole chain. Returns (ok: bool, problem: str)."""
        with self._lock:
            if not self.path.is_file():
                return True, "empty"
            prev = GENESIS
            for lineno, line in enumerate(
                    self.path.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    return False, f"line {lineno}: malformed JSON"
                expected_fields = {"t", "command", "subject", "outcome", "approver", "hash"}
                if set(record) != expected_fields:
                    return False, f"line {lineno}: unexpected fields"
                payload = {k: record[k] for k in
                           ("t", "command", "subject", "outcome", "approver")}
                if _entry_hash(prev, payload) != record["hash"]:
                    return False, f"line {lineno}: chain broken"
                prev = record["hash"]
            if prev != self._head:
                return False, "in-memory head does not match the file"
            return True, "ok"

    def tail_hash_for_owner(self):
        """The hash to display/send periodically; proves the log survived."""
        return self.head
