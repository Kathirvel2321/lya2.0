"""storage/store.py — Clean, encrypted, person-scoped storage for LYA.

Implements the architecture agreed in LYA_FOUNDATION_DECISIONS.md:
- Store lives outside the repository root in %LOCALAPPDATA%\\LYA (or LYA_DATA_DIR)
- AES-256 encrypted SQLite at rest with atomic replacement and process locking
- Person-scoped schemas: people, face_templates, pending_faces, memories, vault_items, audit_events
- Unknown thumbnails expire automatically after 7 days
- Audit log never stores secrets, biometric data, or private transcript text
"""

from contextlib import contextmanager
import datetime
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time

from security import vault

_store_lock = threading.RLock()


def get_data_dir() -> Path:
    """Return root directory for LYA runtime data outside source code."""
    custom = os.environ.get("LYA_DATA_DIR")
    if custom:
        return Path(custom).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return (Path(local_app_data) / "LYA").resolve()
    return (Path.home() / ".local" / "share" / "LYA").resolve()


def ensure_layout(base_dir: Path | None = None) -> dict[str, Path]:
    """Ensure standard LYA directory layout exists."""
    base = base_dir or get_data_dir()
    dirs = {
        "root": base,
        "faces": base / "faces",
        "vault": base / "vault",
        "models": base / "models",
        "logs": base / "logs",
        "db": base / "lya.db.enc",
    }
    for key in ("faces", "vault", "models", "logs"):
        dirs[key].mkdir(parents=True, exist_ok=True)
    return dirs


@contextmanager
def store_connection(db_path: Path | None = None):
    """Encrypted in-memory SQLite with thread/process locking and atomic write."""
    target = db_path or (get_data_dir() / "lya.db.enc")
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_file = str(target) + ".lock"

    with _store_lock, open(lock_file, "a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0, 2)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            deadline = time.monotonic() + 10.0
            while True:
                try:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("LYA database lock timeout.")
                    time.sleep(0.04)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)

        db = sqlite3.connect(":memory:")
        try:
            if target.exists() and target.stat().st_size > 0:
                raw_enc = target.read_bytes()
                db.deserialize(vault.decrypt(raw_enc))
            db.execute("PRAGMA foreign_keys = ON")
            _init_schema(db)
            yield db
            db.commit()
            serialized = db.serialize()
            encrypted = vault.encrypt(serialized)
            tmp_path = target.with_name(target.name + f".tmp.{secrets.token_hex(4)}")
            with open(tmp_path, "wb") as f:
                f.write(encrypted)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        finally:
            db.close()
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def _init_schema(db: sqlite3.Connection):
    """Initialize person-scoped database schemas."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS people (
            person_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'friend',
            created_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS face_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL REFERENCES people(person_id),
            embedding_enc TEXT NOT NULL,
            model_version TEXT NOT NULL,
            quality REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pending_faces (
            pending_id TEXT PRIMARY KEY,
            thumbnail_path TEXT,
            embedding_enc TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            sightings INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL REFERENCES people(person_id),
            kind TEXT NOT NULL,
            key_enc TEXT NOT NULL,
            value_enc TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'user',
            importance REAL NOT NULL DEFAULT 1.0,
            hits INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL REFERENCES people(person_id),
            label_enc TEXT NOT NULL,
            file_path_enc TEXT NOT NULL,
            sync_policy TEXT NOT NULL DEFAULT 'laptop_only',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            action_type TEXT NOT NULL,
            outcome TEXT NOT NULL,
            person_id TEXT
        );
    """)

    # Additive migration: existing rows retain their previous, non-expiring policy.
    columns = {r[1] for r in db.execute("PRAGMA table_info(memories)")}
    for name, definition in (("retention", "TEXT NOT NULL DEFAULT 'permanent'"),
                             ("expires_at", "REAL"), ("revision", "INTEGER NOT NULL DEFAULT 1")):
        if name not in columns:
            db.execute(f"ALTER TABLE memories ADD COLUMN {name} {definition}")
    db.execute("""CREATE TABLE IF NOT EXISTS memory_links (
        src INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
        dst INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
        relation TEXT NOT NULL,
        PRIMARY KEY(src, dst, relation))""")
    db.execute("CREATE INDEX IF NOT EXISTS memory_owner_expiry ON memories(person_id, expires_at)")


