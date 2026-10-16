"""Public announcement cache and hourly monitor; never private assistant memory."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time

from cloud.news_sources import SOURCES, OfficialNewsFetcher, timestamp

INTERVAL = 3600
LOOKBACK = 7 * 86400
MAX_STORED = 256


def data_path():
    if os.environ.get('LYA_DATA_DIR'):
        base = Path(os.environ['LYA_DATA_DIR'])
    elif os.environ.get('LOCALAPPDATA'):
        base = Path(os.environ['LOCALAPPDATA']) / 'LYA'
    else:
        base = Path.home() / '.local' / 'share' / 'LYA'
    return base / 'technology-news.sqlite'


def relevance(item):
    text = item['title'] + ' ' + item['preview']
    if not re.search(r'introduc|launch|releas|upgrad|updat|available|preview|\bnew\b|\bmeet\b|gpt[- ]?\d|gemini \d|claude.*\d', item['title'], re.I):
        return []
    topics = []
    if re.search(r'\b(coding|code|developer|agent|agents|programming|antigravity|jules)\b', text, re.I):
        topics.append('coding and assistant tools')
    if re.search(r'\b(image|images|video|videos|audio|voice|speech|design|creative)\b', text, re.I):
        topics.append('creative and voice tools')
    if re.search(r'\b(model|models|gpt|claude|gemini|reasoning|llm|AI)\b', text, re.I):
        topics.append('AI models and research')
    return topics


class NewsStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def db(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError('News cache cannot be a symbolic link.')
        with closing(sqlite3.connect(self.path, timeout=1)) as db:
            db.execute('PRAGMA max_page_count=256')
            db.execute('BEGIN IMMEDIATE')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('News cache schema is unsupported.')
            if version == 0:
                if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise ValueError('News cache location contains an unrelated database.')
                db.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                db.execute('CREATE TABLE items(id TEXT PRIMARY KEY,data TEXT NOT NULL,published REAL NOT NULL,observed REAL NOT NULL,read_at REAL,notified_at REAL)')
                db.execute('PRAGMA user_version=1')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback(); raise
        if os.name != 'nt': self.path.chmod(0o600)

    @staticmethod
    def get(db, key, default=None):
        row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    @staticmethod
    def put(db, key, value):
        db.execute('INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   (key, json.dumps(value, separators=(',', ':'))))

    def enabled(self):
        with self.db() as db: return self.get(db, 'enabled', True) is True

    def set_enabled(self, value):
        if type(value) is not bool: raise ValueError('Invalid news preference.')
        with self.db() as db: self.put(db, 'enabled', value)

    def reserve(self, now):
        with self.db() as db:
            if self.get(db, 'enabled', True) is not True: return False
            previous = self.get(db, 'last_attempt')
            if previous is not None and now - previous < INTERVAL: return False
            self.put(db, 'last_attempt', now)
            return True

    def finish(self, items, coverage, now, check=lambda: None):
        with self.db() as db:
            check()
            if self.get(db, 'enabled', True) is not True:
                raise InterruptedError('News monitoring paused.')
            for item in items:
                published = datetime.fromisoformat(item['published_at'].replace('Z', '+00:00')).timestamp()
                db.execute('INSERT INTO items VALUES(?,?,?,?,NULL,NULL) ON CONFLICT(id) DO UPDATE SET data=excluded.data,published=excluded.published',
                           (item['id'], json.dumps(item, ensure_ascii=False), published, now))
            db.execute('DELETE FROM items WHERE published < ?', (now - 30*86400,))
            db.execute('DELETE FROM items WHERE id NOT IN (SELECT id FROM items ORDER BY observed DESC,published DESC LIMIT ?)', (MAX_STORED,))
            self.put(db, 'coverage', coverage)
            self.put(db, 'last_completed', now)
            check()

    def snapshot(self, now, limit=12):
        if type(limit) is not int or not 1 <= limit <= 12: raise ValueError('Invalid brief limit.')
        with self.db() as db:
            rows = db.execute('SELECT data,read_at,notified_at FROM items WHERE published BETWEEN ? AND ? ORDER BY read_at IS NOT NULL,published DESC LIMIT ?',
                              (now - LOOKBACK, now + 300, limit)).fetchall()
            unread = db.execute('SELECT COUNT(*) FROM items WHERE read_at IS NULL AND published BETWEEN ? AND ?', (now-LOOKBACK, now+300)).fetchone()[0]
            return {'items': [dict(json.loads(row[0]), unread=row[1] is None,
                                  notification_requested=row[2] is not None) for row in rows],
                    'unread': unread, 'coverage': self.get(db, 'coverage', []),
                    'last_attempt': self.get(db, 'last_attempt'),
                    'last_completed': self.get(db, 'last_completed'),
                    'enabled': self.get(db, 'enabled', True) is True}

    def mark(self, ids, now, *, notified=False):
        if not isinstance(ids, list) or len(ids) > 12 or any(not re.fullmatch('[a-f0-9]{64}', value) for value in ids):
            raise ValueError('Invalid announcement IDs.')
        column = 'notified_at' if notified else 'read_at'
        with self.db() as db:
            for key in ids:
                db.execute(f'UPDATE items SET {column}=COALESCE({column},?) WHERE id=?', (now, key))


class NewsMonitor:
    def __init__(self, store, *, sources=SOURCES, fetch=None, clock=time.time, monotonic=time.monotonic):
        self.store, self.sources = store, tuple(sources)
        self.fetch = fetch or OfficialNewsFetcher()
        self.clock, self.monotonic = clock, monotonic
        self.lock = threading.Lock()

    def check(self, cancelled=None):
        def check():
            if cancelled is not None and cancelled.is_set(): raise InterruptedError('News check cancelled.')
        check()
        if not self.lock.acquire(blocking=False): return False
        try:
            now = self.clock()
            if not self.store.reserve(now): return False
            deadline = self.monotonic() + 20
            requests = 0
            items, coverage = [], []
            def reserve():
                nonlocal requests
                check()
                if requests >= 6: raise ValueError('News HTTP budget reached.')
                requests += 1
            for source in self.sources[:3]:
                check()
                if self.monotonic() >= deadline:
                    coverage.append({'source': source.label, 'status': 'time budget reached'}); continue
                try:
                    values, rejected = self.fetch(source, deadline=deadline, check=check, reserve=reserve)
                    check()
                    admitted = []
                    for item in values[:60]:
                        stamp = datetime.fromisoformat(timestamp(item['published_at']).replace('Z', '+00:00')).timestamp()
                        if not now - LOOKBACK <= stamp <= now + 300: continue
                        topics = relevance(item)
                        if topics:
                            admitted.append(dict(item, topics=topics, observed_at=now))
                    items.extend(admitted)
                    coverage.append({'source': source.label, 'status': 'read',
                                     'matching': len(admitted), 'undated_or_invalid': rejected})
                except InterruptedError: raise
                except (ValueError, OSError, ETError, UnicodeError, TypeError, KeyError):
                    coverage.append({'source': source.label, 'status': 'unavailable or format changed'})
            check()
            self.store.finish(items, coverage, self.clock(), check)
            return True
        finally:
            self.lock.release()


# XML parse errors are intentionally public-source failures, not fallback claims.
from xml.etree.ElementTree import ParseError as ETError


def render_brief(snapshot):
    lines = ['Recent AI and technology announcements',
             'Selected official sources; this is not a complete view of the internet.']
    if not snapshot['enabled']: lines.append('Background checks are paused; these are cached items.')
    if snapshot['last_completed'] is not None:
        lines.append('Last completed check: ' + datetime.fromtimestamp(snapshot['last_completed'], timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
    else:
        lines.append('No source check has completed yet.')
    for row in snapshot['coverage']:
        lines.append(row['source'] + ': ' + row['status'] +
                     (f"; {row.get('undated_or_invalid',0)} undated/invalid item(s) skipped" if row.get('undated_or_invalid') else ''))
    if not snapshot['items']:
        lines += ['', 'No matching recent announcements are in the local cache. This does not establish that nothing new was released.']
    for item in snapshot['items']:
        date = item['published_at'][:10] + ' (publisher date; time unspecified)' if item['precision'] == 'day' else item['published_at']
        lines += ['', item['title'], 'Announced: ' + date,
                  'Publisher: ' + item['publisher']]
        if item['preview']:
            lines.append('Publisher preview (may be shortened): ' + item['preview'])
        lines += ['Possible relevance: ' + ', '.join(item['topics']) + '.',
                  'Access, pricing and performance have not been independently checked.',
                  'Official announcement: ' + item['url']]
    lines += ['', 'These are publisher announcements, not independent model evaluations. Open the source or ask LYA to research a specific launch before choosing a tool.']
    return '\n'.join(lines)
