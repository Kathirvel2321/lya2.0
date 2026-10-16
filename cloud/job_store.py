"""Durable control metadata only. No messages, report bodies, credentials or arbitrary commands."""
from contextlib import closing, contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3

from cloud.job_policy import Job, OPAQUE, from_dict, due_slot


class JobStore:
    def __init__(self,path,verify_owner=None):
        self.path=Path(path);self.verify_owner=verify_owner

    @contextmanager
    def db(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.is_symlink() or self.path.parent.is_symlink():raise ValueError('Job control store cannot be a link.')
        with closing(sqlite3.connect(self.path,timeout=1)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA max_page_count=512');db.execute('BEGIN IMMEDIATE')
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1):raise ValueError('Unsupported job-control schema.')
            if version==0:
                if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():raise ValueError('Unrelated database at job-control path.')
                db.execute('CREATE TABLE jobs(id TEXT PRIMARY KEY,spec TEXT,digest TEXT,epoch INTEGER,enabled INTEGER,expires REAL)')
                db.execute('CREATE TABLE contracts(digest TEXT PRIMARY KEY,spec TEXT NOT NULL,owner TEXT NOT NULL)')
                db.execute('CREATE TABLE runs(id TEXT PRIMARY KEY,job TEXT,digest TEXT,epoch INTEGER,scheduled REAL,notify REAL,state TEXT,reason TEXT,report TEXT,expires REAL,important INTEGER,uncertain INTEGER,started REAL,finished REAL,usage TEXT)')
                db.execute('CREATE TABLE actions(id TEXT PRIMARY KEY,run TEXT,payload TEXT,state TEXT,receipt TEXT)')
                db.execute('CREATE TABLE outbox(run TEXT PRIMARY KEY,due REAL,state TEXT,receipt TEXT)')
                db.execute('PRAGMA user_version=1')
            try:yield db;db.commit()
            except BaseException:db.rollback();raise
        self.path.chmod(0o600)

    def authorize(self,operation,job,proof):
        if self.verify_owner is None or self.verify_owner(operation,job,proof) is not True:
            raise PermissionError('Verified owner authority is required for this exact contract.')

    def enable(self,job,proof,now,expires):
        job.validate();self.authorize('enable',job,proof)
        if not now<expires<=now+30*86400:raise ValueError('Delegation must expire within 30 days.')
        with self.db() as db:
            previous=db.execute('SELECT spec,epoch FROM jobs WHERE id=?',(job.id,)).fetchone()
            if previous and from_dict(json.loads(previous['spec'])).owner != job.owner:
                raise PermissionError('A job identity cannot change owners.')
            if previous and from_dict(json.loads(previous['spec'])).revision>=job.revision:
                raise ValueError('Reapproval requires a new revision; old slots must not be replayed.')
            if db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]>=64 and not previous:raise ValueError('Job count limit reached.')
            if db.execute('SELECT COUNT(*) FROM contracts').fetchone()[0]>=512:raise ValueError('Contract audit history requires maintenance.')
            db.execute('INSERT OR IGNORE INTO contracts VALUES(?,?,?)',(job.digest(),job.canonical(),job.owner))
            epoch=previous['epoch']+1 if previous else 1
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,1,?) ON CONFLICT(id) DO UPDATE SET spec=excluded.spec,digest=excluded.digest,epoch=excluded.epoch,enabled=1,expires=excluded.expires',
                       (job.id,job.canonical(),job.digest(),epoch,expires))

    def revoke(self,job,proof):
        self.authorize('revoke',job,proof)
        with self.db() as db:
            row=db.execute('SELECT digest FROM jobs WHERE id=?',(job.id,)).fetchone()
            if not row or row['digest']!=job.digest():raise PermissionError('Revocation contract mismatch.')
            db.execute('UPDATE jobs SET enabled=0,epoch=epoch+1 WHERE id=?',(job.id,))

    @staticmethod
    def active_db(db,job,digest,epoch,now):
        return db.execute('SELECT 1 FROM jobs WHERE id=? AND digest=? AND epoch=? AND enabled=1 AND expires>?',
                          (job,digest,epoch,now)).fetchone() is not None

    def active(self,job,digest,epoch,now):
        with self.db() as db:return self.active_db(db,job,digest,epoch,now)

    def claim(self,job,slot,now):
        expected=due_slot(job,now)
        if expected is None or any(expected[key]!=slot.get(key) for key in ('id','scheduled','notify')):
            raise ValueError('Run slot does not match the approved schedule.')
        with self.db() as db:
            grant=db.execute('SELECT * FROM jobs WHERE id=?',(job.id,)).fetchone()
            if not grant or grant['digest']!=job.digest() or not grant['enabled'] or grant['expires']<=now:
                raise PermissionError('No active approval for the exact task contract.')
            if db.execute('SELECT 1 FROM runs WHERE id=?',(slot['id'],)).fetchone():return None
            if db.execute("SELECT 1 FROM runs WHERE job=? AND state IN ('running','needs_review')",(job.id,)).fetchone():
                raise PermissionError('A previous run is active or requires recovery review.')
            if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]>=512:raise ValueError('Run history full; explicit retention maintenance required.')
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,NULL,NULL,NULL,0,0,?,NULL,NULL)',
                (slot['id'],job.id,job.digest(),grant['epoch'],slot['scheduled'],slot['notify'],'running',now))
            return grant['epoch']

    def end(self,run,state,reason='',report=None,expires=None,important=0,uncertain=0,notify=False,now=None,usage=None):
        if state not in ('completed','partial','blocked','cancelled','limit_reached','needs_review','failed'):raise ValueError('Invalid terminal run state.')
        with self.db() as db:
            row=db.execute('SELECT * FROM runs WHERE id=?',(run,)).fetchone()
            if state in ('completed','partial') and (now is None or not row or not self.active_db(db,row['job'],row['digest'],row['epoch'],now)):
                state,reason,report,notify='cancelled','delegation_changed',None,False
            changed=db.execute("UPDATE runs SET state=?,reason=?,report=?,expires=?,important=?,uncertain=?,finished=?,usage=? WHERE id=? AND state='running'",
                (state,reason,report,expires,important,uncertain,now,json.dumps(usage or {},sort_keys=True),run)).rowcount
            if changed and state in ('completed','partial') and notify:
                db.execute("INSERT OR IGNORE INTO outbox SELECT id,notify,'pending',NULL FROM runs WHERE id=?",(run,))

    def prepare_action(self,run,job,epoch,key,payload,now):
        with self.db() as db:
            if not self.active_db(db,job.id,job.digest(),epoch,now):raise PermissionError('Task delegation changed before send.')
            if not db.execute("SELECT 1 FROM runs WHERE id=? AND state='running'",(run,)).fetchone():raise PermissionError('Run is no longer active.')
            row=db.execute('SELECT * FROM actions WHERE id=?',(key,)).fetchone()
            if row:
                if row['payload']==payload and row['state']=='sent':return False
                raise RuntimeError('Prior outgoing action is uncertain or conflicts; reconciliation is required.')
            if db.execute('SELECT COUNT(*) FROM actions').fetchone()[0]>=1024:raise ValueError('Outgoing action ledger full.')
            db.execute("INSERT INTO actions VALUES(?,?,?,'pending',NULL)",(key,run,payload))
            return True

    def action_receipt(self,key,receipt):
        if not OPAQUE.fullmatch(receipt):raise ValueError('An opaque trusted provider-receipt reference is required.')
        with self.db() as db:db.execute("UPDATE actions SET state='sent',receipt=? WHERE id=? AND state='pending'",(receipt,key))

    def view(self,run):
        with self.db() as db:
            row=db.execute('SELECT * FROM runs WHERE id=?',(run,)).fetchone()
            if row is None:return None
            result=dict(row)
            result['usage']=json.loads(result['usage']) if result['usage'] else {}
            result['actions']={value['state']:value['count'] for value in db.execute('SELECT state,COUNT(*) count FROM actions WHERE run=? GROUP BY state',(run,))}
            delivery=db.execute('SELECT state FROM outbox WHERE run=?',(run,)).fetchone()
            result['delivery']=delivery['state'] if delivery else None
            return result

    def notification_claim(self,run,now,job):
        with self.db() as db:
            row=db.execute('SELECT r.*,o.state delivery,o.due FROM runs r JOIN outbox o ON o.run=r.id WHERE r.id=?',(run,)).fetchone()
            if row and row['digest']!=job.digest():raise PermissionError('Notification contract mismatch.')
            if not row or row['delivery']!='pending' or row['due']>now:return None
            if row['expires']<=now:
                db.execute("UPDATE outbox SET state='expired' WHERE run=?",(run,));return None
            if not self.active_db(db,row['job'],row['digest'],row['epoch'],now):return None
            db.execute("UPDATE outbox SET state='requesting' WHERE run=?",(run,))
            return dict(row)

    def notification_receipt(self,run,receipt):
        if not OPAQUE.fullmatch(receipt):raise ValueError('Invalid notification request receipt reference.')
        with self.db() as db:db.execute("UPDATE outbox SET state='requested',receipt=? WHERE run=? AND state='requesting'",(receipt,run))

    def inbox_decision(self,job,run,decision,proof,now,until=None):
        self.authorize('inbox_'+decision,job,proof)
        if decision not in ('keep','dismiss','later'):raise ValueError('Unsupported inbox decision.')
        if decision=='later' and (type(until) not in (int,float) or not now<until<=now+7*86400):raise ValueError('Choose an explicit reminder time within seven days.')
        with self.db() as db:
            row=db.execute('SELECT * FROM runs WHERE id=? AND job=?',(run,job.id)).fetchone()
            if not row or row['state'] not in ('completed','partial') or row['digest']!=job.digest():raise ValueError('No completed result for this job.')
            if decision=='later' and until>=row['expires']:raise ValueError('Reminder would outlive report retention.')
            if decision=='later':
                db.execute("INSERT INTO outbox VALUES(?,?,'pending',NULL) ON CONFLICT(run) DO UPDATE SET due=excluded.due,state='pending',receipt=NULL",(run,until))
            else:
                db.execute("INSERT INTO outbox VALUES(?, ?, ?, NULL) ON CONFLICT(run) DO UPDATE SET state=excluded.state",(run,now,'kept' if decision=='keep' else 'dismissed'))

    def recover(self,job,run,proof):
        self.authorize('recover',job,proof)
        with self.db() as db:
            grant=db.execute('SELECT digest FROM jobs WHERE id=?',(job.id,)).fetchone()
            record=db.execute('SELECT job,digest FROM runs WHERE id=?',(run,)).fetchone()
            if not grant or grant['digest']!=job.digest() or not record or record['digest']!=job.digest() or record['job']!=job.id:
                raise PermissionError('Recovery contract mismatch.')
            db.execute('UPDATE jobs SET enabled=0,epoch=epoch+1 WHERE id=?',(job.id,))
            db.execute("UPDATE runs SET state='needs_review',reason='operator_recovery' WHERE id=? AND job=? AND state='running'",(run,job.id))
