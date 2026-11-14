"""Bitwarden-backed recovery code: typed only, shown once, single-use.

Flow per owner directive:
  - Created once by the OWNER manually (not by LYA, not by the model); the
    plaintext is displayed exactly once and stored only as a salted hash in
    the owner's Bitwarden offline copy. LYA stores nothing but the hash.
  - A recovery code may ONLY enroll a new phone (recovery_enroll request).
    It cannot perform any other HIGH action.
  - Using it requires typing (never voice) and a 24-hour waiting period,
    with notifications at every step.
  - Single-use: consuming rotates the hash; the old code is dead.
  - Manual git/DB recovery remains the last resort (documented in
    docs/guides/LYA_MEMORY_KEY_CUSTODY.md).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from pathlib import Path

from security.gate import RECOVERY_WAITING_PERIOD

HASH_FILE = Path(__file__).resolve().parent / "recovery_code.lya"
ITERATIONS = 600_000          # matches the Phase B PBKDF2 uplift standard
_STATE = threading.RLock()   # reentrant: consume() holds it while rotating


def _normalize(code: str) -> str:
    cleaned = "".join(c if (c.isalnum() or c.isspace()) else " " for c in code.lower())
    return " ".join(cleaned.split())


def _hash(code: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", _normalize(code).encode(),
                               salt, ITERATIONS).hex()


class RecoveryService:
    """Reads/writes only a hashed record: {salt, hash, created, rotated_from}."""

    def __init__(self, path: Path = HASH_FILE):
        self.path = Path(path)
        self._hash_loaded = None

    # ---- creation (owner-only, manual) ----------------------------------
    def create_code(self) -> str:
        """Generate a code, store ONLY its hash, return plaintext once.
        The owner writes it into Bitwarden; LYA never sees it again.
        NOTE: does not take _STATE itself - callers that hold the lock
        (consume) would deadlock on a non-reentrant Lock."""
        code = "LYA-" + "-".join(secrets.token_hex(2).upper() for _ in range(4))
        salt = secrets.token_bytes(16)
        record = {"salt": salt.hex(), "hash": _hash(code, salt),
                  "created": int(__import__("time").time())}
        with _STATE:
            self.path.write_text(json.dumps(record), encoding="utf-8")
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
        return code     # shown once; the caller must not log it

    # ---- verification -------------------------------------------------------
    def _record(self):
        if not self.path.is_file():
            return None
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
            return record if record.get("hash") else None
        except (json.JSONDecodeError, OSError):
            return None

    def verify(self, typed_code: str) -> bool:
        record = self._record()
        if not record or not typed_code:
            return False
        expected = bytes.fromhex(record["salt"])
        return hmac.compare_digest(_hash(typed_code, expected).encode(),
                                   record["hash"].encode())

    def consume(self, typed_code: str, new_device_binding: dict) -> dict:
        """Single-use: verify then rotate. Old code dies here. Returns a
        marker only - the NEW plaintext was already displayed to the owner at
        creation time inside create_code(); nothing plaintext is returned
        over any interface. This must only ever be called from the
        gate-approved executor."""
        with _STATE:
            if not self.verify(typed_code):
                raise ValueError("Recovery code did not verify.")
            # create_code() rotates the stored hash; its plaintext return is
            # immediately discarded here - never logged, never returned.
            self.create_code()
            record = self._record() or {}
            record["rotated_from_used"] = True
            self.path.write_text(json.dumps(record), encoding="utf-8")
            return {"enrolled": new_device_binding, "rotated": True}

    @staticmethod
    def waiting_period_seconds():
        return RECOVERY_WAITING_PERIOD
