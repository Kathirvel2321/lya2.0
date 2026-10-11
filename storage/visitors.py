"""Native owner-controlled registry. Stored only in the existing encrypted database."""
import datetime
import hashlib
import json
from pathlib import Path
import secrets

from security import vault
from security.owner_profiles import FACE_MODEL, checked_vector
from storage import store


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
        rows = db.execute('''SELECT p.person_id,p.display_name,p.role,t.embedding_enc
            FROM people p JOIN face_templates t USING(person_id)
            WHERE p.active=1 AND t.model_version=? AND (p.person_id=? OR
                (p.role='friend' AND EXISTS(SELECT 1 FROM visitor_grants g WHERE
                 g.person_id=p.person_id AND g.owner_id=? AND g.credential_digest=?)))
            ORDER BY p.person_id,t.id LIMIT 100''',(FACE_MODEL,owner,owner,digest)).fetchall()
        people = {}
        for pid,name,role,token in rows:
            person = people.setdefault(pid,dict(person_id=pid,display_name=name,role=role,samples=[]))
            person['samples'].append(checked_vector(json.loads(vault.decrypt_text(token)),FACE_MODEL))
        if owner not in people or len(people[owner]['samples']) != 3:
            return []
        return [p for p in people.values() if (p['role']=='admin' and len(p['samples'])==3)
                or (p['role']=='friend' and len(p['samples'])==1)]


def register(session,name,vector,db_path=None):
    if type(name) is not str or not 1 <= len(name.strip()) <= 80 or any(ord(c)<32 for c in name):
        raise ValueError('Use a printable person name of 1 to 80 characters.')
    vector = checked_vector(vector,FACE_MODEL)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with store.store_connection(db_path) as db:
        credential = owner_check(db,session)
        if db.execute('SELECT COUNT(*) FROM visitor_grants').fetchone()[0] >= 24:
            raise ValueError('Visitor registry is full (24 people).')
        if db.execute('SELECT 1 FROM people WHERE active=1 AND lower(display_name)=lower(?)',(name.strip(),)).fetchone():
            raise ValueError('That name already belongs to an active person.')
        pid = 'p_'+secrets.token_urlsafe(12)
        db.execute("INSERT INTO people VALUES(?,?,'friend',?,1)",(pid,name.strip(),now))
        db.execute('INSERT INTO face_templates(person_id,embedding_enc,model_version,quality,created_at) VALUES(?,?,?,?,?)',
                   (pid,vault.encrypt_text(json.dumps(vector)),FACE_MODEL,1.,now))
        db.execute('INSERT INTO visitor_grants VALUES(?,?,?)',(pid,session.person_id,credential_digest(credential)))
        db.execute('INSERT INTO audit_events(time,action_type,outcome,person_id) VALUES(?,?,?,?)',
                   (now,'visitor_registered','limited_apps_only',session.person_id))
        return pid


def remove(session,name,db_path=None):
    with store.store_connection(db_path) as db:
        credential = owner_check(db,session)
        rows = db.execute('''SELECT p.person_id FROM people p JOIN visitor_grants g USING(person_id)
            WHERE p.active=1 AND p.role='friend' AND g.owner_id=? AND g.credential_digest=?
            AND lower(p.display_name)=lower(?) LIMIT 2''',(session.person_id,credential_digest(credential),name)).fetchall()
        if len(rows) != 1:
            raise ValueError('Choose one uniquely registered visitor. Owner registration cannot be removed here.')
        db.execute('UPDATE people SET active=0 WHERE person_id=?',rows[0])
        db.execute('DELETE FROM face_templates WHERE person_id=?',rows[0])
        db.execute('DELETE FROM visitor_grants WHERE person_id=?',rows[0])


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
