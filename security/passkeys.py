"""Phone-owner WebAuthn through nearby transport or the private laptop HTTPS gate.

The private gate uses a short-lived QR and a separate laptop pairing code.
The authenticator keeps its private key and verifies the user through the platform.
"""
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from fido2.server import Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import (AttestedCredentialData, AuthenticationResponse,
                           RegistrationResponse, PublicKeyCredentialRpEntity)

from security import phone_profiles
from security.policy import PROCESS_SESSION_END, Session, owner_passphrase_required
from storage import store

PHONE_PORT = 8767


def phone_host(origin):
    if (type(origin) is not str or len(origin) > 145
            or not re.fullmatch(r'https://[a-z0-9-]{1,63}\.[a-z0-9-]{1,63}\.ts\.net', origin)):
        raise ValueError('An exact private laptop HTTPS origin is required.')
    return origin.removeprefix('https://')


def check_phone_proxy(origin):
    """Check the laptop's private Serve mapping before presenting an invitation."""
    host = phone_host(origin)

    def status(*args):
        reply = subprocess.run(['tailscale', *args, 'status', '--json'], capture_output=True,
                               check=True, timeout=3,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return json.loads(reply.stdout)

    node, config = status(), status('serve')
    mapping = host + ':443'
    proxy = (config.get('Web') or {}).get(mapping, {}).get('Handlers', {}).get('/', {}).get('Proxy')
    if (node.get('BackendState') != 'Running'
            or (node.get('Self') or {}).get('DNSName', '').rstrip('.') != host
            or (config.get('TCP') or {}).get('443', {}).get('HTTPS') is not True
            or proxy != f'http://127.0.0.1:{PHONE_PORT}'
            or (config.get('AllowFunnel') or {}).get(mapping)):
        raise PermissionError('The configured hostname does not serve the private laptop gate.')


def phrase_verifier(phrase, salt):
    if type(phrase) is not str or not 16 <= len(phrase) <= 200 or not phrase.strip() or not phrase.isprintable():
        raise ValueError('Use a unique printable passphrase of 16 to 200 characters.')
    return hashlib.scrypt(phrase.encode('utf-8'), salt=salt, n=2**17, r=8, p=1,
                          maxmem=160 * 1024 * 1024, dklen=32).hex()


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LYA · Owner verification</title>
<style>
:root{color-scheme:dark;font:16px 'Segoe UI',sans-serif;background:#091016;color:#dce0e4}
body{margin:0;min-height:100vh;display:grid;place-items:center}
main{box-sizing:border-box;position:relative;width:min(460px,calc(100% - 32px));margin:16px;padding:40px 28px 32px;text-align:center;background:linear-gradient(140deg,#1c272f,#0e181f 45%,#091016);border:1px solid #465b66;clip-path:polygon(22px 0,calc(100% - 40px) 0,100% 40px,100% calc(100% - 22px),calc(100% - 22px) 100%,22px 100%,0 calc(100% - 22px),0 22px)}
main::before{content:'';position:absolute;top:0;left:24px;width:66px;height:1px;background:#9cdfe8}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0}
.dot{display:block;width:min(260px,100%);height:auto;margin:0 auto 28px;color:#ffc26b}
.dot ellipse{fill:none;stroke:currentColor;stroke-width:2.6;stroke-linecap:round;stroke-dasharray:.1 10}
.dot ellipse:nth-child(2){color:#ada7d3}.dot ellipse:nth-child(3){color:#b9d4cf}
.dot path,.dot rect{fill:none;stroke:currentColor;stroke-width:1.5}
main[data-state=waiting] .dot{animation:breathe 2.8s ease-in-out infinite}
main[data-state=verified] .dot{color:#77e0b2}main[data-state=failed] .dot{color:#ff879b}
@keyframes breathe{50%{opacity:.65;transform:scale(.97)}}
@media(prefers-reduced-motion:reduce){main[data-state=waiting] .dot{animation:none}}
pre{max-height:50vh;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;line-height:1.6;text-align:left;padding:20px;border:1px solid #465b66;border-radius:12px;margin:0 0 24px}
button{display:block;width:56px;height:56px;margin:0 auto;border:1px solid #658594;border-radius:16px;background:#172c35;color:#b9e6e6;cursor:pointer}
button:focus-visible{outline:2px solid #9cdfe8;outline-offset:5px}button:hover{background:#224153}button:disabled{opacity:.5;cursor:default}
button svg{width:22px;height:26px;fill:none;stroke:currentColor;stroke-width:1.4}
</style><main data-state="ready" aria-labelledby="title"><h1 id="title" class="sr-only">Use your phone passkey</h1>
<svg class="dot" viewBox="0 0 260 220" aria-hidden="true"><ellipse cx="130" cy="110" rx="84" ry="36"/><ellipse cx="130" cy="110" rx="96" ry="56"/><ellipse cx="130" cy="110" rx="108" ry="76"/><rect x="120" y="92" width="20" height="36" rx="5"/><path d="M127 122h6"/></svg><pre id="context" hidden></pre>
<button id="go" aria-label="Continue with phone"><svg viewBox="0 0 22 26" aria-hidden="true"><rect x="4" y="1.5" width="14" height="23" rx="3"/><path d="M9 4h4M10 21.5h2"/></svg></button>
<p id="status" class="sr-only" role="status" aria-live="polite">Choose another device in the browser and scan its QR with your phone. Keep Bluetooth on and your phone nearby.</p></main>
<script nonce="__NONCE__">
const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);
const go=document.querySelector('#go'),status=document.querySelector('#status'),main=document.querySelector('main');
const dec=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
const enc=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
async function api(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-LYA-Ceremony':token},body:JSON.stringify(data)});if(!r.ok)throw Error('Verification failed or expired. Return to LYA and retry.');return r.json()}
go.onclick=async()=>{go.disabled=true;try{
 if(!window.isSecureContext||!navigator.credentials)throw Error('Use a current Chrome or Edge browser on this laptop.');
 const x=await api('/options',{}),o=x.publicKey;
 document.querySelector('#title').textContent=x.title;
 const context=document.querySelector('#context');context.textContent=x.context;context.hidden=!x.context;
 // Review the exact operation before opening the authenticator, never approve from load.
 if(x.context&&!go.dataset.reviewed){go.dataset.reviewed='yes';go.setAttribute('aria-label','Approve this exact action');status.textContent='Read the action above, then approve with your phone.';go.disabled=false;return}
 o.challenge=dec(o.challenge);o.hints=['hybrid'];
 if(o.user)o.user.id=dec(o.user.id);
 for(const k of ['allowCredentials','excludeCredentials'])if(o[k])o[k]=o[k].map(c=>({...c,id:dec(c.id),transports:['hybrid']}));
 status.textContent='Waiting for your phone. LYA cannot approve this for you.';
 main.dataset.state='waiting';
 const c=x.phase==='create'?await navigator.credentials.create({publicKey:o}):await navigator.credentials.get({publicKey:o});
 if(!c)throw Error('Phone verification cancelled.');
 const r=c.response,b={id:c.id,rawId:enc(c.rawId),type:c.type,response:{clientDataJSON:enc(r.clientDataJSON)},clientExtensionResults:c.getClientExtensionResults()};
 if(x.phase==='create')b.response.attestationObject=enc(r.attestationObject);
 else Object.assign(b.response,{authenticatorData:enc(r.authenticatorData),signature:enc(r.signature),userHandle:r.userHandle?enc(r.userHandle):null});
 const done=await api('/complete',b);
 if(done.confirm){main.dataset.state='ready';go.setAttribute('aria-label','Verify the new passkey');status.textContent='Passkey created. Verify it once more before LYA saves your owner profile.';go.disabled=false}
 else{main.dataset.state='verified';status.textContent='Verified. Return to LYA. You can close this tab.';go.setAttribute('aria-label','Verified')}
 }catch(e){try{await api('/cancel',{})}catch(_){}main.dataset.state='failed';status.textContent=e.name==='NotAllowedError'?'Cancelled or unavailable. Return to LYA and retry.':e.message;go.setAttribute('aria-label','Return to LYA');go.disabled=true}};
</script></html>'''


class PasskeyCeremony:
    """One bounded loopback backend; credential creation needs signed confirmation."""
    def __init__(self, *, db_path=None, name='Owner', approval=None, clock=time.monotonic,
                 approval_valid=None, phone_origin=None, phone_port=PHONE_PORT,
                 prefer_push=False, notification_setup=False):
        self.db_path, self.name, self.approval, self.clock = db_path, name, approval, clock
        self.approval_valid = approval_valid
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError('Use a printable owner name of 1 to 80 characters.')
        self.owner = store.get_owner_passkey(db_path)
        persisted_origin = self.owner.get('origin') if self.owner else None
        if persisted_origin and persisted_origin != phone_origin:
            raise PermissionError('Restore the private HTTPS origin enrolled for this owner.')
        self.direct = bool(persisted_origin or (phone_origin and not self.owner))
        self.host = phone_host(phone_origin) if self.direct else None
        self.notification_setup = notification_setup
        if notification_setup and (not persisted_origin or approval):
            raise PermissionError('Register your admin passkey on the private phone page first.')
        self.push_record = None
        self.push_key = None
        self.setup_code = f'{secrets.randbelow(10**8):08d}' if notification_setup else ''
        self.setup_attempts = 0
        if self.direct and self.owner and (prefer_push or notification_setup):
            from security import owner_push
            record = owner_push.load(self.owner, db_path)
            if notification_setup:
                self.push_key = owner_push.private_key(record)
            else:
                self.push_record = record
        self.pairing_code = f'{secrets.randbelow(10**8):08d}' if self.direct and not self.owner else ''
        self.phone_gate = None
        self.profile_vectors = None
        self.profile_attempts = 0
        self.confirmed_counter = None
        if approval is not None and (self.owner is None or self.owner['person_id'] != approval.session.person_id
                or approval.session.role != 'admin' or time.time() >= approval.session.verified_until):
            raise PermissionError('The pending action has no current passkey owner.')
        if approval and approval.session.owner_binding:
            from security.owner_push import binding
            if not self.push_record or approval.session.owner_binding != binding(self.owner):
                raise PermissionError('The trusted phone changed. Verify again.')
        self.token, self.script_nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self.lock, self.done = threading.RLock(), threading.Event()
        self.result, self.error, self.credential = None, None, None
        self.deadline = clock() + (90 if self.push_record else 300 if self.direct else 180)
        if approval:
            self.deadline = min(self.deadline, approval.deadline)
        phrase = self.direct and ((not approval and not self.push_record)
                                  or approval and self.push_record and owner_passphrase_required(approval.action, approval.parameters))
        self.phase = ('unlock' if phrase else 'authenticate') if self.owner else 'create'
        self.user_handle = websafe_decode(self.owner['user_handle']) if self.owner else secrets.token_bytes(32)
        if self.owner:
            self.credential = AttestedCredentialData(websafe_decode(self.owner['credential']))
        self.http = HTTPServer(('127.0.0.1', phone_port if self.direct else 0), self._handler())
        self.origin = phone_origin if self.direct else f'http://localhost:{self.http.server_port}'
        self.host = self.host or self.origin.removeprefix('http://')
        self.server = Fido2Server(PublicKeyCredentialRpEntity(id=self.host if self.direct else 'localhost', name='LYA Owner'),
                                 attestation='none', verify_origin=lambda origin: origin == self.origin)
        self.server.allowed_algorithms = [p for p in self.server.allowed_algorithms if p.alg == -7]
        if self.credential is not None and self.credential.public_key.ALGORITHM != -7:
            self.http.server_close()
            raise PermissionError('This owner credential uses an unsupported algorithm.')
        self.server.timeout = 120000
        try:
            self.options, self.state = (None, None) if self.phase == 'unlock' else self._begin()
        except Exception:
            self.http.server_close()
            raise
        self.thread = threading.Thread(target=self.http.serve_forever, kwargs={'poll_interval': .1},
                                       daemon=True, name='LYA-Passkey')
        self.thread.start()
        self._closed = False
        self.expiry = threading.Timer(max(.1, self.deadline - self.clock()), self.close)
        self.expiry.daemon = True
        self.expiry.start()

    @property
    def url(self):
        return self.origin + '/#' + self.token

    def _begin(self):
        if self.phase == 'create':
            return self.server.register_begin(
                dict(id=self.user_handle, name=self.name, displayName=self.name),
                resident_key_requirement='required', user_verification='required',
                authenticator_attachment='platform' if self.direct else 'cross-platform')
        # An approval challenge is cryptographically bound to its exact pending operation.
        challenge = None
        if self.approval:
            payload = json.dumps([self.approval.nonce, self.approval.action, self.approval.parameters,
                                  self.approval.session.id], ensure_ascii=False).encode()
            challenge = hashlib.sha256(payload).digest()
        return self.server.authenticate_begin([self.credential], user_verification='required', challenge=challenge)

    def _check_live(self):
        if self.done.is_set() or self.clock() >= self.deadline:
            raise PermissionError('Verification expired or already used.')
        if self.approval and time.time() >= self.approval.session.verified_until:
            raise PermissionError('Owner session expired.')
        if self.approval_valid is not None and self.approval_valid() is not True:
            raise PermissionError('The exact action was cancelled or changed.')

    def options_json(self):
        with self.lock:
            self._check_live()
            public = dict(self.options)['publicKey'] if self.options is not None else None
            result = dict(publicKey=public, phase=self.phase,
                        title='Approve one LYA action' if self.approval else 'Use your phone passkey',
                        context=(self.approval.action.replace('_', ' ').capitalize() + '\n\n' + self.approval.parameters) if self.approval else '',
                        remaining=max(0, int((self.deadline - self.clock()) * 1000)))
            if self.phase in ('profiles', 'profile_retry'):
                result['captureReady'] = phone_profiles.available()
            if self.phase == 'notifications':
                from security import owner_push
                result['pushKey'] = owner_push.public_key(self.push_key)
            return result

    def claim_setup_code(self, code):
        with self.lock:
            self._check_live()
            self.setup_attempts += 1
            if (not self.notification_setup or self.phase != 'unlock' or not self.setup_code
                    or self.setup_attempts > 10 or type(code) is not str or len(code) != 8
                    or not code.isascii() or not secrets.compare_digest(self.setup_code, code)):
                raise PermissionError('Invalid setup code.')
            self.setup_code = ''
            return {'token': self.token}

    def signed_session(self, name, person_id, persistent):
        identity = ''
        if persistent:
            from security.owner_push import binding
            identity = binding(self.owner)
        until = PROCESS_SESSION_END if persistent else time.time() + 300
        return Session('admin', name, secrets.token_urlsafe(24), person_id, until, identity)

    def subscribe(self, subscription):
        with self.lock:
            self._check_live()
            if self.phase != 'notifications' or not self.notification_setup:
                raise PermissionError('Verify the owner before connecting notifications.')
            from security import owner_push
            owner_push.save(self.owner, self.subscription_session, self.push_key, subscription, self.db_path)
            self._check_live()
            self.result = self.signed_session(self.owner['display_name'], self.owner['person_id'], True)
            self.done.set()
            return {'verified': True}

    def submit_details(self, data):
        with self.lock:
            self._check_live()
            if not self.direct or self.phase not in ('details', 'unlock'):
                raise PermissionError('The ceremony is not accepting details.')
            try:
                if self.phase == 'details':
                    name, code = data.get('name'), data.get('code')
                    if (type(name) is not str or not 1 <= len(name.strip()) <= 80 or not name.isprintable()
                            or type(code) is not str or len(code) != 8 or not code.isascii()
                            or not secrets.compare_digest(code, self.pairing_code)):
                        raise ValueError('Laptop pairing or owner details do not match.')
                    salt = secrets.token_bytes(16)
                    self.phone_gate = self.origin, salt.hex() + ':' + phrase_verifier(data.get('phrase'), salt)
                    self.name, self.pairing_code = name.strip(), ''
                    self.phase = 'confirm'
                else:
                    salt, expected = self.owner['phrase_verifier'].split(':', 1)
                    if not secrets.compare_digest(phrase_verifier(data.get('phrase'), bytes.fromhex(salt)), expected):
                        raise PermissionError('The owner passphrase does not match.')
                    self.phase = 'authenticate'
                self._check_live()
                self.options, self.state = self._begin()
                # The scanned invitation stops working once the laptop code or passphrase is verified.
                self.token = secrets.token_urlsafe(32)
                return {'token': self.token}
            except Exception:
                self.cancel()
                raise

    def complete(self, response):
        with self.lock:
            self._check_live()
            if self.phase not in ('create', 'confirm', 'authenticate'):
                raise PermissionError('Owner details are required before verification.')
            try:
                if self.phase == 'create':
                    parsed = RegistrationResponse.from_dict(response)
                    self._check_client(parsed.response.client_data)
                    data = self.server.register_complete(self.state, parsed)
                    cred = data.credential_data
                    if (cred is None or not cred.credential_id or parsed.raw_id != cred.credential_id
                            or not 0 < len(bytes(cred)) <= 8192 or cred.public_key.ALGORITHM != -7):
                        raise ValueError('Invalid registered credential.')
                    self.credential, self.initial_counter = cred, data.counter
                    self.backup_eligible = bool(data.flags & data.FLAG.BE)
                    self._check_flags(data)
                    if self.direct:
                        self.phase = 'details'
                        self.options, self.state = None, None
                        return {'details': True}
                    self.phase = 'confirm'
                    self.options, self.state = self._begin()
                    return {'confirm': True}
                parsed = AuthenticationResponse.from_dict(response)
                self._check_client(parsed.response.client_data)
                self.server.authenticate_complete(self.state, [self.credential], parsed)
                data = parsed.response.authenticator_data
                self._check_flags(data)
                handle = parsed.response.user_handle
                if handle is not None and handle != self.user_handle:
                    raise ValueError('Wrong passkey user handle.')
                eligible = bool(data.flags & data.FLAG.BE)
                self._check_live()
                if self.phase == 'confirm':
                    if eligible != self.backup_eligible or ((self.initial_counter or data.counter)
                            and data.counter <= self.initial_counter):
                        raise ValueError('Invalid new passkey counter or backup flags.')
                    if self.direct:
                        self.phase = 'profiles'
                        self.confirmed_counter = data.counter
                        self.state, self.options = None, None
                        return {'profiles': True}
                    pid = store.register_passkey_owner(self.name, websafe_encode(bytes(self.credential)),
                        websafe_encode(self.user_handle), data.counter, eligible, self.db_path)
                    name = self.name
                else:
                    store.accept_passkey_assertion(self.owner, data.counter, eligible, self.db_path)
                    pid, name = self.owner['person_id'], self.owner['display_name']
                self._check_live()
                if self.notification_setup:
                    self.subscription_session = self.signed_session(name, pid, False)
                    self.phase = 'notifications'
                    self.options, self.state = None, None
                    self.token = secrets.token_urlsafe(32)
                    return {'notifications': True, 'token': self.token}
                self.result = self.approval or self.signed_session(name, pid, bool(self.push_record))
                self.done.set()
                self.state = None
                return {'verified': True}
            except Exception:
                self.error = 'Phone proof failed. Nothing was unlocked. Start a fresh attempt.'
                self.done.set()
                self.state = None
                raise

    def accept_media(self, raw):
        with self.lock:
            self._check_live()
            if (self.phase not in ('profiles', 'profile_retry') or len(raw) != phone_profiles.UPLOAD_BYTES
                    or self.profile_attempts >= 3 or not phone_profiles.available()):
                raise PermissionError('This attempt cannot accept recognition samples.')
            self.profile_attempts += 1
            self.phase = 'processing_profiles'
            threading.Thread(target=self.process_media, args=(raw,), daemon=True, name='LYA-Phone-Profiles').start()
            return {'processing': True}

    def process_media(self, raw):
        try:
            deadline = time.monotonic() + max(0, self.deadline - self.clock())
            vectors = store.checked_owner_profiles(phone_profiles.process(raw, deadline))
        except Exception:
            vectors = None
        finally:
            raw[:] = b'\0' * len(raw)
        with self.lock:
            if self.done.is_set() or self.clock() >= self.deadline:
                return
            self.profile_vectors = vectors
            self.phase = ('review_profiles' if vectors is not None else
                          'profile_retry' if self.profile_attempts < 3 else 'profile_failed')

    def finish_registration(self, data):
        with self.lock:
            self._check_live()
            skip = data.get('skip')
            keep = self.phase == 'review_profiles' and skip is False and self.profile_vectors is not None
            if not keep and not (skip is True and self.phase in ('profiles', 'profile_retry', 'profile_failed', 'review_profiles')):
                raise PermissionError('Only an explicit review or skip can complete enrollment.')
            try:
                pid = store.register_passkey_owner(
                    self.name, websafe_encode(bytes(self.credential)), websafe_encode(self.user_handle),
                    self.confirmed_counter, self.backup_eligible, self.db_path, phone_gate=self.phone_gate,
                    phone_profiles=self.profile_vectors if keep else None, still_current=self._check_live)
                self._check_live()
                self.result = Session('admin', self.name, secrets.token_urlsafe(24), pid, time.time() + 300)
                self.done.set()
                return {'verified': True}
            except Exception:
                self.cancel()
                raise
            finally:
                self.profile_vectors = None

    @staticmethod
    def _check_client(client):
        if client.cross_origin is not False or json.loads(bytes(client)).get('topOrigin') is not None:
            raise ValueError('Cross-origin credential requests are not allowed.')

    @staticmethod
    def _check_flags(data):
        if data.flags & data.FLAG.BS and not data.flags & data.FLAG.BE:
            raise ValueError('Inconsistent authenticator backup flags.')

    def close(self):
        with self.lock:
            if self._closed:
                return
            self._closed = True
            self.expiry.cancel()
            if not self.done.is_set():
                self.error = 'Verification cancelled.'
                self.done.set()
            self.state = None
            self.token = ''
            self.pairing_code = ''
            self.phone_gate = None
            self.profile_vectors = None
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=1)

    def cancel(self):
        with self.lock:
            if not self.done.is_set():
                self.error = 'Phone verification cancelled. Access stays locked.'
                self.done.set()
                self.state = None
                self.pairing_code = ''
                self.phone_gate = None
                self.profile_vectors = None

    def _handler(self):
        ceremony = self
        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(2)

            def log_message(self, *_):
                pass  # No credential IDs, capability tokens, proofs or private parameters in logs.

            def send(self, code, body, mime='application/json'):
                data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; "
                    f"script-src 'nonce-{ceremony.script_nonce}'; connect-src 'self'; "
                    + ("media-src 'self' blob:; " if ceremony.direct else "")
                    + "worker-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
                camera = '(self)' if ceremony.direct else '()'
                self.send_header('Permissions-Policy', f'camera={camera}, microphone={camera}')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(data)
                self.close_connection = True

            def valid_host(self):
                return self.headers.get('Host') == ceremony.host

            def do_GET(self):
                if not self.valid_host():
                    self.send(404, {})
                    return
                if ceremony.direct and self.path == '/owner-push.js':
                    script = Path(__file__).with_name('owner_push.js').read_text(encoding='utf-8')
                    self.send(200,script,'text/javascript; charset=utf-8')
                    return
                if ceremony.direct and self.path == '/owner.webmanifest':
                    self.send(200,dict(id='/owner', name='LYA Owner', short_name='LYA Owner',
                                       start_url='/', display='standalone'), 'application/manifest+json')
                    return
                if self.path != '/':
                    self.send(404, {})
                    return
                page = Path(__file__).with_name('phone_gate.html').read_text(encoding='utf-8') if ceremony.direct else PAGE
                self.send(200, page.replace('__NONCE__', ceremony.script_nonce), 'text/html; charset=utf-8')

            def do_POST(self):
                token = self.headers.get('X-LYA-Ceremony', '')
                media = ceremony.direct and self.path == '/profiles'
                claim = ceremony.notification_setup and self.path == '/push/claim'
                content = 'application/octet-stream' if media else 'application/json'
                if (not self.valid_host() or self.headers.get('Origin') != ceremony.origin
                        or not claim and (not token or not token.isascii() or not secrets.compare_digest(token, ceremony.token))
                        or self.headers.get('Content-Type') != content
                        or self.headers.get('Transfer-Encoding') is not None
                        or self.path not in ('/options', '/complete', '/cancel', '/details', '/profiles', '/finish',
                                             '/push/claim', '/push/subscribe')):
                    # Drain only a bounded declared body so Windows can deliver the rejection.
                    declared = self.headers.get('Content-Length', '')
                    if len(declared) <= 5 and declared.isascii() and declared.isdigit() and int(declared) <= 65536:
                        try:
                            self.rfile.read(int(declared))
                        except OSError:
                            pass
                    self.send(403, {})
                    return
                length = self.headers.get('Content-Length', '')
                if media:
                    if length != str(phone_profiles.UPLOAD_BYTES) or ceremony.phase not in ('profiles', 'profile_retry'):
                        self.send(403, {})
                        return
                    try:
                        deadline = min(ceremony.deadline, ceremony.clock() + 12)
                        raw = bytearray()
                        while len(raw) < phone_profiles.UPLOAD_BYTES:
                            if ceremony.done.is_set() or ceremony.clock() >= deadline:
                                raise PermissionError('Profile upload expired.')
                            chunk = self.rfile.read1(min(65536, phone_profiles.UPLOAD_BYTES - len(raw)))
                            if not chunk:
                                raise ValueError('Incomplete samples.')
                            raw.extend(chunk)
                        self.send(200, ceremony.accept_media(raw))
                    except Exception:
                        self.send(400, {})
                    return
                if len(length) > 5 or not length.isascii() or not length.isdigit() or not 0 < int(length) <= 65536:
                    self.send(413, {})
                    return
                try:
                    raw = self.rfile.read(int(length))
                    if len(raw) != int(length):
                        raise ValueError('Incomplete request.')
                    data = json.loads(raw)
                    if type(data) is not dict:
                        raise ValueError('Object required.')
                    if self.path == '/cancel':
                        ceremony.cancel()
                        result = {'cancelled': True}
                    elif self.path == '/details':
                        result = ceremony.submit_details(data)
                    elif self.path == '/finish':
                        result = ceremony.finish_registration(data)
                    elif self.path == '/push/claim':
                        result = ceremony.claim_setup_code(data.get('code'))
                    elif self.path == '/push/subscribe':
                        result = ceremony.subscribe(data)
                    else:
                        result = ceremony.options_json() if self.path == '/options' else ceremony.complete(data)
                    self.send(200, result)
                except Exception:
                    self.send(400, {})
        return Handler
