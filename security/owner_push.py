"""Web Push for the private iPhone owner gate."""
import json
import re
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fido2.utils import websafe_decode, websafe_encode

from security import vault
from storage import store


def binding(owner):
    from hashlib import sha256
    return sha256(json.dumps([owner['person_id'], owner['credential'], owner['user_handle'],
                              owner.get('origin')], separators=(',', ':')).encode()).hexdigest()


def checked_subscription(data):
    if type(data) is not dict or set(data) != {'endpoint', 'keys'}:
        raise ValueError('Invalid iPhone subscription.')
    endpoint, keys = data['endpoint'], data['keys']
    if (type(endpoint) is not str or len(endpoint) > 2048
            or not re.fullmatch(r'https://(?:[a-z0-9-]+\.)+push\.apple\.com/[^\s#]+', endpoint)):
        raise ValueError('Use the iPhone Home Screen app.')
    if type(keys) is not dict or set(keys) != {'p256dh', 'auth'}:
        raise ValueError('Invalid iPhone subscription keys.')
    for key, size in (('p256dh', 65), ('auth', 16)):
        value = keys[key]
        if (type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{20,90}', value)
                or len(websafe_decode(value)) != size):
            raise ValueError('Invalid subscription key.')
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), websafe_decode(keys['p256dh']))
    return data


def load(owner, db_path):
    if not owner or not owner.get('origin'):
        return None
    with store.store_connection(db_path, read_only=True) as db:
        row = db.execute('SELECT payload FROM owner_push WHERE binding=?', (binding(owner),)).fetchone()
    return json.loads(vault.decrypt_text(row[0])) if row else None


def private_key(record=None):
    if record is None:
        return ec.generate_private_key(ec.SECP256R1())
    return serialization.load_der_private_key(websafe_decode(record['key']), password=None)


def public_key(key):
    return websafe_encode(key.public_key().public_bytes(serialization.Encoding.X962,
                                                        serialization.PublicFormat.UncompressedPoint))


def save(owner, session, key, subscription, db_path):
    checked_subscription(subscription)
    encoded = websafe_encode(key.private_bytes(serialization.Encoding.DER,
                                                serialization.PrivateFormat.PKCS8,
                                                serialization.NoEncryption()))
    payload = vault.encrypt_text(json.dumps({'key': encoded, 'subscription': subscription}))
    with store.store_connection(db_path) as db:
        store._profile_owner(db, session, owner['credential'])
        row = db.execute('SELECT origin FROM owner_phone_gate WHERE person_id=?', (session.person_id,)).fetchone()
        if row != (owner['origin'],):
            raise PermissionError('Owner phone changed.')
        db.execute('DELETE FROM owner_push')
        db.execute('INSERT INTO owner_push VALUES(?,?)', (binding(owner), payload))


def send(record, origin, token):
    import requests
    from pywebpush import webpush

    class AppleSession(requests.Session):
        def post(self, url, **kwargs):
            if url != subscription['endpoint']:
                raise ValueError('Unexpected notification destination.')
            return super().post(url, allow_redirects=False, **kwargs)

    subscription = checked_subscription(record['subscription'])
    endpoint = urlsplit(subscription['endpoint'])
    with AppleSession() as http:
        http.trust_env = False
        response = webpush(subscription, data=json.dumps({'ticket': token}),
                           vapid_private_key=record['key'],
                           vapid_claims={'aud': f'https://{endpoint.netloc}', 'sub': origin},
                           ttl=90, timeout=5, headers={'Urgency':'high'}, requests_session=http)
    if not 200 <= response.status_code < 300:
        raise RuntimeError('iPhone push was refused.')
