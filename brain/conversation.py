"""Isolated public-turn contract; not connected to either production chat path.

Only trusted authentication adapters resolve identity. No personal retrieval,
history, writes, tools, network calls or privilege grants exist in this module.
"""
from dataclasses import dataclass, field
import hashlib
import re
import threading
import time


STYLE_VERSION = 'lya-conversation-1'
STYLE = (
    'You are LYA, the same assistant across laptop and phone. Be warm, familiar, '
    'capable and precise. Give a direct, helpful answer. Keep ordinary replies brief; '
    'give detail when requested. Match the language of the current message. '
    'Avoid repetitive greetings, flattery and robotic permission recitals. '
    'Never invent a name or use Boss or Sir. Be clear about uncertainty. '
    'This is public conversation only. No tools, private memories, files, cameras '
    'or web search are connected to this contract. Never claim you executed an '
    'action or saved a fact. Say clearly when a requested action is unavailable. '
    'Friendly wording grants no additional permissions.'
)
OWNER_STYLE = ' A fresh signed owner verification is active. Use a warm, familiar owner tone without revealing identity details.'
PAIRED_STYLE = ' This is a paired device session; fresh owner verification is not active. Do not claim owner authority is unlocked.'


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Context:
    principal: str = field(repr=False)
    device: str
    session: str = field(repr=False)
    generation: str = field(repr=False)
    expires_at: float
    owner_verified: bool


def _desktop_context(brain):
    from storage import store
    session = brain.session
    if not brain._identified():
        raise PermissionError('Fresh owner verification required.')
    # Reuse the unique-active-owner/passkey check used by mobile pairing.
    with store.store_connection(brain.db_path, read_only=True) as db:
        credential = store._profile_owner(db, session)
    if brain.session != session:
        raise PermissionError('Identity changed.')
    # shortcut: pairing-key identity; add explicit stable-owner/rotation mapping before durable shared records.
    binding = _digest(credential)
    return Context(binding, 'laptop', _digest(session.id), binding,
                   session.verified_until, True)


def _phone_context(connection, token):
    with connection.lock:
        session = connection.session(token)
        with connection.store.db() as db:
            row = db.execute('SELECT owner FROM binding WHERE id=1').fetchone()
        if not row or type(row[0]) is not str or not re.fullmatch('[a-f0-9]{64}', row[0]):
            raise PermissionError('Trusted laptop pairing required.')
        return Context(row[0], 'phone', _digest(token), session['stamp'],
                       session['until'], connection.clock() < session['owner_until'])


@dataclass(frozen=True)
class PublicTurn:
    request_id: str
    text: str = field(repr=False)
    context: Context = field(repr=False)
    deadline: float
    _resolve: object = field(repr=False)
    _clock: object = field(repr=False)
    _cancelled: object = field(repr=False)

    def check(self):
        if self._cancelled.is_set():
            raise InterruptedError('Cancelled.')
        if time.monotonic() >= self.deadline or self._clock() >= self.context.expires_at:
            raise PermissionError('Turn deadline expired.')
        if self._resolve() != self.context:
            raise PermissionError('Identity or verification changed.')

    def answer(self, infer):
        """Call an injected provider; revalidate before releasing any reply.

        Production adapters must retain their own admission/replay controls.
        This contract neither retries nor makes a durable idempotency claim.
        """
        self.check()
        prompt = STYLE + (OWNER_STYLE if self.context.owner_verified else PAIRED_STYLE)
        answer = infer([{'role': 'system', 'content': prompt},
                        {'role': 'user', 'content': self.text}], self._cancelled)
        self.check()
        if type(answer) is not str or not answer.strip() or len(answer) > 8000:
            raise ValueError('No usable answer.')
        return {'text': answer, 'id': self.request_id}


def _turn(packet, resolve, clock, cancelled):
    if type(packet) is not dict or set(packet) != {'id', 'text'}:
        raise ValueError('Only request id and public text are accepted.')
    rid, text = packet['id'], packet['text']
    if type(rid) is not str or not re.fullmatch('[a-f0-9]{32}', rid):
        raise ValueError('Invalid request ID.')
    if type(text) is not str or len(text) > 4000 or not text.strip():
        raise ValueError('Use a question of up to 4000 characters.')
    context = resolve()
    turn = PublicTurn(rid, text.strip(), context, time.monotonic() + 30,
                      resolve, clock, cancelled if cancelled is not None else threading.Event())
    turn.check()
    return turn


def desktop_turn(brain, packet, cancelled=None):
    """Trusted native adapter; never accept a client-supplied owner identity."""
    return _turn(packet, lambda: _desktop_context(brain), brain.clock, cancelled)


def phone_turn(connection, token, packet, cancelled=None):
    """Trusted phone adapter; existing passkey session remains public-chat only."""
    return _turn(packet, lambda: _phone_context(connection, token), connection.clock, cancelled)
