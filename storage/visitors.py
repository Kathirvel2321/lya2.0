"""Native owner-controlled registry. Stored only in the existing encrypted database."""
import datetime
import hashlib
import json
from pathlib import Path
import secrets

from security import vault
from security.owner_profiles import FACE_MODEL, checked_vector
from storage import store


VISITOR_ROLES = frozenset(('friend', 'family'))
VISITOR_STYLES = frozenset(('warm', 'brief', 'formal', 'casual'))
PHOTO_RETENTION_DAYS = 7


def credential_digest(credential):
    return hashlib.sha256(credential.encode('ascii')).hexdigest()


def owner_check(db,session):
    store._profile_owner(db,session)
    return db.execute('SELECT credential FROM owner_passkeys WHERE person_id=?',(session.person_id,)).fetchone()[0]


def set_enabled(session, enabled, db_path=None):
    if type(enabled) is not bool:
        raise ValueError('Explicit recognition preference required.')
    with store.store_connection(db_path) as db:
        credential = owner_check(db,session)
        count = db.execute('SELECT COUNT(*) FROM face_templates WHERE person_id=? AND model_version=?',
                           (session.person_id,FACE_MODEL)).fetchone()[0]
        if enabled and count != 3:
            raise PermissionError('Finish the consented owner face profiles first.')
        enable_in_transaction(db,session.person_id,credential,enabled)


def enable_in_transaction(db,owner,credential,enabled=True):
    db.execute('INSERT OR REPLACE INTO recognition_preferences VALUES(?,?,?)',
               (owner,credential_digest(credential),int(enabled)))


def set_photo_enabled(session, enabled, db_path=None):
    if type(enabled) is not bool:
        raise ValueError('Explicit visitor-photo preference required.')
    with store.store_connection(db_path) as db:
        credential = owner_check(db, session)
        db.execute('INSERT OR REPLACE INTO visitor_photo_preferences VALUES(?,?,?)',
                   (session.person_id, credential_digest(credential), int(enabled)))


def photo_enabled(db_path=None):
    target = Path(db_path) if db_path is not None else store.get_data_dir()/'lya.db.enc'
    if not target.is_file():
        return False
    with store.store_connection(target, read_only=True) as db:
        owners = db.execute("SELECT p.person_id,k.credential FROM people p JOIN owner_passkeys k USING(person_id) WHERE p.role='admin' AND p.active=1 LIMIT 2").fetchall()
        if len(owners) != 1 or db.execute("SELECT COUNT(*) FROM people WHERE role='admin' AND active=1").fetchone()[0] != 1:
            return False
        owner, credential = owners[0]
        return db.execute('SELECT enabled FROM visitor_photo_preferences WHERE owner_id=? AND credential_digest=?',
                          (owner, credential_digest(credential))).fetchone() == (1,)


def recognition_people(db_path=None):
    target = Path(db_path) if db_path is not None else store.get_data_dir()/'lya.db.enc'
    if not target.is_file():
        return []
    with store.store_connection(target,read_only=True) as db:
        owners = db.execute("SELECT p.person_id,k.credential FROM people p JOIN owner_passkeys k USING(person_id) WHERE p.role='admin' AND p.active=1 LIMIT 2").fetchall()
        if len(owners) != 1 or db.execute("SELECT COUNT(*) FROM people WHERE role='admin' AND active=1").fetchone()[0] != 1:
            return []
        owner, credential = owners[0]
        digest = credential_digest(credential)
        if db.execute('SELECT enabled FROM recognition_preferences WHERE owner_id=? AND credential_digest=?',
                      (owner,digest)).fetchone() != (1,):
            return []
        rows = db.execute('''SELECT p.person_id,p.display_name,p.role,t.embedding_enc,
                pref.nickname_enc,pref.greeting_enc,pref.style_enc
            FROM people p JOIN face_templates t USING(person_id)
            LEFT JOIN person_preferences pref USING(person_id)
            WHERE p.active=1 AND t.model_version=? AND (p.person_id=? OR
                (p.role IN ('friend','family') AND EXISTS(SELECT 1 FROM visitor_grants g WHERE
                 g.person_id=p.person_id AND g.owner_id=? AND g.credential_digest=?)))
            ORDER BY p.person_id,t.id LIMIT 100''',(FACE_MODEL,owner,owner,digest)).fetchall()
        people = {}
        for pid,name,role,token,nickname_enc,greeting_enc,style_enc in rows:
            person = people.setdefault(pid,dict(person_id=pid,display_name=name,role=role,samples=[]))
            if nickname_enc is not None:
                person['nickname'] = vault.decrypt_text(nickname_enc)[:80]
            if greeting_enc is not None:
                person['greeting'] = vault.decrypt_text(greeting_enc)[:240]
            if style_enc is not None:
                person['style'] = vault.decrypt_text(style_enc)[:16]
            person['samples'].append(checked_vector(json.loads(vault.decrypt_text(token)),FACE_MODEL))
        if owner not in people or len(people[owner]['samples']) != 3:
            return []
        return [p for p in people.values() if (p['role']=='admin' and len(p['samples'])==3)
                or (p['role'] in VISITOR_ROLES and len(p['samples'])==1)]


