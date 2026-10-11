"""In-process approval boundary. Verifiers must be trusted OS/phone adapters.

No network endpoint or user text may call this boundary as an identity verifier.
Without a configured verifier, every protected request is denied.
"""
from dataclasses import dataclass
import math
import secrets
import threading
import time

from security.policy import OWNER, Session


@dataclass(frozen=True)
class Challenge:
    nonce: str
    session: Session
    action: str
    parameters: str
    deadline: float


class ApprovalGate:
    def __init__(self, verifier=None, *, clock=time.monotonic, wall_clock=time.time):
        self.verifier = verifier
        self.clock, self.wall_clock = clock, wall_clock
        self._pending = None
        self._lock = threading.Lock()

    def invalidate(self):
        with self._lock:
            self._pending = None

    def is_pending(self, challenge):
        """Trusted phone UI may close when its exact request is cancelled or expires."""
        with self._lock:
            return (type(challenge) is Challenge and self._pending == challenge
                    and self.clock() < challenge.deadline
                    and self.wall_clock() < challenge.session.verified_until)

    def __call__(self, action, parameters, session):
        if (self.verifier is None or action not in OWNER or session.role != 'admin'
                or not session.id or not session.person_id
                or not math.isfinite(session.verified_until)
                or session.verified_until <= self.wall_clock()
                or not isinstance(parameters, str) or not 0 < len(parameters) <= 4000):
            return False
        with self._lock:
            if self._pending is not None:
                return False
            challenge = Challenge(secrets.token_urlsafe(32), session, action,
                                  parameters, self.clock() + 120)
            self._pending = challenge
        try:
            # The adapter must authenticate independently and return the exact
            # displayed challenge only after explicit approval. True is not proof.
            response = self.verifier(challenge)
            with self._lock:
                return (self._pending == challenge and type(response) is Challenge
                        and response == challenge and self.clock() < challenge.deadline
                        and self.wall_clock() < session.verified_until)
        except Exception:
            return False
        finally:
            with self._lock:
                if self._pending == challenge:
                    self._pending = None
