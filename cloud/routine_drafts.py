"""Bounded routine proposals. Saving a draft never grants execution authority."""
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

from cloud.job_policy import Job, Limits, OPAQUE

PROVIDERS = {
    'official_news': 'Official technology announcements',
    'whatsapp_unspecified': 'WhatsApp — account type undecided',
    'whatsapp_personal': 'WhatsApp — personal account requested',
    'whatsapp_business': 'WhatsApp — Business account requested',
    'youtube_comments': 'YouTube — channel comments requested',
}
SCHEMA = 731092
MAX_DRAFTS = 32


@dataclass(frozen=True)
class Settings:
    provider: str = 'official_news'
    start: str = '13:00'
    notify: str = '13:05'
    zone: str = 'Asia/Kolkata'
    placement: str = 'oracle'
    lookback_hours: int = 168
    catchup_minutes: int = 30
    retention_hours: int = 24
    notification_filter: str = 'important_or_uncertain'

    def validate(self):
        if self.provider not in PROVIDERS or self.placement not in ('desktop', 'oracle'):
            raise ValueError('Choose a supported proposal type and placement.')
        for value in (self.start, self.notify):
            if type(value) is not str or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
                raise ValueError('Choose explicit 24-hour times.')
        if type(self.zone) is not str or len(self.zone) > 64 or not re.fullmatch(r'[A-Za-z0-9_+/-]+', self.zone):
            raise ValueError('Choose an IANA timezone name.')
        ZoneInfo(self.zone)
        for value, maximum, minimum in ((self.lookback_hours, 168, 1),
                (self.catchup_minutes, 120, 0), (self.retention_hours, 24, 1)):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError('Choose bounded input, catch-up and retention periods.')
        if self.notification_filter not in ('always', 'important_only', 'important_or_uncertain'):
            raise ValueError('Choose a notification filter.')
        return self

    def canonical(self):
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))


def from_settings(data):
    if type(data) is not dict:
        raise ValueError('Structured routine settings are required.')
    try:
        return Settings(**data).validate()
    except TypeError as exc:
        raise ValueError('Unknown or invalid routine settings.') from exc


