"""Central privileged-change gate - Phase B.

Risk levels and who approves what:

  LOW     face match only                    (greetings, preferences)
  MEDIUM  face match + phone approval        (visitor adds, scheduled jobs)
  HIGH    phone Face ID passkey approval +   (admin add/remove/change,
          typed secret key + waiting period   password/secret key change,
          + notification on every state       granting a new capability)
  NEVER   nothing approves these             (security code, thresholds, the
                                              gate itself, the audit log,
                                              this rule list)

Fail-closed rule (owner directive): HIGH requires an enrolled phone passkey.
No passkey enrolled -> every HIGH request is denied. There is no weaker
fallback for HIGH - not the secret word, not the it's-me session, nothing.

The AI model's involvement ends at creating a structured REQUEST dict.
It never receives credentials, never verifies, never executes. The executor
functions are decorated with requires_gate and live in executor modules that
import this module - never the other way around, and never reachable from a
model-facing surface.
"""
from __future__ import annotations

import functools
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

LOW = "low"
MEDIUM = "medium"
HIGH = "high"
NEVER = "never"

REQUEST_TTL = 300               # approval expires 5 minutes after request
DEFAULT_WAITING_PERIOD = 600    # 10 minutes for admin/secret-key changes
RECOVERY_WAITING_PERIOD = 86400 # recovery-code use waits 24 hours
MAX_FAILS = 3
LOCKOUT_SECONDS = 30 * 60       # 30 minutes after repeated failed verifications


class GateError(PermissionError):
    pass


class HighTierUnavailable(GateError):
    """Raised when HIGH is requested but no phone passkey is enrolled.
    Fail closed: no fallback whatsoever."""


class DuressDetected(GateError):
    """The spoken/typed phrase matched the duress word. Callers must NOT
    reveal this: outwardly it behaves like any other denial, and a silent
    notification is dispatched by the gate."""


class LockoutActive(GateError):
    pass


@dataclass
class ChangeRequest:
    request_id: str
    kind: str                     # admin_add | admin_remove | admin_role | password | secret_key | capability | recovery_enroll
    level: str
    target: dict                  # structured parameters; never credentials in plaintext beyond necessity
    created: float
    requester: str = "model"
    state: str = "pending"        # pending | waiting | approved | completed | cancelled | rejected | expired
    waiting_until: float = 0.0


@dataclass
class GateState:
    passkey_enrolled: bool = False
    fail_count: int = 0
    locked_until: float = 0.0
    requests: dict = field(default_factory=dict)
    notifications: list = field(default_factory=list)   # (ts, event, detail)


