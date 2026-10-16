"""Structured automation contracts. Text/model output cannot authorize a job."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from cloud.web_reader import public_url

UTC = timezone.utc
REF = re.compile(r'[a-zA-Z][a-zA-Z0-9_-]{2,63}')
OPAQUE = re.compile(r'[a-f0-9]{64}')


@dataclass(frozen=True)
class Limits:
    seconds: int = 60
    requests: int = 8
    items: int = 100
    result_bytes: int = 32768
    sends: int = 0

    def validate(self):
        for field, maximum in [('seconds',120),('requests',20),('items',200),('result_bytes',65536),('sends',20)]:
            value = getattr(self, field)
            if type(value) is not int or not (0 if field=='sends' else 1) <= value <= maximum:
                raise ValueError('Invalid task resource limit: ' + field)


@dataclass(frozen=True)
class Job:
    id: str
    revision: int
    kind: str
    placement: str
    sensitivity: str
    start: str
    notify: str
    zone: str = 'Asia/Kolkata'
    account: str = ''
    owner: str = 'owner_not_connected'
    catchup_seconds: int = 1800
    retention_hours: int = 24
    lookback_hours: int = 24
    importance_rules: tuple = ()
    notification_filter: str = 'important_or_uncertain'
    send_mode: str = 'draft_only'
    catalog: tuple = ()  # Exact (resource key, approved public HTTPS URL) pairs.
    private_remote: bool = False
    zero_spend: bool = True
    limits: Limits = Limits()

    def validate(self):
        if not REF.fullmatch(self.id) or type(self.revision) is not int or self.revision < 1:
            raise ValueError('A stable job ID and positive revision are required.')
        if self.kind not in ('technology_updates','inbox_review') or self.placement not in ('desktop','oracle'):
            raise ValueError('Unsupported task or execution placement.')
        if self.sensitivity not in ('public','private') or not REF.fullmatch(self.owner):
            raise ValueError('Invalid task sensitivity or owner reference.')
        ZoneInfo(self.zone)  # Missing timezone data fails explicitly; never assume server local time.
        for value in (self.start,self.notify):
            if type(value) is not str or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):
                raise ValueError('Use explicit 24-hour start/notification times.')
        if type(self.catchup_seconds) is not int or not 0 <= self.catchup_seconds <= 7200:
            raise ValueError('Choose a bounded missed-run grace period.')
        if type(self.retention_hours) is not int or not 1 <= self.retention_hours <= (24 if self.sensitivity=='private' else 168):
            raise ValueError('Invalid report retention limit.')
        if self.zero_spend is not True or type(self.private_remote) is not bool:
            raise ValueError('This executor requires zero-spend adapters and explicit remote-data policy.')
        if self.sensitivity=='private' and self.placement=='oracle' and not self.private_remote:
            raise ValueError('Private server processing has not been explicitly permitted.')
        if type(self.lookback_hours) is not int or not 1 <= self.lookback_hours <= 168:
            raise ValueError('Choose a bounded input time window.')
        if type(self.importance_rules) is not tuple or len(self.importance_rules)>16 or any(not isinstance(value,str) or not REF.fullmatch(value) for value in self.importance_rules):
            raise ValueError('Invalid owner-defined importance-rule references.')
        if self.kind=='inbox_review' and self.notification_filter!='always' and not self.importance_rules:
            raise ValueError('Important-message filtering needs explicit owner-defined rules.')
        if self.notification_filter not in ('always','important_only','important_or_uncertain'):
            raise ValueError('Choose an explicit notification filter.')
        if self.send_mode not in ('draft_only','approved_catalog'):
            raise ValueError('Unsupported outgoing-message authority.')
        self.limits.validate()
        if self.kind=='technology_updates' and (self.sensitivity!='public' or self.account or self.catalog or self.limits.sends or self.send_mode!='draft_only'):
            raise ValueError('Public technology jobs cannot access accounts or send replies.')
        if self.kind=='inbox_review' and not REF.fullmatch(self.account):
            raise ValueError('An explicit connected account reference is required.')
        if type(self.catalog) is not tuple or len(self.catalog)>20:
            raise ValueError('Invalid approved-link catalogue.')
        keys=set()
        for entry in self.catalog:
            if type(entry) is not tuple or len(entry)!=2 or not REF.fullmatch(entry[0]) or entry[0] in keys:
                raise ValueError('Invalid or repeated resource key.')
            url=public_url(entry[1])
            if url != entry[1] or re.search(r'(?i)[?&](?:token|key|api_key|password|secret|auth)=',url):
                raise ValueError('Catalogue links must be exact public HTTPS URLs without credentials.')
            keys.add(entry[0])
        if self.send_mode=='approved_catalog' and (not self.catalog or self.limits.sends<1):
            raise ValueError('Auto replies need an exact catalogue and send cap.')
        return self

    def canonical(self):
        self.validate()
        return json.dumps(asdict(self),sort_keys=True,separators=(',',':'))

    def digest(self):
        return hashlib.sha256(self.canonical().encode()).hexdigest()


def from_dict(data):
    if type(data) is not dict: raise ValueError('A structured task contract is required.')
    data=dict(data)
    try:
        if 'limits' in data: data['limits']=Limits(**data['limits'])
        if 'importance_rules' in data:data['importance_rules']=tuple(data['importance_rules'])
        if 'catalog' in data: data['catalog']=tuple(tuple(entry) for entry in data['catalog'])
        return Job(**data).validate()
    except (TypeError,KeyError) as exc:
        raise ValueError('Unknown or invalid task contract fields.') from exc


def wall_time(day, value, zone):
    naive=datetime.combine(day,datetime.strptime(value,'%H:%M').time())
    local=naive.replace(tzinfo=ZoneInfo(zone),fold=0)
    # Skip a nonexistent wall time; repeated times run once, at the first occurrence.
    if local.astimezone(UTC).astimezone(ZoneInfo(zone)).replace(tzinfo=None)!=naive:
        return None
    return local.astimezone(UTC)


def due_slot(job, now):
    job.validate()
    local=datetime.fromtimestamp(now,UTC).astimezone(ZoneInfo(job.zone))
    for day in (local.date(),local.date()-timedelta(days=1)):
        start=wall_time(day,job.start,job.zone)
        if start is None: continue
        lateness=now-start.timestamp()
        if 0<=lateness<=job.catchup_seconds:
            report_day=day+(timedelta(days=1) if job.notify<job.start else timedelta())
            notify=wall_time(report_day,job.notify,job.zone)
            if notify is None: return None
            key=hashlib.sha256(f'{job.id}:{job.revision}:{start.isoformat()}'.encode()).hexdigest()
            return {'id':key,'scheduled':start.timestamp(),'notify':notify.timestamp(),'late_seconds':int(lateness)}
    return None
