"""LYA's multi-user FACE IDENTITY ENGINE (iPhone-FaceID-style flow)
====================================================================
One ADMIN (full power), optional SECONDARY user (password, READ-ONLY),
and KNOWN FRIENDS (greeted by name). Unknown faces are stored as
'pending' — the next time the ADMIN wakes LYA, she asks who they were,
and once named they're recognized forever.

Uses ArcFace 512-d embeddings (via security/auth_wall.py).
All data encrypted at rest in person-scoped SQLite storage (storage/store.py).
"""
import os
import sys
import json
import time
import hashlib
import hmac
import secrets
from pathlib import Path
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import vault
from security import auth_wall
from storage import store

STORE = os.path.join(os.path.dirname(__file__), "known_faces.lya")

ADMIN, SECONDARY, FRIEND, UNKNOWN = "admin", "secondary", "friend", "unknown"


def _cos(a, b):
    a, b = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def face_embedding(source):
    """Normalize input into a unit-length 512-d embedding vector.
    Accepts raw list/array (mock or precomputed vectors) or JPEG bytes.
    """
    if isinstance(source, (list, tuple, np.ndarray)):
        arr = np.asarray(source, dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        return arr / (norm + 1e-9)
    return auth_wall.face_embedding(source)


def has_enrolled_admin(db_path: Path | None = None) -> bool:
    """Check if an active primary administrator face template exists."""
    try:
        admins = [t for t in store.list_face_templates(db_path=db_path) if t.get("role") == ADMIN]
        return len(admins) > 0
    except Exception:
        return False


# ---------------- ENROLLMENT ----------------

def enroll_person(name: str, role: str, samples: list, db_path: Path | None = None) -> bool:
    """Enroll a person from one or more face samples (JPEG bytes or 512-d vectors)."""
    embs = []
    for i, s in enumerate(samples):
        try:
            emb = face_embedding(s)
            embs.append(emb.tolist())
        except Exception as e:
            print(f"[LYA] sample {i + 1}/{len(samples)} unusable: {e}")
    if not embs:
        print(f"[LYA] enrollment FAILED for {name}: no usable face samples.")
        return False

    existing = [p for p in store.list_people(db_path=db_path) if p["display_name"].lower() == name.lower()]
    if existing:
        person_id = existing[0]["person_id"]
        store.remove_face_templates(person_id, db_path=db_path)
    else:
        person_id = store.create_person(display_name=name, role=role, db_path=db_path)

    for emb in embs:
        store.add_face_template(person_id, emb, model_version="arcface-512d", quality=1.0, db_path=db_path)

    print(f"[LYA] {name} enrolled as {role} ({len(embs)} face samples).")
    return True


def enroll_admin(sample, name: str = "admin", db_path: Path | None = None) -> bool:
    """Convenience wrapper: enroll the primary ADMIN."""
    if sample is None:
        raise ValueError("no camera frame captured")
    if not enroll_person(name, ADMIN, [sample], db_path=db_path):
        raise ValueError("no face detected in the frame")
    return True


# ---------------- SECONDARY PASSWORDS (per person) ----------------

def _pw_hash(password: str, salt: str) -> str:
    """Salted PBKDF2 — 200,000 SHA-256 iterations."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def set_secondary_password(name: str, password: str, db_path: Path | None = None) -> bool:
    """ADMIN sets a named secondary user's password (salted hash, encrypted)."""
    if not name or not password:
        return False
    salt = secrets.token_hex(16)
    pw_hash = _pw_hash(password, salt)
    cred_json = json.dumps({"salt": salt, "hash": pw_hash})

    people = [p for p in store.list_people(db_path=db_path) if p["display_name"].lower() == name.lower()]
    if people:
        person_id = people[0]["person_id"]
    else:
        person_id = store.create_person(display_name=name, role=SECONDARY, db_path=db_path)

    store.forget(person_id, exact_key="secondary_password", db_path=db_path)
    store.remember(person_id, key="secondary_password", value=cred_json, kind="credential", db_path=db_path)
    return True


def check_secondary_password(name: str, password: str, db_path: Path | None = None) -> bool:
    """Constant-time check of one named secondary's password."""
    if not name or not password:
        return False
    people = [p for p in store.list_people(db_path=db_path) if p["display_name"].lower() == name.lower()]
    if not people:
        return False
    person_id = people[0]["person_id"]
    for c in store.recall(person_id, kind="credential", db_path=db_path):
        if c["key"] == "secondary_password":
            try:
                rec = json.loads(c["value"])
                calc = _pw_hash(password, rec["salt"])
                return hmac.compare_digest(calc, rec["hash"])
            except Exception:
                return False
    return False


# ---------------- RECOGNITION ----------------

def identify(sample, admin_threshold: float = 0.45, friend_threshold: float = 0.50, db_path: Path | None = None) -> dict:
    """Match a webcam snapshot or face embedding against registered people in encrypted store.
    Returns dict: {status, name, who, role, similarity, person_id}
      status: 'admin' | 'secondary' | 'friend' | 'unknown' | 'no_face'
    """
    try:
        emb = face_embedding(sample)
    except Exception as e:
        return {
            "status": "no_face",
            "name": None,
            "who": None,
            "role": None,
            "similarity": 0.0,
            "person_id": None,
            "error": str(e),
        }

    templates = store.list_face_templates(db_path=db_path)
    best_person = None
    best_score = -1.0

    for t in templates:
        s = _cos(emb, t["embedding"])
        if s > best_score:
            best_score = s
            best_person = t

    thr = admin_threshold if (best_person and best_person["role"] == ADMIN) else friend_threshold

    if best_person and best_score >= thr:
        return {
            "status": best_person["role"],
            "name": best_person["display_name"],
            "who": best_person["display_name"],
            "role": best_person["role"],
            "person_id": best_person["person_id"],
            "similarity": round(best_score, 3),
        }

    # Unknown face — log to pending_faces for admin review
    try:
        store.record_pending_face(
            thumbnail_path=None,
            embedding=emb.tolist(),
            expires_days=7,
            db_path=db_path,
        )
    except Exception:
        pass

    return {
        "status": UNKNOWN,
        "name": None,
        "who": None,
        "role": UNKNOWN,
        "person_id": None,
        "similarity": round(best_score, 3) if best_score > 0 else 0.0,
    }


def list_pending(db_path: Path | None = None) -> list[dict]:
    """List pending unverified visitor faces."""
    return [
        {"id": p["pending_id"], "seen": p["first_seen"], "sightings": p.get("sightings", 1)}
        for p in store.list_pending_faces(db_path=db_path)
    ]


def verify_owner(sample, threshold: float = 0.60, db_path: Path | None = None) -> tuple[bool, str]:
    """Explicit owner verification with anti-spoof liveness check."""
    # Liveness verification on raw image bytes
    if isinstance(sample, bytes) and len(sample) > 512:
        from security.liveness import face_liveness
        live, _, reason = face_liveness(sample)
        if not live:
            return False, reason

    try:
        emb = face_embedding(sample)
    except Exception as e:
        return False, f"Face extraction error: {e}"

    admins = [t for t in store.list_face_templates(db_path=db_path) if t["role"] == ADMIN]
    if not admins:
        return False, "Exactly one enrolled primary admin is required."

    score = max((_cos(emb, t["embedding"]) for t in admins), default=-1.0)
    return score >= threshold, "Owner matched." if score >= threshold else f"Owner not recognized ({score:.2f} < {threshold:.2f})."


def name_person(face_id: str, name: str, role: str = FRIEND, db_path: Path | None = None) -> bool:
    """ADMIN names a stored stranger -> they become a known friend/person in encrypted store."""
    try:
        store.promote_pending_face(face_id, name, role=role, db_path=db_path)
        print(f"[LYA] Stranger {face_id} is now registered as {name} ({role}).")
        return True
    except Exception as e:
        print(f"[LYA] Failed to promote stranger {face_id}: {e}")
        return False


def forget(name: str, db_path: Path | None = None) -> bool:
    """Deactivate person and remove their enrolled face templates."""
    people = [p for p in store.list_people(db_path=db_path) if p["display_name"].lower() == name.lower()]
    for p in people:
        store.remove_face_templates(p["person_id"], db_path=db_path)
        with store.store_connection(db_path) as db:
            db.execute("UPDATE people SET active = 0 WHERE person_id = ?", (p["person_id"],))
    return True


# ---------------- WEBCAM SNAPSHOT ----------------

def snapshot_jpg(camera: int = 0, warmup: int = 4):
    """Grab one webcam frame as JPEG bytes (auto-exposure settling)."""
    try:
        import cv2
        cam = cv2.VideoCapture(camera)
        frame = None
        for _ in range(warmup):
            ok, frame = cam.read()
            if not ok:
                break
        cam.release()
        if frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes() if ok else None
    except Exception:
        return None

