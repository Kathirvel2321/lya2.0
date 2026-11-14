"""Tiered admin recognition - "LYA, it's me".

Simple conversation needs a friendly hello, not an interrogation. This module
implements the owner-approved policy:

  TIER 1  simple info/tasks      -> face match ONLY ("LYA, it's me" while
                                    looking at the camera). No secret word.
  TIER 2  sensitive actions      -> face match AND the secret word
                                    (passwords, vault, device control,
                                    bridge actions). Unchanged from the
                                    existing escalation policy.

The face check reuses vision.identity.identify (ArcFace 512-d embeddings,
encrypted templates). A successful Tier-1 match mints a short-lived admin
session with the same 10-minute TTL the phone gateway already uses. Frames
are never stored: each webcam snap is converted to an embedding in memory
and discarded.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SESSION_TTL = 600          # 10 minutes, same as the phone gateway
SESSION_LOCK = threading.Lock()
_sessions = {}             # sid -> expiry


# ---- admin sessions ----------------------------------------------------
def mint_session(now=None):
    import secrets
    sid = secrets.token_urlsafe(24)
    with SESSION_LOCK:
        _sessions[sid] = time.time() if now is None else now
    return sid


def session_valid(sid, now=None):
    now = time.time() if now is None else now
    with SESSION_LOCK:
        for k, exp in list(_sessions.items()):
            if now - exp > SESSION_TTL:
                del _sessions[k]
        return sid in _sessions


def end_session(sid):
    with SESSION_LOCK:
        _sessions.pop(sid, None)


# ---- the "it's me" flow ------------------------------------------------
def capture_frames(count=3, camera_index=0):
    """Grab `count` frames from the laptop webcam. Frames stay in memory."""
    import cv2
    cam = cv2.VideoCapture(camera_index)
    frames = []
    try:
        for _ in range(count):
            ok, frame = cam.read()
            if ok and frame is not None:
                frames.append(frame)
            time.sleep(0.3)          # slight spread so micro-motions differ
    finally:
        cam.release()
    return frames


def recognize_me(frames, admin_threshold=0.45, db_path=None):
    """Frames -> best admin match. Returns the identity dict from identify()
    plus a session id when the match is an admin. Frames are not persisted.

    First-glance optimization: every frame passes vision.quick_check first.
    Covered cameras, blur, and turned-away faces are rejected in milliseconds
    WITHOUT running ArcFace; the expensive embedding runs only on a frame that
    can actually produce a match."""
    import numpy as np
    from vision import identity
    from vision.quick_check import analyze
    verdicts = []
    quick_rejects = []
    for frame in frames:
        # identity.face_embedding treats a raw ndarray as a precomputed
        # vector, so a BGR camera frame would be "normalized" whole and crash
        # against the stored template (shapes (480,640,3) vs (128,)). Frames
        # must be JPEG-encoded so they go through the real ArcFace pipeline,
        # exactly like the desktop's own recognition path. Test fakes may
        # pass plain bytes/strings through unchanged - only arrays encode.
        if isinstance(frame, np.ndarray):
            precheck = analyze(frame)
            if not precheck.get("usable"):
                quick_rejects.append(precheck["reason"])
                continue
            import cv2
            ok, jpeg = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            sample = jpeg.tobytes()
        elif isinstance(frame, (bytes, bytearray)):
            sample = bytes(frame)
        else:
            continue
        verdict = identity.identify(sample,
                                    admin_threshold=admin_threshold,
                                    db_path=db_path)
        verdicts.append(verdict)
        if verdict["status"] == "admin":
            break                     # one confident hit is enough
    if not verdicts:
        # Every frame was rejected by the pre-check (covered camera, blur, no
        # face, pose) - say WHY, so the caller can act like a normal assistant
        # instead of looping a failing biometric check.
        reason = quick_rejects[0] if quick_rejects else "no_usable_frame"
        return {"status": reason, "verified": False, "session": None}
    best = max(verdicts, key=lambda v: v.get("similarity", 0.0))
    if best["status"] == "admin":
        return {**best, "verified": True, "session": mint_session()}
    return {**best, "verified": False, "session": None}


def its_me(camera_index=0, db_path=None):
    """One call: grab frames, match, mint a session if it's really you.
    This is Tier 1 - no secret word involved."""
    frames = capture_frames(count=3, camera_index=camera_index)
    if not frames:
        return {"status": "camera_unavailable", "verified": False, "session": None}
    return recognize_me(frames, db_path=db_path)


def capture_embedding_dim(db_path=None):
    """The dimension of stored templates, for pipeline sanity checks."""
    from vision import identity
    templates = identity.store.list_face_templates(db_path=db_path)
    return len(templates[0]["embedding"]) if templates else 0


# ---- tier decisions ----------------------------------------------------
SENSITIVE_ACTIONS = {
    "password", "vault", "credential", "secret", "api key", "bank",
    "device_control", "bridge_action", "admin_transfer", "delete memory",
    "delete_memory", "delete my", "payment", "wallet",
}


def classify_request(text):
    """'simple info or task' -> tier1; anything sensitive -> tier2."""
    low = (text or "").lower()
    if any(word in low for word in SENSITIVE_ACTIONS):
        return "tier2"
    return "tier1"


def authorize(text, face_result, spoken_word_check=None):
    """The full policy in one function.

    face_result: the dict from recognize_me()/its_me().
    spoken_word_check: callable(str)->bool, present only when tier2.

    Tier 1: verified face is enough.
    Tier 2: verified face AND the secret word check passing.
    """
    tier = classify_request(text)
    if not face_result.get("verified"):
        return False, "face", tier
    if tier == "tier1":
        return True, "ok", tier
    if spoken_word_check is None or not callable(spoken_word_check):
        return False, "word_required", tier
    if spoken_word_check():
        return True, "ok", tier
    return False, "word", tier
