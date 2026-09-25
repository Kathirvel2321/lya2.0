"""Bounded note retention and one-hop knowledge graph in the existing encrypted store.

These are internal storage operations. The workflow checks session and permission
before calling them. Model output never calls these functions.
"""
import time
import math
from storage import store
from security import vault

KINDS = {"fact", "preference", "lesson", "decision", "private"}
LIFETIMES = {"short": 7 * 86400, "long": 90 * 86400, "permanent": None}
RELATIONS = {"related_to", "depends_on", "supports", "contradicts"}
MAX_NOTES = 2000  # Keep whole-file encrypted transactions bounded on a laptop.


def expire(person_id, *, db_path=None, now=None):
    now = time.time() if now is None else now
    with store.store_connection(db_path) as db:
        cur = db.execute("DELETE FROM memories WHERE person_id = ? AND expires_at <= ?", (person_id, now))
        return cur.rowcount


def save(person_id, key, value, retention="short", *, until=None, kind="fact",
         db_path=None, now=None, correct=False):
    now = time.time() if now is None else now
    key, value = key.strip(), value.strip()
    if not person_id or not key or len(key) > 160 or not value or len(value) > 2000:
        raise ValueError("Use a non-empty label (up to 160 characters) and note (up to 2,000).")
    if kind not in KINDS:
        raise ValueError("Credentials are not conversational memories.")
    if retention == "until":
        if until is None or not math.isfinite(until) or until <= now:
            raise ValueError("The expiry must be a future timestamp with a timezone.")
        expiry = float(until)
    elif retention in LIFETIMES:
        ttl = LIFETIMES[retention]
        expiry = now + ttl if ttl else None
    else:
        raise ValueError("Choose short, long, until, permanent or session.")
    with store.store_connection(db_path) as db:
        if not db.execute("SELECT 1 FROM people WHERE person_id=? AND active=1", (person_id,)).fetchone():
            raise PermissionError("An active identity is required.")
        db.execute("DELETE FROM memories WHERE person_id=? AND expires_at<=?", (person_id, now))
        rows = db.execute("SELECT id,key_enc,kind,retention,expires_at FROM memories WHERE person_id=?", (person_id,)).fetchall()
        existing = [r for r in rows if vault.decrypt_text(r[1]).casefold() == key.casefold()]
        if len(existing) > 1:
            raise ValueError("That label has legacy duplicates. Resolve them before correcting it.")
        if existing:
            mid, _, old_kind, old_retention, old_expiry = existing[0]
            if old_kind not in KINDS:
                raise PermissionError("That label belongs to a protected record.")
            if not correct:
                raise ValueError("A note already has that label. Use correct label = value.")
            db.execute("UPDATE memories SET value_enc=?,revision=revision+1,updated_at=? WHERE id=?",
                       (vault.encrypt_text(value), str(now), mid))
            return {"id": mid, "retention": old_retention, "expires_at": old_expiry}
        if correct:
            raise ValueError("No active note has that label.")
        if len(rows) >= MAX_NOTES:
            raise ValueError("The 2,000-note budget is full. Review notes before saving more.")
        cur = db.execute("""INSERT INTO memories
            (person_id,kind,key_enc,value_enc,source,importance,hits,created_at,updated_at,retention,expires_at)
            VALUES (?,?,?,?, 'user',1,0,?,?,?,?)""",
            (person_id, kind, vault.encrypt_text(key), vault.encrypt_text(value), str(now), str(now), retention, expiry))
        return {"id": cur.lastrowid, "retention": retention, "expires_at": expiry}