def _clean_text(value, label, limit):
    if type(value) is not str or not 1 <= len(value.strip()) <= limit or any(ord(c)<32 for c in value):
        raise ValueError(f'Use a printable {label} of 1 to {limit} characters.')
    return value.strip()


def _role(category):
    if category not in VISITOR_ROLES:
        raise ValueError('Visitor category must be friend or family.')
    return category


def register(session,name,vector,db_path=None,*,category='friend'):
    if type(name) is not str or not 1 <= len(name.strip()) <= 80 or any(ord(c)<32 for c in name):
        raise ValueError('Use a printable person name of 1 to 80 characters.')
    category = _role(category)
    vector = checked_vector(vector,FACE_MODEL)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with store.store_connection(db_path) as db:
        credential = owner_check(db,session)
        if db.execute('SELECT COUNT(*) FROM visitor_grants').fetchone()[0] >= 24:
            raise ValueError('Visitor registry is full (24 people).')
        if db.execute('SELECT 1 FROM people WHERE active=1 AND lower(display_name)=lower(?)',(name.strip(),)).fetchone():
            raise ValueError('That name already belongs to an active person.')
        pid = 'p_'+secrets.token_urlsafe(12)
        db.execute("INSERT INTO people VALUES(?,?,?,?,1)",(pid,name.strip(),category,now))
        db.execute('INSERT INTO face_templates(person_id,embedding_enc,model_version,quality,created_at) VALUES(?,?,?,?,?)',
                   (pid,vault.encrypt_text(json.dumps(vector)),FACE_MODEL,1.,now))
        db.execute('INSERT INTO visitor_grants VALUES(?,?,?)',(pid,session.person_id,credential_digest(credential)))
        db.execute('INSERT OR REPLACE INTO person_preferences(person_id,nickname_enc,greeting_enc,style_enc,updated_at) VALUES(?,?,?,?,?)',
                   (pid,None,None,vault.encrypt_text('casual'),now))
        db.execute('INSERT INTO audit_events(time,action_type,outcome,person_id) VALUES(?,?,?,?)',
                    (now,'visitor_registered',category+'_limited_apps_only',session.person_id))
        return pid


def record_unknown(vector, photo=None, db_path=None):
    """Persist an unknown only when the owner explicitly enabled photo review."""
    if photo is None or not photo_enabled(db_path):
        return None
    vector = checked_vector(vector, FACE_MODEL)
    return store.record_pending_face(embedding=vector, photo_bytes=photo,
                                     expires_days=PHOTO_RETENTION_DAYS, db_path=db_path)


def pending(db_path=None):
    return store.list_pending_faces(db_path)


def pending_photo(pending_id, db_path=None):
    return store.pending_face_photo(pending_id, db_path)


def discard_pending(session, pending_id, db_path=None):
    with store.store_connection(db_path) as db:
        owner_check(db, session)
    return store.delete_pending_face(pending_id, db_path)


def register_pending(session, pending_id, name, db_path=None, *, category='friend'):
    """Owner-reviewed promotion of an encrypted unknown observation."""
    name = _clean_text(name, 'person name', 80)
    category = _role(category)
    with store.store_connection(db_path) as db:
        credential = owner_check(db, session)
        row = db.execute('''SELECT pending_id,embedding_enc,thumbnail_path FROM pending_faces
            WHERE pending_id=? AND expires_at>?''',
                         (pending_id, datetime.datetime.now().isoformat())).fetchone()
        if not row or not row[1]:
            raise ValueError('That visitor photo is missing or expired.')
        if db.execute('SELECT 1 FROM people WHERE active=1 AND lower(display_name)=lower(?)', (name,)).fetchone():
            raise ValueError('That name already belongs to an active person.')
        vector = checked_vector(json.loads(vault.decrypt_text(row[1])), FACE_MODEL)
        if db.execute('SELECT COUNT(*) FROM visitor_grants').fetchone()[0] >= 24:
            raise ValueError('Visitor registry is full (24 people).')
        pid = 'p_'+secrets.token_urlsafe(12)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        db.execute('INSERT INTO people VALUES(?,?,?,?,1)', (pid,name,category,now))
        db.execute('INSERT INTO face_templates(person_id,embedding_enc,model_version,quality,created_at) VALUES(?,?,?,?,?)',
                   (pid,vault.encrypt_text(json.dumps(vector)),FACE_MODEL,1.,now))
        db.execute('INSERT INTO visitor_grants VALUES(?,?,?)',
                   (pid,session.person_id,credential_digest(credential)))
        db.execute('INSERT OR REPLACE INTO person_preferences(person_id,nickname_enc,greeting_enc,style_enc,updated_at) VALUES(?,?,?,?,?)',
                   (pid,None,None,vault.encrypt_text('casual'),now))
        db.execute('DELETE FROM pending_faces WHERE pending_id=?', (pending_id,))
        db.execute('INSERT INTO audit_events(time,action_type,outcome,person_id) VALUES(?,?,?,?)',
                   (now,'visitor_registered',category+'_from_pending_photo',session.person_id))
        photo_path = row[2]
    store._delete_pending_photo(photo_path, db_path)
    return pid


