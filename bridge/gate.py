"""LYA <-> iPhone bridge - the security gate.

TWO TIERS, per the owner-approved policy:

  Tier 1 (simple info/tasks): FACE ONLY. A successful admin face match
          suffices - no secret word needed for looking things up.
  Tier 2 (sensitive: passwords, vault, device control, bridge actions):
          face AND the secret word (security.escalation, salted PBKDF2).

Bridge actions are ALWAYS tier 2 - a phone-triggered device command is by
definition a sensitive action. Simple laptop-side "it's me" checks live in
brain.admin_recognizer and use tier 1.

Failures are RATE LIMITED. Five consecutive failures lock the bridge for
15 minutes, exactly like the escalation flow. Reuse beats reinvention:
both primitives are already battle-tested in this project, so the gate is
composition, not new crypto.
"""
import hmac
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60

_lock = threading.Lock()
_failures = 0
_locked_until = 0.0


def reset_gate():
    """Clear the failure counter and any lockout. Used by tests and by an
    explicit owner unlock; not called during normal operation."""
    global _failures, _locked_until
    with _lock:
        _failures = 0
        _locked_until = 0.0


def _register_failure(now):
    global _failures, _locked_until
    _failures += 1
    if _failures >= MAX_FAILURES:
        _locked_until = now + LOCKOUT_SECONDS
        _failures = 0


def gate_status(now=None):
    """(allowed, reason). allowed=False means every attempt is refused
    WITHOUT running biometrics - an attacker learns nothing by retrying."""
    now = time.time() if now is None else now
    with _lock:
        if _locked_until > now:
            return False, "locked"
        return True, "ok"


def verify_gate(frame_bytes, transcript, *, verify_face=None, check_word=None, now=None):
    """Two-factor gate for one bridge request.

    verify_face: bytes -> (ok, detail). Defaults to the real owner verifier.
    check_word:  str -> "ok"/"duress"/False. Defaults to the real phrase check.

    Returns (allowed: bool, detail: str). "duress" is returned as a failure
    with that detail so callers can raise a silent alarm WITHOUT telling the
    speaker why - duress only works if the coercer cannot distinguish it.
    """
    now = time.time() if now is None else now

    if verify_face is None:
        from vision import identity
        verify_face = identity.verify_owner
    if check_word is None:
        from security import escalation
        check_word = escalation.check_security_word

    allowed, reason = gate_status(now)
    if not allowed:
        return False, reason

    ok, face_detail = verify_face(frame_bytes)
    if not ok:
        with _lock:
            _register_failure(now)
        return False, f"face:{face_detail}"

    word = check_word(transcript)
    if word == "ok":
        with _lock:
            _failures = 0
        return True, "ok"
    with _lock:
        _register_failure(now)
    # Re-read the lockout AFTER registering: this failure may itself be the
    # one that trips the lock. gate_status takes the same non-reentrant lock,
    # so it MUST be called after the with-block exits, never nested inside it.
    allowed_now, reason_now = gate_status(now)
    if not allowed_now:
        return False, reason_now
    # duress is deliberately reported exactly like a wrong word.
    return False, "word" if word != "duress" else "duress"


def _register_failure_and_check(now):
    """One failure under the lock, then the freshest allowed state.

    Deliberately separate from _register_failure: callers need BOTH the
    registration and the post-registration lockout read, and gate_status
    cannot be called while the non-reentrant lock is held."""


def constant_time_equals(a, b):
    """Expose hmac.compare_digest for token checks so callers cannot
    accidentally use == on secrets (the classic byte-at-a-time leak)."""
    return hmac.compare_digest(a, b)