def retrieve(person_id, query="", *, db_path=None, now=None, limit=6):
    """Rank scoped notes in the encrypted store's FTS index, then add graph evidence."""
    import re
    limit = max(0, min(int(limit), 6))
    if not limit or not person_id:
        return []
    now = time.time() if now is None else now
    ignored = {"what", "does", "have", "with", "that", "this", "please", "tell", "about", "should", "would", "could"}
    tokens = sorted({x for x in re.findall(r"\w+", query.casefold()) if len(x) > 2} - ignored)[:64]
    with store.store_connection(db_path, read_only=True) as db:
        if not db.execute("SELECT 1 FROM people WHERE person_id=? AND active=1", (person_id,)).fetchone():
            return []
        if tokens:
            # Quoted tokens are data, never caller-supplied FTS operators.
            expression = ' OR '.join('"' + token + '"' for token in tokens)
            ranked_ids = [mid for (mid,) in db.execute("""
                SELECT note_search.rowid FROM note_search
                JOIN memories m ON m.id=note_search.rowid
                WHERE note_search MATCH ? AND note_search.person_id=?
                  AND m.person_id=? AND m.kind IN ('fact','preference','lesson','decision','private')
                  AND (m.expires_at IS NULL OR m.expires_at>?)
                ORDER BY bm25(note_search,3.0,1.0),note_search.rowid DESC LIMIT ?""",
                (expression, person_id, person_id, now, limit))]
        else:
            ranked_ids = [mid for (mid,) in db.execute("""
                SELECT id FROM memories WHERE person_id=?
                  AND kind IN ('fact','preference','lesson','decision','private')
                  AND (expires_at IS NULL OR expires_at>?)
                ORDER BY id DESC LIMIT ?""", (person_id, now, limit))]
        if not ranked_ids:
            return []
        seeds = ranked_ids[:max(1, limit-2)] if tokens else ranked_ids
        candidates = []
        if tokens:
            placeholders = ','.join('?' for _ in seeds)
            edges = db.execute(f"""SELECT src,dst,relation FROM memory_links
                WHERE src IN ({placeholders}) OR dst IN ({placeholders})""", (*seeds, *seeds))
            priority = {'contradicts': 0, 'depends_on': 1, 'supports': 2, 'related_to': 3}
            for src, dst, relation in edges:
                other = dst if src in seeds else src
                if other not in seeds:
                    candidates.append((priority.get(relation, 4), other))
        order = list(seeds) + [mid for _, mid in sorted(candidates)] + ranked_ids
        ids = list(dict.fromkeys(order))
        placeholders = ','.join('?' for _ in ids)
        rows = db.execute(f"""SELECT id,kind,key_enc,value_enc,source,importance,hits,
            created_at,retention,expires_at,revision FROM memories
            WHERE id IN ({placeholders}) AND person_id=?
              AND kind IN ('fact','preference','lesson','decision','private')
              AND (expires_at IS NULL OR expires_at>?)""", (*ids, person_id, now))
        by_id = {}
        for mid, kind, key_enc, value_enc, source, importance, hits, created, retention, expiry, revision in rows:
            try:
                key, value = vault.decrypt_text(key_enc), vault.decrypt_text(value_enc)
            except Exception:
                continue
            by_id[mid] = {"id": mid, "person_id": person_id, "kind": kind, "key": key,
                          "value": value, "source": source, "importance": importance,
                          "hits": hits, "created_at": created, "retention": retention,
                          "expires_at": expiry, "revision": revision}
        return [by_id[mid] for mid in ids if mid in by_id][:limit]


def link(person_id, src, relation, dst, *, db_path=None, now=None):
    if relation not in RELATIONS or src == dst:
        raise ValueError("Use two different notes and related_to, depends_on, supports or contradicts.")
    now = time.time() if now is None else now
    with store.store_connection(db_path) as db:
        rows = db.execute("SELECT id,kind FROM memories WHERE person_id=? AND id IN (?,?) AND (expires_at IS NULL OR expires_at>?)",
                          (person_id, src, dst, now)).fetchall()
        if len(rows) != 2 or any(kind not in KINDS for _, kind in rows):
            raise PermissionError("Both active notes must belong to this person.")
        db.execute("INSERT OR IGNORE INTO memory_links(src,dst,relation) VALUES (?,?,?)", (src, dst, relation))


def graph(person_id, *, db_path=None, now=None):
    active = {r["id"]: r for r in store.recall(person_id, limit=MAX_NOTES, db_path=db_path, context_only=True, now=now)}
    with store.store_connection(db_path, read_only=True) as db:
        rows = db.execute("SELECT src,relation,dst FROM memory_links WHERE src IN (SELECT id FROM memories WHERE person_id=?) LIMIT 200", (person_id,)).fetchall()
    return [(active[a]["key"], relation, active[b]["key"]) for a, relation, b in rows if a in active and b in active]
