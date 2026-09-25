"""Portable selected-note backups and bounded file operations. No cloud or sensors.

The caller is a trusted controller, never model-generated code. It supplies the
current session and approval gate. Keys must be generated with new_recovery_key,
kept separately from the returned ciphertext, and never placed in logs/prompts.
This key recovers notes only, not identity, Windows keys, files or biometrics.
"""
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from brain.notes import KINDS, RELATIONS, MAX_NOTES
from security import vault
from security.approval import ApprovalGate
from security.policy import Session
from storage import store

MAGIC = b"LYA-NOTES-1\n"
MAX_BYTES = 16 * 1024 * 1024
MAX_LINKS = 8000
FIELDS = {"id", "kind", "key", "value", "source", "created_at", "updated_at",
          "retention", "expires_at", "revision"}


def new_recovery_key():
    """Return a random Fernet key; not a human password or registration code."""
    return Fernet.generate_key()


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _now(clock):
    now = clock()
    if not math.isfinite(now):
        raise PermissionError("Trusted clock unavailable.")
    return now


def _session(get_session, clock, expected=None):
    s = get_session()
    if (type(s) is not Session or s.role != "admin" or not s.id or not s.person_id
            or not math.isfinite(s.verified_until) or s.verified_until <= _now(clock)
            or (expected is not None and s != expected)):
        raise PermissionError("A current verified owner session is required.")
    return s


def _owner(db, s):
    if not db.execute("SELECT 1 FROM people WHERE person_id=? AND active=1 AND role='admin'",
                      (s.person_id,)).fetchone():
        raise PermissionError("Owner profile is inactive or changed.")


def _authorize(action, params, get_session, approve, db_path, clock):
    s = _session(get_session, clock)
    with store.store_connection(db_path, read_only=True) as db:
        _owner(db, s)
    gate = approve if approve is not None else ApprovalGate(wall_clock=clock)
    if gate(action, _encode(params).decode("utf-8"), s) is not True:
        raise PermissionError("Exact owner approval is required.")
    _session(get_session, clock, s)
    return s


def _validate(data):
    if (type(data) is not dict or set(data) != {"format", "created_at", "notes", "links"}
            or data["format"] != "lya-selected-notes/v1"
            or type(data["created_at"]) not in (int, float)
            or not math.isfinite(data["created_at"])):
        raise ValueError("Unsupported or malformed backup format.")
    rows, links = data["notes"], data["links"]
    if type(rows) is not list or not 1 <= len(rows) <= MAX_NOTES:
        raise ValueError("Invalid note count.")
    ids, labels = set(), set()
    for row in rows:
        if type(row) is not dict or set(row) != FIELDS:
            raise ValueError("Unexpected note fields.")
        for field, limit in (("key", 160), ("value", 2000), ("source", 64),
                             ("created_at", 64), ("updated_at", 64)):
            if type(row[field]) is not str or not row[field].strip() or len(row[field]) > limit:
                raise ValueError("Invalid note text.")
        if (type(row["id"]) is not int or row["id"] <= 0 or row["id"] in ids
                or row["key"].strip().casefold() in labels
                or type(row["revision"]) is not int or not 1 <= row["revision"] <= 2147483647
                or type(row["kind"]) is not str or row["kind"] not in KINDS
                or row["retention"] not in ("short", "long", "until", "permanent")):
            raise ValueError("Invalid or duplicate note metadata.")
        expiry = row["expires_at"]
        if row["retention"] == "permanent":
            if expiry is not None:
                raise ValueError("Permanent note cannot have an expiry.")
        elif type(expiry) not in (int, float) or not math.isfinite(expiry):
            raise ValueError("Timed note must have a finite expiry.")
        ids.add(row["id"])
        labels.add(row["key"].strip().casefold())
    if type(links) is not list or len(links) > MAX_LINKS:
        raise ValueError("Invalid link count.")
    seen = set()
    for edge in links:
        if (type(edge) is not list or len(edge) != 3 or type(edge[0]) is not int
                or type(edge[2]) is not int or type(edge[1]) is not str
                or edge[0] not in ids or edge[2] not in ids or edge[0] == edge[2]
                or edge[1] not in RELATIONS or tuple(edge) in seen):
            raise ValueError("Invalid note relationship.")
        seen.add(tuple(edge))