def proposal(settings):
    """No capability discovery, account access, scheduling or approval side effects."""
    settings.validate()
    public = settings.provider == 'official_news'
    job = Job(id='technology_digest' if public else 'message_review', revision=1,
              kind='technology_updates' if public else 'inbox_review',
              placement=settings.placement, sensitivity='public' if public else 'private',
              start=settings.start, notify=settings.notify, zone=settings.zone,
              account='' if public else 'account_not_connected',
              lookback_hours=settings.lookback_hours,
              catchup_seconds=settings.catchup_minutes * 60,
              retention_hours=settings.retention_hours,
              notification_filter=settings.notification_filter,
              importance_rules=() if public else ('owner_definition_required',),
              limits=Limits())
    # Private remote consent is deliberately unresolved; never invent approval to
    # make an incomplete draft pass the executable-contract validator.
    missing = ['Verified owner and approval of the exact executable contract',
               'Qualified worker and scheduler on the chosen device/server',
               'Connected owner notification route with delivery status']
    if public:
        missing.append('Qualified public report storage with expiry enforcement')
        missing.append('Live qualification of the selected official news sources')
        if settings.notification_filter != 'always':
            missing.append('Owner-defined relevance rules; current news matching is keyword based')
    else:
        if settings.provider == 'whatsapp_unspecified':
            missing.append('Personal WhatsApp or WhatsApp Business account choice')
        missing.extend(['Supported account connection, verified scopes and input adapter',
                        'Protected private report storage and key custody'])
        if settings.provider == 'whatsapp_personal':
            missing.append('A supported personal-inbox integration; Business API access cannot be assumed')
        if settings.notification_filter != 'always':
            missing.append('Owner-defined important-message rules and qualified classification')
        if settings.placement == 'oracle':
            missing.append('Explicit permission for private processing on the server')
    contract = asdict(job)
    envelope = {'schema': 1, 'state': 'draft_not_authorized_or_scheduled',
                'requested_provider': settings.provider, 'contract': contract}
    payload = json.dumps(envelope, sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    tomorrow = ' on the following day' if settings.notify < settings.start else ''
    text = [
        'DRAFT — NOT ENABLED OR SCHEDULED', PROVIDERS[settings.provider],
        f'Every day: collect at {settings.start}; request notification at {settings.notify}{tomorrow}.',
        f'Timezone: {settings.zone}. Proposed placement: {settings.placement}.',
        ('Desktop work needs this laptop awake with LYA running.' if settings.placement == 'desktop'
         else 'Laptop-off work needs a qualified online server; this screen installs no service.'),
        f'Input snapshot: preceding {settings.lookback_hours} hours, ending at collection time.',
        'Messages arriving after that snapshot are excluded from this report.' if not public
        else 'Coverage: OpenAI, Gemini and Anthropic selected sources; not the entire internet.',
        f'Missed run: allow up to {settings.catchup_minutes} minutes late, then skip.',
        'DST: skip nonexistent times; repeated times run once at the first occurrence.',
        'A notification time is the earliest request time, not a guaranteed completion or delivery time.',
        'Notification filter: ' + settings.notification_filter.replace('_', ' ') + '.',
        'Limits: 60 seconds, 8 requests, 100 items, 32 KiB report; zero outgoing replies.',
        'Stop on cancellation, changed authority, unavailable connection or exhausted budget.',
        'Limits are cooperative; production requires worker/process limits.',
        f'Report expiry: {settings.retention_hours} hours. No paid adapters permitted.',
        'Link requests: draft only. No approved catalogue, recipient scope or send delegation exists.',
        '', 'Required before activation:', *['• ' + item for item in missing],
        '', 'Saving preserves only these setup choices. It does not connect an account, approve a contract,',
        'start collection, send a reply, enable notifications or alter the existing hourly news watcher.',
        'Draft fingerprint: ' + fingerprint,
    ]
    return {'envelope': envelope, 'fingerprint': fingerprint,
            'missing': missing, 'text': '\n'.join(text)}


class DraftStore:
    """Only fixed setup choices, no free-text messages, credentials or account IDs."""
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def db(self):
        if self.path.is_symlink() or any(parent.is_symlink() for parent in self.path.parents):
            raise ValueError('Draft storage cannot use symbolic links.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=1)) as db:
            db.execute('PRAGMA max_page_count=128')
            db.execute('BEGIN IMMEDIATE')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version == 0:
                if db.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone():
                    raise ValueError('Unrelated database at draft path.')
                db.execute('CREATE TABLE drafts(id TEXT PRIMARY KEY, settings TEXT NOT NULL)')
                db.execute(f'PRAGMA user_version={SCHEMA}')
            elif version != SCHEMA:
                raise ValueError('Unsupported routine-draft schema.')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
        self.path.chmod(0o600)

    def save(self, settings):
        review = proposal(settings)
        key, payload = review['fingerprint'], settings.canonical()
        with self.db() as db:
            if not db.execute('SELECT 1 FROM drafts WHERE id=?', (key,)).fetchone():
                if db.execute('SELECT COUNT(*) FROM drafts').fetchone()[0] >= MAX_DRAFTS:
                    raise ValueError('Draft limit reached; remove an unused draft first.')
                db.execute('INSERT INTO drafts VALUES(?,?)', (key, payload))
        return key

    def list(self):
        with self.db() as db:
            rows = db.execute('SELECT id,settings FROM drafts ORDER BY rowid DESC LIMIT 33').fetchall()
        if len(rows) > MAX_DRAFTS:
            raise ValueError('Draft count exceeds the storage limit.')
        result = []
        for key, payload in rows:
            if not OPAQUE.fullmatch(key) or len(payload) > 4096:
                raise ValueError('Invalid saved draft.')
            settings = from_settings(json.loads(payload))
            if proposal(settings)['fingerprint'] != key:
                raise ValueError('Saved draft does not match this compiler; review migration is required.')
            result.append((key, settings))
        return result

    def delete(self, key):
        if type(key) is not str or not OPAQUE.fullmatch(key):
            raise ValueError('Invalid draft reference.')
        with self.db() as db:
            db.execute('DELETE FROM drafts WHERE id=?', (key,))