class Gate:
    """One gate per LYA process. All verification happens here, in code."""

    def __init__(self, *, notifier=None, audit=None, clock=time.time,
                 passkey_enroll_check=None):
        self.state = GateState()
        self.notifier = notifier          # callable(event, detail) -> None
        self.audit = audit                # callable(command, project, outcome)
        self.clock = clock
        self._lock = threading.RLock()
        self._passkey_enroll_check = passkey_enroll_check or (lambda: self.state.passkey_enrolled)

    # ---- notifications ---------------------------------------------------
    def _notify(self, event, detail=""):
        self.state.notifications.append((self.clock(), event, detail))
        if self.notifier:
            try:
                self.notifier(event, detail)
            except Exception:
                pass    # notification failure never gates a decision

    # ---- request lifecycle --------------------------------------------------
    def request(self, kind, level, target, requester="model"):
        """The ONLY thing the model-facing side may call. Creates a pending
        request. No credential is needed or accepted here."""
        if level == NEVER:
            raise GateError("This change type can never be requested or performed by LYA.")
        with self._lock:
            now = self.clock()
            if self.state.locked_until > now:
                raise LockoutActive("Verification lockout is active; HIGH requests are blocked.")
            if level == HIGH:
                if not self._passkey_enroll_check():
                    self._notify("high_denied_no_passkey", kind)
                    if self.audit:
                        self.audit("gate-request", kind, "denied-no-passkey")
                    raise HighTierUnavailable(
                        "No phone passkey is enrolled. HIGH requests are denied - "
                        "there is no fallback for this tier.")
            request_id = secrets.token_urlsafe(16)
            req = ChangeRequest(request_id=request_id, kind=kind, level=level,
                                target=target, created=now, requester=requester)
            self.state.requests[request_id] = req
            if self.audit:
                self.audit("gate-request", kind, f"level={level}")
            if level == HIGH:
                self._notify("high_requested", f"{kind}: {self._describe(target)}")
            return req

    def _describe(self, target):
        # Human-readable, non-secret description for phone confirmation.
        kind = target.get("_display_kind")
        if kind == "admin_add":
            return f'Add {target.get("name")} as admin?'
        if kind == "admin_remove":
            return f'Remove admin {target.get("name")}?'
        if kind == "admin_role":
            return f'Change role of {target.get("name")} to {target.get("role")}?'
        if kind == "password":
            return "Change the LYA password?"
        if kind == "secret_key":
            return "Change the LYA secret key?"
        if kind == "capability":
            return f'Grant capability {target.get("capability")}?'
        if kind == "recovery_enroll":
            return "Enroll a new phone via recovery code?"
        return "Review this change on your phone."

    # ---- verification -------------------------------------------------------
    def approve_with_passkey(self, request_id, passkey_ok):
        """Called by the phone-approval path after a passkey ceremony succeeds.
        passkey_ok is a boolean produced by the real WebAuthn verifier - the
        gate never sees the passkey itself. Single-use: a second call on the
        same request is refused."""
        with self._lock:
            req = self.state.requests.get(request_id)
            if req is None or req.state != "pending":
                # missing, expired already, already approved/rejected/used
                if req and req.state == "pending":
                    pass
                elif req is None:
                    return "expired"
                if req is not None and self.clock() - req.created > REQUEST_TTL:
                    req.state = "expired"
                    return "expired"
                if req is not None and req.state != "pending":
                    return "expired"
                return "expired"
            if self.clock() - req.created > REQUEST_TTL:
                req.state = "expired"
                self._notify("expired", req.kind)
                if self.audit:
                    self.audit("gate-expire", req.kind, "expired")
                return "expired"
            if passkey_ok is not True:
                req.state = "rejected"
                self._register_fail(req)
                return "rejected"
            if req.level == HIGH:
                wait = RECOVERY_WAITING_PERIOD if req.kind == "recovery_enroll" \
                    else self.waiting_period()
                req.waiting_until = self.clock() + wait
                req.state = "waiting"
                self._notify("high_approved",
                             f"{req.kind}: waiting until change completes")
            else:
                req.state = "approved"
            if self.audit:
                self.audit("gate-approve", req.kind, req.state)
            return req.state

    waiting_period_value = DEFAULT_WAITING_PERIOD

    def waiting_period(self):
        env = os.environ.get("LYA_HIGH_WAITING_SECONDS", "")
        if env.strip().isdigit():
            value = int(env)
            if 0 <= value <= 86400:
                return value
        return self.waiting_period_value

    def complete(self, request_id, executor_result=None):
        """Complete a waiting/approved request. The executor callback is what
        performs the change; the gate only decides whether it may run."""
        with self._lock:
            req = self.state.requests.get(request_id)
            if not req:
                return "unknown"
            now = self.clock()
            if req.state == "waiting" and req.waiting_until > now:
                return "waiting"
            if req.state not in ("approved", "waiting"):
                return req.state
            req.state = "completed"
            self._notify("high_completed" if req.level == HIGH else "completed",
                         req.kind)
            if self.audit:
                self.audit("gate-complete", req.kind, "ok")
            return "completed"

    def cancel(self, request_id):
        with self._lock:
            req = self.state.requests.get(request_id)
            if req and req.state in ("pending", "waiting"):
                req.state = "cancelled"
                self._notify("high_cancelled" if req.level == HIGH else "cancelled",
                             req.kind)
                if self.audit:
                    self.audit("gate-cancel", req.kind, "cancelled")
                return True
            return False

    def _live_request(self, request_id):
        req = self.state.requests.get(request_id)
        if not req:
            return None
        now = self.clock()
        if req.state == "pending" and now - req.created > REQUEST_TTL:
            req.state = "expired"
            self._notify("expired", req.kind)
            if self.audit:
                self.audit("gate-expire", req.kind, "expired")
            return None
        if req.state in ("expired", "rejected", "cancelled", "completed",
                         "approved", "waiting"):
            # An approved/waiting request is consumed by its first approve call;
            # a second approve attempt finds nothing live (single-use).
            return None
        return req

    # ---- failure accounting ---------------------------------------------------
    def _register_fail(self, req):
        self.state.fail_count += 1
        self._notify("high_rejected" if req.level == HIGH else "rejected", req.kind)
        if self.audit:
            self.audit("gate-fail", req.kind, "rejected")
        if self.state.fail_count >= MAX_FAILS:
            self.state.locked_until = self.clock() + LOCKOUT_SECONDS
            self._notify("lockout", f"HIGH requests blocked for {LOCKOUT_SECONDS // 60} minutes")
            self.state.fail_count = 0

    # ---- duress ----------------------------------------------------------------
    def check_duress(self, phrase, duress_hash_pair):
        """duress_hash_pair: (spoken_normalized, verify_callable). If the
        phrase matches the duress word, raise DuressDetected (a denial) and
        notify silently. Never returns 'duress' to any caller."""
        spoken, verify = duress_hash_pair
        if verify(spoken) == "duress":
            self._notify("duress_silent_alarm", "A duress phrase matched during a privileged request.")
            raise DuressDetected("Verification failed.")
        return False


def requires_gate(level, kind=None):
    """Decorator for privileged executor functions. The wrapped function is
    callable ONLY with an approved request token: verify_gate(request_id).
    There is deliberately no way to call it with a bare True/ok flag - an
    approved ChangeRequest must exist and be in the approved state."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(request=None, *args, **kwargs):
            gate = kwargs.pop("gate", None)
            if not isinstance(request, ChangeRequest) or gate is None:
                raise GateError(
                    "Privileged changes require a gate-approved ChangeRequest. "
                    "Direct calls are refused.")
            with gate._lock:
                if gate.state.requests.get(request.request_id) is not request:
                    raise GateError("Request token does not match the gate registry.")
                if request.state != "approved":
                    raise GateError(
                        f"Request is {request.state}; an approved request is required.")
                if level != request.level:
                    raise GateError("Request level does not match the executor level.")
            return fn(request, *args, **kwargs)
        wrapper.__gate_level__ = level
        wrapper.__gate_kind__ = kind
        wrapper.__requires_gate__ = True
        return wrapper
    return decorator
