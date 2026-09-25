"""Fail-closed first-administrator registration for LYA.

This module coordinates injected camera, microphone, liveness, embedding, and
trusted-device adapters. It never opens hardware or sends data to a network.
"""

from dataclasses import dataclass
import math
from pathlib import Path
import secrets
import time
from typing import Callable

from security.policy import Session
from storage import has_active_admin, register_primary_admin


class RegistrationDenied(PermissionError):
    """Registration stopped without changing the identity store."""


@dataclass(frozen=True)
class RegistrationConsent:
    display_name: str
    local_biometric_storage: bool
    understood_recovery_code: bool
    explicitly_confirmed: bool


@dataclass(frozen=True)
class BootstrapChallenge:
    action: str
    display_name: str
    nonce: str
    deadline: float


@dataclass(frozen=True)
class RegistrationResult:
    person_id: str
    session: Session
    greeting: str
    recovery_code: str


@dataclass(frozen=True)
class RegistrationConfig:
    sample_count: int = 3
    face_consistency: float = 0.55
    voice_consistency: float = 0.75
    proof_ttl_seconds: float = 90.0
    session_seconds: float = 300.0

    def __post_init__(self):
        if type(self.sample_count) is not int or not 3 <= self.sample_count <= 6:
            raise ValueError("Capture count must be between three and six.")
        for value in (self.face_consistency, self.voice_consistency):
            if not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError("Consistency thresholds must be finite and within (0, 1].")
        for value in (self.proof_ttl_seconds, self.session_seconds):
            if not math.isfinite(value) or not 0 < value <= 300:
                raise ValueError("Verification lifetimes must be within five minutes.")


def _normalized(vector) -> list[float]:
    values = [float(value) for value in vector]
    if not values or any(not math.isfinite(value) for value in values):
        raise RegistrationDenied("Biometric template was invalid.")
    magnitude = math.hypot(*values)
    if not math.isfinite(magnitude) or magnitude <= 0.0:
        raise RegistrationDenied("Biometric template was empty.")
    return [value / magnitude for value in values]


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise RegistrationDenied("Biometric template dimensions changed during capture.")
    return sum(a * b for a, b in zip(left, right))


def _require_consistency(vectors: list[list[float]], threshold: float, label: str):
    for index, left in enumerate(vectors):
        for right in vectors[index + 1:]:
            if _cosine(left, right) < threshold:
                raise RegistrationDenied(f"{label} samples were not consistent. Please recapture.")


class AdminRegistrar:
    """Register exactly one primary admin after strong local verification."""

    FACE_CHALLENGES = ("look-center-and-blink", "turn-left", "turn-right")

    def __init__(
        self,
        *,
        trusted_device_verifier: Callable[[BootstrapChallenge], object] | None,
        capture_face: Callable[[str], bytes],
        capture_voice: Callable[[str], bytes],
        verify_face_liveness: Callable[[bytes, str], bool],
        verify_voice_challenge: Callable[[bytes, str], bool],
        encode_face: Callable[[bytes], object],
        encode_voice: Callable[[bytes], object],
        db_path: Path | None = None,
        config: RegistrationConfig | None = None,
        clock: Callable[[], float] = time.time,
        cancelled: Callable[[], bool] = lambda: False,
    ):
        self.trusted_device_verifier = trusted_device_verifier
        self.capture_face = capture_face
        self.capture_voice = capture_voice
        self.verify_face_liveness = verify_face_liveness
        self.verify_voice_challenge = verify_voice_challenge
        self.encode_face = encode_face
        self.encode_voice = encode_voice
        self.db_path = db_path
        self.config = config or RegistrationConfig()
        self.clock = clock
        self.cancelled = cancelled

    def register(self, consent: RegistrationConsent) -> RegistrationResult:
        name = consent.display_name.strip()
        if not (name and len(name) <= 80 and consent.local_biometric_storage is True
                and consent.understood_recovery_code is True and consent.explicitly_confirmed is True):
            raise RegistrationDenied("Explicit local biometric consent is required.")
        if self.cancelled():
            raise RegistrationDenied("Registration cancelled.")
        if has_active_admin(self.db_path):
            raise RegistrationDenied("An active primary administrator already exists.")
        if self.trusted_device_verifier is None:
            raise RegistrationDenied("Trusted-device verification is unavailable.")

        started = self.clock()
        if not math.isfinite(started):
            raise RegistrationDenied("Verification clock unavailable.")
        challenge = BootstrapChallenge(
            action="register-primary-admin",
            display_name=name,
            nonce=secrets.token_urlsafe(24),
            deadline=started + self.config.proof_ttl_seconds,
        )
        proof = self.trusted_device_verifier(challenge)
        if type(proof) is not BootstrapChallenge or proof != challenge:
            raise RegistrationDenied("Trusted-device verification failed or expired.")

        def check_active():
            now = self.clock()
            if self.cancelled() or not math.isfinite(now) or now >= challenge.deadline:
                raise RegistrationDenied("Registration cancelled or verification expired.")

        check_active()

        face_vectors = []
        voice_vectors = []
        for index in range(self.config.sample_count):
            check_active()
            face_prompt = self.FACE_CHALLENGES[index % len(self.FACE_CHALLENGES)]
            face_sample = self.capture_face(face_prompt)
            try:
                check_active()
                if not face_sample or self.verify_face_liveness(face_sample, face_prompt) is not True:
                    raise RegistrationDenied("Live face challenge failed.")
                face_vectors.append(_normalized(self.encode_face(face_sample)))
            finally:
                del face_sample

            spoken_code = " ".join(str(secrets.randbelow(10)) for _ in range(6))
            check_active()
            voice_sample = self.capture_voice(spoken_code)
            try:
                check_active()
                if not voice_sample or self.verify_voice_challenge(voice_sample, spoken_code) is not True:
                    raise RegistrationDenied("Live voice challenge failed.")
                voice_vectors.append(_normalized(self.encode_voice(voice_sample)))
            finally:
                del voice_sample

        _require_consistency(face_vectors, self.config.face_consistency, "Face")
        _require_consistency(voice_vectors, self.config.voice_consistency, "Voice")
        check_active()

        recovery_code = secrets.token_urlsafe(32)
        person_id = register_primary_admin(
            name,
            face_vectors,
            voice_vectors,
            recovery_code,
            db_path=self.db_path,
        )
        now = self.clock()
        session = Session(
            role="admin",
            person=name,
            id="session_" + secrets.token_urlsafe(18),
            person_id=person_id,
            verified_until=now + self.config.session_seconds,
        )
        return RegistrationResult(
            person_id=person_id,
            session=session,
            greeting=f"Welcome, {name}. LYA recognizes you as the primary administrator.",
            recovery_code=recovery_code,
        )