def set_personalization(session, target, db_path=None, *, nickname=None, greeting=None, style=None):
    """Set owner-approved, non-authorizing presentation preferences."""
    if nickname is not None:
        nickname = _clean_text(nickname, 'nickname', 80)
    if greeting is not None:
        greeting = _clean_text(greeting, 'greeting', 240)
    if style is not None:
        style = _clean_text(style.casefold(), 'style', 16)
        if style not in VISITOR_STYLES:
            raise ValueError('Style must be warm, brief, formal or casual.')
    with store.store_connection(db_path) as db:
        credential = owner_check(db, session)
        digest = credential_digest(credential)
        if target in (None, '', 'me', 'myself'):
            person_id = session.person_id
        else:
            row = db.execute('''SELECT p.person_id FROM people p
                LEFT JOIN visitor_grants g ON g.person_id=p.person_id
                WHERE p.active=1 AND lower(p.display_name)=lower(?) AND
                (p.person_id=? OR (g.owner_id=? AND g.credential_digest=?))
                LIMIT 2''', (target.strip(),session.person_id,session.person_id,digest)).fetchall()
            if len(row) != 1:
                raise ValueError('Choose one registered friend or family member.')
            person_id = row[0][0]
        current = db.execute('SELECT nickname_enc,greeting_enc,style_enc FROM person_preferences WHERE person_id=?',
                             (person_id,)).fetchone()
        values = (
            vault.encrypt_text(nickname) if nickname is not None else (current[0] if current else None),
            vault.encrypt_text(greeting) if greeting is not None else (current[1] if current else None),
            vault.encrypt_text(style) if style is not None else (current[2] if current else vault.encrypt_text('casual')),
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            person_id,
        )
        db.execute('''INSERT OR REPLACE INTO person_preferences
            (person_id,nickname_enc,greeting_enc,style_enc,updated_at) VALUES(?,?,?,?,?)''',
                   (person_id,values[0],values[1],values[2],values[3]))
    return person_id


def personalization(person_id, db_path=None):
    if not person_id:
        return {}
    with store.store_connection(db_path, read_only=True) as db:
        row = db.execute('SELECT nickname_enc,greeting_enc,style_enc FROM person_preferences WHERE person_id=?',
                         (person_id,)).fetchone()
    if not row:
        return {}
    result = {}
    for key, token in zip(('nickname','greeting','style'),row):
        if token is not None:
            try:
                result[key] = vault.decrypt_text(token)
            except Exception:
                pass
    return result


def list_registered(session, db_path=None):
    """Return owner-approved friend/family labels without embeddings."""
    with store.store_connection(db_path, read_only=True) as db:
        credential = owner_check(db, session)
        rows = db.execute('''SELECT p.person_id,p.display_name,p.role
            FROM people p JOIN visitor_grants g USING(person_id)
            WHERE p.active=1 AND p.role IN ('friend','family')
              AND g.owner_id=? AND g.credential_digest=? ORDER BY lower(p.display_name)''',
                           (session.person_id,credential_digest(credential))).fetchall()
    return [dict(person_id=pid,display_name=name,role=role) for pid,name,role in rows]


def remove(session,name,db_path=None):
    with store.store_connection(db_path) as db:
        credential = owner_check(db,session)
        rows = db.execute('''SELECT p.person_id FROM people p JOIN visitor_grants g USING(person_id)
            WHERE p.active=1 AND p.role IN ('friend','family') AND g.owner_id=? AND g.credential_digest=?
            AND lower(p.display_name)=lower(?) LIMIT 2''',(session.person_id,credential_digest(credential),name)).fetchall()
        if len(rows) != 1:
            raise ValueError('Choose one uniquely registered visitor. Owner registration cannot be removed here.')
        db.execute('UPDATE people SET active=0 WHERE person_id=?',rows[0])
        db.execute('DELETE FROM face_templates WHERE person_id=?',rows[0])
        db.execute('DELETE FROM visitor_grants WHERE person_id=?',rows[0])
        db.execute('DELETE FROM person_preferences WHERE person_id=?',rows[0])


def save_summary(session,counts,db_path=None):
    if (type(counts) is not dict or set(counts) != {'requests','limited_apps','blocked'}
            or any(type(v) is not int or not 0 <= v <= 1000 for v in counts.values())):
        raise ValueError('Only bounded activity counts may be saved.')
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with store.store_connection(db_path) as db:
        owner_check(db,session)
        db.execute('''INSERT INTO memories(person_id,kind,key_enc,value_enc,source,importance,hits,created_at,updated_at)
            VALUES(?,'private',?,?,'owner_review',1.,0,?,?)''',
            (session.person_id,vault.encrypt_text('Visitor summary '+now),vault.encrypt_text(json.dumps(counts)),now,now))
