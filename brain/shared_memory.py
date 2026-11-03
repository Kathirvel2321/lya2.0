"""Shared client integration for the explicitly synthetic publication authority.

No real-memory activation, enrollment, provider call or implicit writer takeover.
"""
from datetime import datetime
import hashlib
import re
import threading

from brain.conversation import PublicTurn
from brain.memory_authority import WriterGrant
from brain.memory_prototype import Conflict, MAX_REQUESTS, MAX_RECORDS, _id, _text, _validate
from brain.memory_publication_authority import SyntheticPublicationAuthority


class SharedMemoryUncertain(ValueError):
    shared_memory_uncertain = True


def parse_command(text, request_id):
    _id(request_id)
    if type(text) is not str or not 1 <= len(text) <= 4000:
        raise ValueError('Use a shared-memory command of up to 4,000 characters.')
    match = re.fullmatch(r'shared memory ([a-zA-Z0-9_-]{1,64}):\s*(.+)', text.strip(), re.I | re.S)
    if not match:
        raise ValueError('Use shared memory demo: remember permanent colour = blue / recall colour / correct colour = green / forget colour.')
    project, body = match.groups()
    operation = re.fullmatch(r'(remember|correct|recall|forget)\s+(.+)', body.strip(), re.I | re.S)
    if not operation:
        raise ValueError('Shared memory supports remember, recall, correct and forget.')
    verb, argument = operation.groups(); verb = verb.casefold()
    packet = dict(op={'remember': 'save', 'recall': 'search', 'correct': 'correct', 'forget': 'forget'}[verb],
                  project=project.casefold())
    if verb in ('remember', 'correct'):
        label, separator, value = argument.partition('=')
        if not separator or not value.strip() or len(value.strip()) > 2000:
            raise ValueError('Use label = a note of up to 2,000 characters.')
        packet.update(request_id=request_id, value={'text': value.strip()})
        if verb == 'remember':
            policy, separator, label = label.strip().partition(' ')
            policy = policy.casefold()
            if not separator or policy not in ('short', 'long', 'permanent', 'until'):
                raise ValueError('Choose short, long, permanent or until with a timezone.')
            retention = {'mode': policy}
            if policy == 'until':
                stamp, separator, label = label.strip().partition(' ')
                deadline = datetime.fromisoformat(stamp)
                if not separator or deadline.tzinfo is None:
                    raise ValueError('Include the expiry timezone and a label.')
                retention['expires_at'] = deadline.timestamp()
            packet.update(kind='fact', retention=retention)
    else:
        label = argument
        if verb == 'forget': packet['request_id'] = request_id
    label = _text(label, 400)
    if re.search(r'\b(password|secret|credential|api[ _-]?key)\b', label, re.I):
        raise PermissionError('Credentials belong in protected custody, not shared conversation memory.')
    if verb == 'remember': packet['key'] = label
    if verb == 'recall': packet['query'] = label
    action = 'memory_read' if verb == 'recall' else 'memory_forget' if verb == 'forget' else 'memory_write'
    return packet, label, action


