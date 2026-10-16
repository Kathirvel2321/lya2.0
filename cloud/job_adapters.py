"""First public adapter and public report sink. No real messaging connector is installed."""
from contextlib import closing, contextmanager
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from xml.etree.ElementTree import ParseError

from cloud.job_runner import Result, LimitReached
from cloud.job_policy import OPAQUE
from cloud.news_sources import SOURCES, OfficialNewsFetcher
from cloud.tech_news import relevance, LOOKBACK


class PublicReports:
    """Public output only; private reports require a separately qualified protected sink."""
    def __init__(self,path):self.path=Path(path)
    def supports(self,job):return job.sensitivity=='public'
    @contextmanager
    def db(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.is_symlink() or self.path.parent.is_symlink():raise ValueError('Report store cannot be a link.')
        with closing(sqlite3.connect(self.path,timeout=1)) as db,db:
            db.execute('PRAGMA max_page_count=512')
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version==0:
                if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():raise ValueError('Unrelated database at report-store path.')
                db.execute('CREATE TABLE reports(id TEXT PRIMARY KEY,body BLOB,expires REAL)')
                db.execute('PRAGMA user_version=731091')
            elif version!=731091:raise ValueError('Unsupported public-report schema.')
            yield db
        self.path.chmod(0o600)

    def write(self,job,run,body,expires):
        if not self.supports(job):raise PermissionError('Private output cannot enter a public report store.')
        if type(body) is not bytes or len(body)>job.limits.result_bytes:raise ValueError('Report byte limit exceeded.')
        reference=hashlib.sha256(run.encode()+body).hexdigest()
        with self.db() as db:
            db.execute('DELETE FROM reports WHERE expires<=?',(expires-job.retention_hours*3600,))
            if db.execute('SELECT COUNT(*) FROM reports').fetchone()[0]>=256:raise ValueError('Public report retention maintenance required.')
            db.execute('INSERT OR IGNORE INTO reports VALUES(?,?,?)',(reference,body,expires))
        return reference

    def read(self,reference,now):
        if not OPAQUE.fullmatch(reference):raise ValueError('Invalid report reference.')
        with self.db() as db:
            row=db.execute('SELECT body FROM reports WHERE id=? AND expires>?',(reference,now)).fetchone()
            if row is None:raise LookupError('Report is missing or expired.')
            return bytes(row[0])

    def purge(self,now):
        with self.db() as db:return db.execute('DELETE FROM reports WHERE expires<=?',(now,)).rowcount


class TechnologyUpdates:
    zero_spend=True
    def __init__(self,fetch=None):self.fetch=fetch or OfficialNewsFetcher()
    def preflight(self,job):return job.kind=='technology_updates' and job.sensitivity=='public'
    def collect(self,job,context):
        items,coverage=[],[];partial=False
        for source in SOURCES:
            context.check()
            try:
                rows,rejected=self.fetch(source,deadline=context.deadline,check=context.check,reserve=context.request)
                for row in rows:
                    stamp=datetime.fromisoformat(row['published_at'].replace('Z','+00:00')).timestamp()
                    if context.window_start<=stamp<=context.window_end and relevance(row):
                        context.item();items.append(row)
                coverage.append({'source':source.key,'status':'read','invalid_items':rejected})
            except (InterruptedError,PermissionError,LimitReached):raise
            except (ValueError,OSError,ParseError):partial=True;coverage.append({'source':source.key,'status':'unavailable'})
        body=json.dumps({'announcements':items,'coverage':coverage,
            'qualification':'Publisher announcements; usefulness, performance and access are not independently verified.'},ensure_ascii=False).encode()
        return Result(body,uncertain=len(items),partial=partial)