def export_notes(note_ids, recovery_key, *, get_session, db_path, approve=None,
                 cancelled=lambda: False, clock=time.time, destination=None):
    """Return authenticated ciphertext for the explicitly selected owner's notes."""
    db_path = Path(db_path).resolve()
    ids = list(note_ids)
    if (not 1 <= len(ids) <= MAX_NOTES or any(type(n) is not int or n <= 0 for n in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("Select unique note IDs within the note budget.")
    ids.sort()
    cipher = Fernet(recovery_key)
    params = {"operation": "export-selected-notes", "count": len(ids),
              "selection_sha256": hashlib.sha256(_encode(ids)).hexdigest(),
              "key_sha256": hashlib.sha256(recovery_key).hexdigest(),
              "database": str(db_path)}
    if destination is not None:
        params["destination"] = str(Path(destination).resolve())
    if cancelled():
        raise PermissionError("Backup cancelled.")
    s = _authorize("memory_backup", params, get_session, approve, db_path, clock)
    with store.store_connection(db_path, read_only=True) as db:
        _owner(db, s)
        rows = []
        now = _now(clock)
        for mid in ids:
            row = db.execute("""SELECT id,kind,key_enc,value_enc,source,created_at,updated_at,
                retention,expires_at,revision FROM memories WHERE id=? AND person_id=?""",
                             (mid, s.person_id)).fetchone()
            if not row or row[1] not in KINDS or (row[8] is not None and row[8] <= now):
                raise PermissionError("Selection includes unavailable or protected notes.")
            values = list(row)
            values[2], values[3] = vault.decrypt_text(row[2]), vault.decrypt_text(row[3])
            rows.append(dict(zip(("id", "kind", "key", "value", "source", "created_at",
                                  "updated_at", "retention", "expires_at", "revision"), values)))
        selected = set(ids)
        links = []
        for a, relation, b in db.execute("""SELECT src,relation,dst FROM memory_links
            WHERE src IN (SELECT id FROM memories WHERE person_id=?)""", (s.person_id,)):
            if a in selected and b in selected:
                links.append([a, relation, b])
                if len(links) > MAX_LINKS:
                    raise ValueError("Too many relationships for one backup.")
        data = {"format": "lya-selected-notes/v1", "created_at": now, "notes": rows, "links": links}
        _validate(data)
        raw = _encode(data)
        if len(raw) > MAX_BYTES // 2:
            raise ValueError("Backup exceeds the size budget.")
        result = MAGIC + cipher.encrypt(raw)
        _session(get_session, clock, s)
        if cancelled() or any(r["expires_at"] is not None and r["expires_at"] <= _now(clock) for r in rows):
            raise PermissionError("Backup cancelled or selected note expired.")
        return result


def restore_notes(blob, recovery_key, *, get_session, db_path, approve=None,
                  cancelled=lambda: False, clock=time.time):
    """Restore into an empty, verified owner profile; never import identity or roles.

    Requires an already initialized destination store. Original expiries survive;
    expired records and their edges are skipped. Existing notes are never merged.
    """
    db_path = Path(db_path).resolve()
    if type(blob) is not bytes or len(blob) > MAX_BYTES or not blob.startswith(MAGIC):
        raise ValueError("Unsupported or oversized backup.")
    if cancelled():
        raise PermissionError("Restore cancelled.")
    params = {"operation": "restore-to-empty-profile", "database": str(db_path),
              "archive_sha256": hashlib.sha256(blob).hexdigest()}
    s = _authorize("memory_restore", params, get_session, approve, db_path, clock)
    data = _decode(blob, recovery_key)
    now = _now(clock)
    rows = [r for r in data["notes"] if r["expires_at"] is None or r["expires_at"] > now]
    with store.store_connection(db_path) as db:
        _owner(db, s)
        if db.execute("SELECT 1 FROM memories WHERE person_id=? LIMIT 1", (s.person_id,)).fetchone():
            raise PermissionError("Restore requires an empty owner profile; existing notes are preserved.")
        mapping = {}
        for row in rows:
            cur = db.execute("""INSERT INTO memories (person_id,kind,key_enc,value_enc,source,
                created_at,updated_at,retention,expires_at,revision) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (s.person_id, row["kind"], vault.encrypt_text(row["key"]), vault.encrypt_text(row["value"]),
                 row["source"], row["created_at"], row["updated_at"], row["retention"],
                 row["expires_at"], row["revision"]))
            mapping[row["id"]] = cur.lastrowid
        for a, relation, b in data["links"]:
            if a in mapping and b in mapping:
                db.execute("INSERT INTO memory_links(src,dst,relation) VALUES (?,?,?)",
                           (mapping[a], mapping[b], relation))
        _session(get_session, clock, s)
        if cancelled() or any(r["expires_at"] is not None and r["expires_at"] <= _now(clock) for r in rows):
            raise PermissionError("Restore cancelled or note expired during restore.")
        db.execute("INSERT INTO audit_events(time,action_type,outcome,person_id) VALUES (?,?,?,?)",
                   (str(now), "notes_restored", "portable_v1", s.person_id))
    return {"restored": len(rows), "expired_skipped": len(data["notes"]) - len(rows)}


def _decode(blob, key):
    if type(blob) is not bytes or len(blob) > MAX_BYTES or not blob.startswith(MAGIC):
        raise ValueError("Unsupported or oversized backup.")
    try:
        data = json.loads(Fernet(key).decrypt(blob[len(MAGIC):]))
    except (InvalidToken, ValueError, UnicodeError, RecursionError):
        raise ValueError("Backup key or authenticated contents are invalid.") from None
    _validate(data)
    return data


def list_notes(*, get_session, db_path, approve=None, cancelled=lambda: False, clock=time.time):
    """Approved owner-only label list. Never return note values or credential labels."""
    db_path = Path(db_path).resolve()
    s = _authorize("memory_read", {"operation": "recovery-note-list", "database": str(db_path)},
                   get_session, approve, db_path, clock)
    with store.store_connection(db_path, read_only=True) as db:
        _owner(db, s)
        rows = db.execute("""SELECT id,kind,key_enc,retention,expires_at FROM memories
            WHERE person_id=? AND (expires_at IS NULL OR expires_at>?) LIMIT ?""",
            (s.person_id, _now(clock), MAX_NOTES + 1)).fetchall()
        if len(rows) > MAX_NOTES:
            raise ValueError("Note budget exceeded.")
        result = [{"id": r[0], "label": vault.decrypt_text(r[2]), "retention": r[3],
                   "expires_at": r[4]} for r in rows if r[1] in KINDS]
        _session(get_session, clock, s)
        if cancelled():
            raise PermissionError("Cancelled.")
        return result


def export_file(note_ids, key, archive_path, **options):
    """Publish ciphertext atomically without overwriting. Never write the key."""
    note_ids = tuple(note_ids)
    target = Path(archive_path).resolve()
    if target.suffix != ".lya-notes" or target.exists():
        raise ValueError("Choose a new .lya-notes file; existing files cannot be overwritten.")
    clock = options.get("clock", time.time)
    cancelled = options.get("cancelled", lambda: False)
    s = _session(options["get_session"], clock)
    blob = export_notes(note_ids, key, destination=target, **options)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".lya-backup-", suffix=".tmp", dir=target.parent,
                                         delete=False) as out:
            temp = Path(out.name)
            out.write(blob)
            out.flush()
            os.fsync(out.fileno())
        # Recheck owner under the store lock immediately before publishing.
        with store.store_connection(Path(options["db_path"]).resolve(), read_only=True) as db:
            _owner(db, s)
            _session(options["get_session"], clock, s)
            if cancelled():
                raise PermissionError("Backup cancelled.")
            if os.name == "nt":
                os.rename(temp, target)  # Windows rename fails if destination exists.
            else:
                os.link(temp, target)  # Atomic no-clobber publication on POSIX.
        return {"saved": len(note_ids)}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def _read_archive(path):
    with open(path, "rb") as source:
        blob = source.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("Archive exceeds the size budget.")
    return blob


def preview_file(path, key, *, get_session, db_path, approve=None,
                 cancelled=lambda: False, clock=time.time):
    """Authenticate contents before showing a bounded restore summary."""
    db_path = Path(db_path).resolve()
    # Do not even open the archive for an unverified session.
    s = _session(get_session, clock)
    blob = _read_archive(path)
    digest = hashlib.sha256(blob).hexdigest()
    _authorize("memory_restore", {"operation": "preview-archive", "archive_sha256": digest,
                "database": str(Path(db_path).resolve())}, get_session, approve, db_path, clock)
    data = _decode(blob, key)
    _session(get_session, clock, s)
    with store.store_connection(db_path, read_only=True) as db:
        _owner(db, s)
        empty = not db.execute("SELECT 1 FROM memories WHERE person_id=? LIMIT 1", (s.person_id,)).fetchone()
    if cancelled():
        raise PermissionError("Preview cancelled.")
    expired = sum(r["expires_at"] is not None and r["expires_at"] <= _now(clock) for r in data["notes"])
    return {"digest": digest, "available": len(data["notes"]) - expired, "expired": expired, "empty": empty}


def restore_file(path, key, expected_digest, **options):
    _session(options["get_session"], options.get("clock", time.time))
    blob = _read_archive(path)
    if hashlib.sha256(blob).hexdigest() != expected_digest:
        raise ValueError("Archive changed after preview. Preview it again.")
    return restore_notes(blob, key, **options)