class SharedMemoryService:
    """One existing fenced writer shared by both authenticated client adapters."""
    synthetic_only = True

    def __init__(self, authority, grant, *, synthetic_only=False):
        if synthetic_only is not True or type(authority) is not SyntheticPublicationAuthority:
            raise PermissionError('Only an explicitly configured synthetic shared-memory pilot is supported.')
        if type(grant) is not WriterGrant:
            raise PermissionError('An existing server writer grant is required.')
        self.authority, self.grant = authority, grant
        self.lock = threading.RLock()
        if (authority._repository.path.parent / 'RECOVERY-INCOMPLETE').exists():
            raise PermissionError('Incomplete recovery cannot serve shared memory.')
        with authority._repository._db() as db:
            authority._schema(db); authority._grant(db, grant)
            # Only hashes and resolved IDs/revisions; never command text, note values or grants.
            db.execute('''CREATE TABLE IF NOT EXISTS shared_requests(
                principal TEXT NOT NULL, request_id TEXT NOT NULL, command_sha256 TEXT NOT NULL,
                target_id TEXT, target_revision INTEGER, PRIMARY KEY(principal,request_id))''')

    def respond(self, turn):
        if type(turn) is not PublicTurn or not turn.context.owner_verified:
            raise PermissionError('Verify the owner before using shared memory.')
        turn.check()
        packet, label, _ = parse_command(turn.text, turn.request_id)
        with self.lock:
            # Persist resolution before sending a mutation: an interrupted correction must
            # retry its original revision, rather than silently overwrite a later change.
            with self.authority._repository._db() as db:
                self.authority._grant(db, self.grant)
                link, head, _, _, _ = self.authority._link(db, self.grant.lineage)
                if link['operation_id'] is not None:
                    raise Conflict('Shared publication is pending; explicit reconciliation is required.')
                _, anchor, memory, *_ = self.authority._entry(db, self.grant.lineage)
                if self.authority._latest.head(self.grant.lineage) != head:
                    raise Conflict('Shared latest state is uncertain; no local fallback is allowed.')
                with memory._db() as source:
                    owner = memory._owner(source, turn, True)
                    if 'request_id' in packet:
                        digest = hashlib.sha256(turn.text.encode()).hexdigest()
                        prior = db.execute('SELECT command_sha256,target_id,target_revision FROM shared_requests WHERE principal=? AND request_id=?',
                                           (turn.context.principal, turn.request_id)).fetchone()
                        if prior and prior['command_sha256'] != digest:
                            raise Conflict('Shared request ID was reused with different text.')
                        if packet['op'] in ('correct', 'forget'):
                            if prior:
                                target, revision = prior['target_id'], prior['target_revision']
                            else:
                                row = source.execute('''SELECT id,revision FROM memories WHERE owner=? AND project=?
                                    AND normkey=? AND deleted=0 AND (expires_at IS NULL OR expires_at>?)''',
                                    (owner, packet['project'], label.casefold(), memory.clock())).fetchone()
                                if not row: raise Conflict('No active shared note has that exact label.')
                                target, revision = row['id'], row['revision']
                            packet.update(id=target, expected_revision=revision)
                        if not prior:
                            count = db.execute('SELECT COUNT(*) FROM shared_requests').fetchone()[0]
                            if count >= MAX_REQUESTS + (MAX_RECORDS if packet['op'] == 'forget' else 0):
                                raise ValueError('Shared request budget is full.')
                            db.execute('INSERT INTO shared_requests VALUES(?,?,?,?,?)',
                                       (turn.context.principal, turn.request_id, digest, packet.get('id'), packet.get('expected_revision')))
                packet = _validate(packet)
                turn.check()
            try:
                reply = self.authority.handle(self.grant, turn, packet, expected_anchor=anchor,
                                              approved=True, cancelled=turn._cancelled.is_set)
            except Exception:
                raise SharedMemoryUncertain('Shared completion is unconfirmed. Retry the same request after explicit publication reconciliation; a write may have committed.') from None
        turn.check()
        if reply.get('publication_confirmed') is not True:
            raise Conflict('Shared publication was not confirmed.')
        data = reply['result']
        if packet['op'] == 'search':
            records = data['records'][:3]
            text = '\n'.join(f"{r['key']}: {r['value'].get('text', '')}" for r in records) or 'No matching active shared memories.'
            if len(data['records']) > 3:text += '\nMore matches are available; use a more specific label.'
            expiry = min((r['expires_at'] for r in records if r['expires_at'] is not None), default=None)
        else:
            expiry = None
            text = {'save': 'Saved', 'correct': 'Corrected', 'forget': 'Forgot'}[packet['op']] + ' the shared note.'
        if expiry is not None and turn._clock() >= expiry:
            raise PermissionError('Shared memory expired before delivery.')
        return dict(text='Shared demo memory: ' + text, synthetic_only=True,
                    publication_confirmed=True, project=packet['project'], expires_at=expiry)