# ---------------------------------------------------------- People / Profiles

def create_person(display_name: str, role: str = "friend", db_path: Path | None = None) -> str:
    """Create a new person profile and return person_id."""
    person_id = "p_" + secrets.token_urlsafe(12)
    now = datetime.datetime.now().isoformat()
    with store_connection(db_path) as db:
        db.execute(
            "INSERT INTO people (person_id, display_name, role, created_at, active) VALUES (?, ?, ?, ?, 1)",
            (person_id, display_name.strip(), role.strip().lower(), now),
        )
    record_audit("create_person", f"role={role}", person_id=person_id, db_path=db_path)
    return person_id


def get_person(person_id: str, db_path: Path | None = None) -> dict | None:
    """Fetch person record by ID."""
    with store_connection(db_path) as db:
        row = db.execute(
            "SELECT person_id, display_name, role, created_at, active FROM people WHERE person_id = ?",
            (person_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "person_id": row[0],
            "display_name": row[1],
            "role": row[2],
            "created_at": row[3],
            "active": bool(row[4]),
        }


def list_people(active_only: bool = True, db_path: Path | None = None) -> list[dict]:
    """List registered people."""
    with store_connection(db_path) as db:
        q = "SELECT person_id, display_name, role, created_at, active FROM people"
        if active_only:
            q += " WHERE active = 1"
        q += " ORDER BY created_at ASC"
        return [
            {
                "person_id": r[0],
                "display_name": r[1],
                "role": r[2],
                "created_at": r[3],
                "active": bool(r[4]),
            }
            for r in db.execute(q).fetchall()
        ]


# ---------------------------------------------------------- Face Templates

def add_face_template(
    person_id: str,
    embedding: list[float] | object,
    model_version: str = "arcface-512d",
    quality: float = 1.0,
    db_path: Path | None = None,
) -> int:
    """Save an encrypted biometric face template for a registered person."""
    if not person_id:
        raise ValueError("Cannot save face template without person_id.")
    if hasattr(embedding, "tolist"):
        emb_list = embedding.tolist()
    else:
        emb_list = list(embedding)
    now = datetime.datetime.now().isoformat()
    emb_enc = vault.encrypt_text(json.dumps(emb_list))

    with store_connection(db_path) as db:
        person = db.execute("SELECT active FROM people WHERE person_id = ?", (person_id,)).fetchone()
        if not person or not person[0]:
            raise PermissionError(f"Active person profile not found for ID: {person_id}")
        cur = db.execute(
            """INSERT INTO face_templates (person_id, embedding_enc, model_version, quality, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (person_id, emb_enc, model_version, float(quality), now),
        )
        template_id = cur.lastrowid
    record_audit("face_template_add", f"model={model_version}", person_id=person_id, db_path=db_path)
    return template_id


def list_face_templates(
    person_id: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Retrieve decrypted face templates, optionally filtered by person_id."""
    with store_connection(db_path) as db:
        q = """SELECT t.id, t.person_id, t.embedding_enc, t.model_version, t.quality, t.created_at, p.display_name, p.role
               FROM face_templates t
               JOIN people p ON t.person_id = p.person_id
               WHERE p.active = 1"""
        args = []
        if person_id:
            q += " AND t.person_id = ?"
            args.append(person_id)
        q += " ORDER BY t.id ASC"

        results = []
        for tid, pid, emb_enc, model_ver, qual, created, dname, role in db.execute(q, args).fetchall():
            try:
                emb = json.loads(vault.decrypt_text(emb_enc))
            except Exception:
                continue
            results.append({
                "template_id": tid,
                "person_id": pid,
                "display_name": dname,
                "role": role,
                "embedding": emb,
                "model_version": model_ver,
                "quality": qual,
                "created_at": created,
            })
        return results


def remove_face_templates(person_id: str, db_path: Path | None = None) -> int:
    """Remove all face templates for the specified person_id."""
    if not person_id:
        return 0
    with store_connection(db_path) as db:
        cur = db.execute("DELETE FROM face_templates WHERE person_id = ?", (person_id,))
        count = cur.rowcount
    if count:
        record_audit("face_templates_removed", f"count={count}", person_id=person_id, db_path=db_path)
    return count


# ---------------------------------------------------------- Person-Scoped Memory

def remember(
    person_id: str,
    key: str,
    value: str,
    kind: str = "fact",
    importance: float = 1.0,
    source: str = "user",
    db_path: Path | None = None,
) -> int:
    """Save an encrypted memory scoped strictly to person_id."""
    if not person_id:
        raise ValueError("Cannot save memory without a valid person_id.")
    now = datetime.datetime.now().isoformat()
    key_enc = vault.encrypt_text(key.strip())
    val_enc = vault.encrypt_text(value.strip())

    with store_connection(db_path) as db:
        # Verify person exists
        person = db.execute("SELECT active FROM people WHERE person_id = ?", (person_id,)).fetchone()
        if not person or not person[0]:
            raise PermissionError(f"Active person profile not found for ID: {person_id}")

        cur = db.execute(
            """INSERT INTO memories
               (person_id, kind, key_enc, value_enc, source, importance, hits, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (person_id, kind, key_enc, val_enc, source, importance, now, now),
        )
        mem_id = cur.lastrowid
    record_audit("memory_write", f"kind={kind}", person_id=person_id, db_path=db_path)
    return mem_id


def recall(
    person_id: str,
    query: str | None = None,
    kind: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
    context_only: bool = False,
    now: float | None = None,
) -> list[dict]:
    """Recall memories strictly scoped to the specified person_id."""
    if not person_id:
        return []
    with store_connection(db_path) as db:
        now = time.time() if now is None else now
        q = "SELECT id, kind, key_enc, value_enc, source, importance, hits, created_at, retention, expires_at, revision FROM memories WHERE person_id = ? AND (expires_at IS NULL OR expires_at > ?) AND EXISTS (SELECT 1 FROM people WHERE person_id = memories.person_id AND active = 1)"
        args: list = [person_id, now]
        if context_only:
            q += " AND kind IN ('fact', 'preference', 'lesson', 'decision', 'private')"
        if kind:
            q += " AND kind = ?"
            args.append(kind)
        q += " ORDER BY importance DESC, hits DESC, id DESC"

        results = []
        for mid, mkind, k_enc, v_enc, src, imp, hits, created, retention, expiry, revision in db.execute(q, args):
            try:
                k = vault.decrypt_text(k_enc)
                v = vault.decrypt_text(v_enc)
            except Exception:
                continue

            if query:
                q_low = query.lower()
                if q_low not in k.lower() and q_low not in v.lower():
                    continue

            results.append({
                "id": mid,
                "person_id": person_id,
                "kind": mkind,
                "key": k,
                "value": v,
                "source": src,
                "importance": imp,
                "hits": hits,
                "created_at": created,
                "retention": retention,
                "expires_at": expiry,
                "revision": revision,
            })
            if len(results) >= limit:
                break
        return results


def forget(person_id: str, exact_key: str, db_path: Path | None = None) -> int:
    """Delete memories matching exact key for the given person_id."""
    if not person_id:
        return 0
    deleted_count = 0
    with store_connection(db_path) as db:
        rows = db.execute("SELECT id, key_enc FROM memories WHERE person_id = ?", (person_id,)).fetchall()
        for mid, k_enc in rows:
            try:
                k = vault.decrypt_text(k_enc)
                if k.strip().lower() == exact_key.strip().lower():
                    db.execute("DELETE FROM memories WHERE id = ?", (mid,))
                    deleted_count += 1
            except Exception:
                continue
    if deleted_count:
        record_audit("memory_forget", f"deleted={deleted_count}", person_id=person_id, db_path=db_path)
    return deleted_count


# ---------------------------------------------------------- Pending Faces (7-day Expiry)

def record_pending_face(
    thumbnail_path: str | None = None,
    embedding: object = None,
    expires_days: int = 7,
    db_path: Path | None = None,
    embedding_bytes: object = None,
) -> str:
    """Record an unknown face observation. Expires automatically in 7 days."""
    now_dt = datetime.datetime.now()
    now_iso = now_dt.isoformat()
    expiry_iso = (now_dt + datetime.timedelta(days=expires_days)).isoformat()
    pending_id = "face_" + secrets.token_urlsafe(8)
    raw_emb = embedding if embedding is not None else embedding_bytes
    emb_enc = None
    if raw_emb is not None:
        if isinstance(raw_emb, bytes):
            if len(raw_emb) % 4 == 0 and len(raw_emb) >= 128:
                import numpy as np
                emb_list = np.frombuffer(raw_emb, dtype=np.float32).tolist()
            else:
                emb_list = list(raw_emb)
        elif hasattr(raw_emb, "tolist"):
            emb_list = raw_emb.tolist()
        else:
            emb_list = list(raw_emb)
        emb_enc = vault.encrypt_text(json.dumps(emb_list))

    with store_connection(db_path) as db:
        # Cleanup expired on write
        db.execute("DELETE FROM pending_faces WHERE expires_at <= ?", (now_iso,))
        db.execute(
            """INSERT INTO pending_faces
               (pending_id, thumbnail_path, embedding_enc, first_seen, last_seen, sightings, expires_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (pending_id, thumbnail_path, emb_enc, now_iso, now_iso, expiry_iso),
        )
    record_audit("pending_face_captured", "unknown_visitor", db_path=db_path)
    return pending_id


def list_pending_faces(db_path: Path | None = None) -> list[dict]:
    """List pending visitor faces that have not yet expired."""
    now_iso = datetime.datetime.now().isoformat()
    with store_connection(db_path) as db:
        db.execute("DELETE FROM pending_faces WHERE expires_at <= ?", (now_iso,))
        rows = db.execute(
            "SELECT pending_id, thumbnail_path, first_seen, last_seen, sightings, expires_at FROM pending_faces ORDER BY last_seen DESC"
        ).fetchall()
        return [
            {
                "pending_id": r[0],
                "thumbnail_path": r[1],
                "first_seen": r[2],
                "last_seen": r[3],
                "sightings": r[4],
                "expires_at": r[5],
            }
            for r in rows
        ]


def promote_pending_face(
    pending_id: str,
    display_name: str,
    role: str = "friend",
    db_path: Path | None = None,
) -> str:
    """Admin tags a pending face, creating a verified person and template."""
    with store_connection(db_path) as db:
        face = db.execute(
            "SELECT embedding_enc FROM pending_faces WHERE pending_id = ? AND expires_at > ?",
            (pending_id, datetime.datetime.now().isoformat()),
        ).fetchone()
        if not face:
            raise KeyError(f"Pending face {pending_id} not found or expired.")
        emb_enc = face[0]

        person_id = "p_" + secrets.token_urlsafe(12)
        now = datetime.datetime.now().isoformat()
        db.execute(
            "INSERT INTO people (person_id, display_name, role, created_at, active) VALUES (?, ?, ?, ?, 1)",
            (person_id, display_name.strip(), role.strip().lower(), now),
        )
        if emb_enc:
            db.execute(
                """INSERT INTO face_templates
                   (person_id, embedding_enc, model_version, quality, created_at)
                   VALUES (?, ?, 'insightface-buffalo_l', 1.0, ?)""",
                (person_id, emb_enc, now),
            )
        db.execute("DELETE FROM pending_faces WHERE pending_id = ?", (pending_id,))

    record_audit("promote_face", f"name={display_name}, role={role}", person_id=person_id, db_path=db_path)
    return person_id


# ---------------------------------------------------------- Audit Log (Safe, Privacy Preserving)

def record_audit(action_type: str, outcome: str, person_id: str | None = None, db_path: Path | None = None):
    """Record an audit event. NEVER accepts passwords, secrets, transcripts, or images."""
    now = datetime.datetime.now().isoformat()
    try:
        with store_connection(db_path) as db:
            db.execute(
                "INSERT INTO audit_events (time, action_type, outcome, person_id) VALUES (?, ?, ?, ?)",
                (now, str(action_type)[:64], str(outcome)[:128], person_id),
            )
    except Exception:
        # Audit failures must not crash caller
        pass


def list_audit_events(limit: int = 50, db_path: Path | None = None) -> list[dict]:
    """Retrieve audit records."""
    with store_connection(db_path) as db:
        rows = db.execute(
            "SELECT id, time, action_type, outcome, person_id FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "time": r[1],
                "action_type": r[2],
                "outcome": r[3],
                "person_id": r[4],
            }
            for r in rows
        ]
