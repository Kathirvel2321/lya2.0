"""Private HTTPS proxy target: paired public conversation with opt-in research, no private vault.

Run behind Tailscale Serve on loopback. Public authentication metadata is protected
by filesystem permissions; conversation/audio/biometrics are never persisted here.
"""
from contextlib import contextmanager
import hashlib
import base64
import io
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
import wave
from urllib.parse import urlsplit
from cloud.answering import messages_for, completed_history, needs_current_sources
from cloud.web_research import research_mode, synthesis_prompt, render_research

from fido2.server import Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import AttestedCredentialData, AuthenticationResponse, RegistrationResponse, PublicKeyCredentialRpEntity

MAX_BODY=24000
MAX_AUDIO=120*32000+44
COOKIE='__Host-lya'


def checked_origin(origin):
    if type(origin) is not str or not re.fullmatch(r'https://[a-z0-9-]+\.[a-z0-9-]+\.ts\.net',origin):
        raise ValueError('Configure the exact private Tailscale HTTPS origin.')
    return origin


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class AuthStore:
    def __init__(self,path):
        self.path=Path(path)
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ValueError('Authentication storage cannot be a link.')
        self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS invite (id INTEGER PRIMARY KEY CHECK(id=1), hash TEXT, until REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS credential (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT, handle TEXT, counter INTEGER, eligible INTEGER, stamp TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS speech_usage (id INTEGER PRIMARY KEY CHECK(id=1), day TEXT, calls INTEGER)')
        if os.name!='nt':
            self.path.chmod(0o600)
            if self.path.parent.stat().st_mode & 0o077:
                raise PermissionError('Authentication directory must be private.')

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=3)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:db.close()

    def credential(self):
        with self.db() as db:
            row=db.execute('SELECT data,handle,counter,eligible,stamp FROM credential WHERE id=1').fetchone()
            return dict(zip(('data','handle','counter','eligible','stamp'),row)) if row else None

    def reserve_speech(self,now):
        day=time.strftime('%Y-%m-%d',time.gmtime(now))
        with self.db() as db:
            row=db.execute('SELECT day,calls FROM speech_usage WHERE id=1').fetchone()
            calls=row[1] if row and row[0]==day else 0
            if calls>=100:raise PermissionError('Daily speech limit reached. Use text.')
            db.execute('INSERT OR REPLACE INTO speech_usage VALUES(1,?,?)',(day,calls+1))

    def control(self,op,binding,now):
        if op not in ('invite','revoke') or type(binding) is not str or not re.fullmatch('[a-f0-9]{64}',binding):
            raise ValueError('Invalid connection control operation.')
        with self.db() as db:
            row=db.execute('SELECT owner FROM binding WHERE id=1').fetchone()
            if row and row[0]!=binding:raise PermissionError('Owner binding changed; trusted review required.')
            db.execute('INSERT OR IGNORE INTO binding VALUES(1,?)',(binding,))
            if op=='revoke':
                db.execute('DELETE FROM credential');db.execute('DELETE FROM invite')
                return {'revoked':True}
            if db.execute('SELECT 1 FROM credential').fetchone():return {'paired':True}
            token=secrets.token_urlsafe(32)
            db.execute('INSERT OR REPLACE INTO invite VALUES(1,?,?)',(digest(token),now+180))
            return {'token':token}

    def invited(self,token,now):
        if type(token) is not str or not re.fullmatch('[A-Za-z0-9_-]{43}',token):return False
        with self.db() as db:
            row=db.execute('SELECT hash,until FROM invite WHERE id=1').fetchone()
            return bool(row and now<row[1] and secrets.compare_digest(row[0],digest(token))
                        and not db.execute('SELECT 1 FROM credential').fetchone())

    def commit(self,token,record,now):
        with self.db() as db:
            row=db.execute('SELECT hash,until FROM invite WHERE id=1').fetchone()
            if (not row or now>=row[1] or not secrets.compare_digest(row[0],digest(token))
                    or db.execute('SELECT 1 FROM credential').fetchone()):
                raise PermissionError('Pairing expired or already used.')
            stamp=secrets.token_hex(16)
            db.execute('INSERT INTO credential VALUES(1,?,?,?,?,?)',
                       (record['data'],record['handle'],record['counter'],record['eligible'],stamp))
            db.execute('DELETE FROM invite')
            return stamp

    def accept(self,record,counter,eligible):
        with self.db() as db:
            row=db.execute('SELECT data,counter,eligible,stamp FROM credential WHERE id=1').fetchone()
            if (not row or row[0]!=record['data'] or row[3]!=record['stamp'] or eligible!=bool(row[2])
                    or ((row[1] or counter) and counter<=row[1])):
                raise PermissionError('Credential revoked, changed or replayed.')
            db.execute('UPDATE credential SET counter=? WHERE id=1',(counter,))


class Connection:
    def __init__(self,origin,store,infer,clock=time.time,transcribe=None,speak=None,researcher=None,shared_memory=None):
        self.origin=checked_origin(origin)
        self.store,self.infer,self.clock=store,infer,clock
        self.transcriber=transcribe
        self.researcher=researcher
        self.shared_memory=shared_memory
        self.speaker=speak
        self.audio_slots=threading.BoundedSemaphore(1)
        self.rp=urlsplit(origin).hostname
        self.server=Fido2Server(PublicKeyCredentialRpEntity(id=self.rp,name='LYA Connection'),
                               attestation='none',verify_origin=lambda value:value==self.origin)
        self.server.allowed_algorithms=[p for p in self.server.allowed_algorithms if p.alg==-7]
        self.server.timeout=120000
        self.lock=threading.RLock()
        self.infer_slots=threading.BoundedSemaphore(2)
        self.ceremonies,self.sessions={},{}
        self.starts=[]
        self.timings=threading.local()

    @contextmanager
    def measure(self,stage):
        started=time.perf_counter()
        try:yield
        finally:
            values=getattr(self.timings,'values',None)
            if values is not None:values[stage]=max(0,(time.perf_counter()-started)*1000)

    def begin(self,mode,token=None,session_token=None):
        with self.lock:
            now=self.clock()
            self.ceremonies={k:v for k,v in self.ceremonies.items() if now<v['until']}
            self.sessions={k:v for k,v in self.sessions.items() if now<v['until']}
            self.starts=[t for t in self.starts if now-t<60]
            if len(self.starts)>=20 or len(self.ceremonies)>=8:raise PermissionError('Wait before retrying.')
            self.starts.append(now)
            handle=secrets.token_bytes(32)
            record=self.store.credential()
            if mode=='owner':self.session(session_token)
            if mode=='pair' and self.store.invited(token,now):
                options,state=self.server.register_begin(dict(id=handle,name='LYA owner',displayName='LYA owner'),
                    resident_key_requirement='required',user_verification='required')
            elif mode in ('login','owner') and record:
                handle=websafe_decode(record['handle'])
                options,state=self.server.authenticate_begin([AttestedCredentialData(websafe_decode(record['data']))],
                                                              user_verification='required')
            else:raise PermissionError('Pair on the laptop first or sign in with the paired passkey.')
            ticket=secrets.token_urlsafe(32)
            self.ceremonies[ticket]=dict(mode=mode,token=token,handle=handle,record=record,state=state,until=now+120,
                                        session_token=session_token if mode=='owner' else None)
            return dict(ticket=ticket,phase='create' if mode=='pair' else 'get',**dict(options))

    def complete(self,ticket,response):
        with self.lock:
            c=self.ceremonies.pop(ticket,None)
            if not c or self.clock()>=c['until']:raise PermissionError('Passkey attempt expired; retry.')
            if c['mode']=='owner':self.session(c['session_token'])
            create=c['mode']=='pair'
            parsed=(RegistrationResponse if create else AuthenticationResponse).from_dict(response)
            client=parsed.response.client_data
            if client.cross_origin is not False or json.loads(bytes(client)).get('topOrigin') is not None:
                raise ValueError('Cross-origin proof is forbidden.')
            if create:
                auth=self.server.register_complete(c['state'],parsed)
                credential=auth.credential_data
                if (credential is None or credential.public_key.ALGORITHM!=-7 or not credential.credential_id
                        or parsed.raw_id!=credential.credential_id or len(bytes(credential))>8192):
                    raise ValueError('Invalid credential.')
                c['record']=dict(data=websafe_encode(bytes(credential)),handle=websafe_encode(c['handle']),
                                 counter=auth.counter,eligible=bool(auth.flags & auth.FLAG.BE))
                options,c['state']=self.server.authenticate_begin([credential],user_verification='required')
                c['mode']='confirm'
                self._flags(auth)
                self.ceremonies[ticket]=c
                return dict(ticket=ticket,phase='get',confirm=True,**dict(options)),None
            credential=AttestedCredentialData(websafe_decode(c['record']['data']))
            self.server.authenticate_complete(c['state'],[credential],parsed)
            auth=parsed.response.authenticator_data
            self._flags(auth)
            if parsed.response.user_handle is not None and parsed.response.user_handle!=c['handle']:
                raise ValueError('Wrong passkey user.')
            eligible=bool(auth.flags & auth.FLAG.BE)
            if c['mode']=='confirm':
                previous=c['record']['counter']
                if eligible!=c['record']['eligible'] or ((previous or auth.counter) and auth.counter<=previous):
                    raise ValueError('Invalid confirmation counter.')
                c['record']['counter']=auth.counter
                c['record']['stamp']=self.store.commit(c['token'],c['record'],self.clock())
            else:self.store.accept(c['record'],auth.counter,eligible)
            if c['mode']=='owner':
                s=self.session(c['session_token'])
                s['owner_until']=min(s['until'],self.clock()+300)
                return self.status(c['session_token']),None
            if len(self.sessions)>=8:
                oldest=next(iter(self.sessions));old=self.sessions.pop(oldest)
                if old['active']:old['active'][1].set()
            session=secrets.token_urlsafe(32)
            self.sessions[digest(session)]=dict(until=self.clock()+900,credential=c['record']['data'],stamp=c['record']['stamp'],active=None,
                                                history=[],used=set(),owner_until=0)
            return {'verified':True},session

    @staticmethod
    def _flags(auth):
        if auth.flags & auth.FLAG.BS and not auth.flags & auth.FLAG.BE:
            raise ValueError('Invalid passkey backup flags.')

    def session(self,token):
        if type(token) is not str or not re.fullmatch('[A-Za-z0-9_-]{43}',token):raise PermissionError('Sign in first.')
        s=self.sessions.get(digest(token))
        record=self.store.credential()
        if (not s or self.clock()>=s['until'] or not record or record['data']!=s['credential']
                or record['stamp']!=s['stamp']):
            self.sessions.pop(digest(token),None)
            raise PermissionError('Session expired or revoked; sign in again.')
        return s

    def status(self,token):
        with self.lock:
            s=self.session(token)
            result=dict(verified=True,expires_in=max(0,int(s['until']-self.clock())),
                        owner_verified=self.clock()<s['owner_until'],
                        owner_expires_in=max(0,int(s['owner_until']-self.clock())),
                        scope='public_chat',voice_available=self.transcriber is not None)
            if self.shared_memory is not None:result['shared_memory_demo']=True
            return result

    @contextmanager
    def audio_job(self):
        # One heavy audio worker at a time keeps the existing service memory cap.
        if not self.audio_slots.acquire(blocking=False):raise ValueError('Audio is busy.')
        try:yield
        finally:self.audio_slots.release()

    @contextmanager
    def job(self,token,request_id,*,shared_digest=None):
        if type(request_id) is not str or not re.fullmatch('[a-f0-9]{32}',request_id):
            raise ValueError('Invalid request ID.')
        with self.lock:
            s=self.session(token)
            retry=shared_digest is not None and s.get('shared_used',{}).get(request_id)==shared_digest
            if s['active'] or (request_id in s['used'] and not retry) or (len(s['used'])>=50 and not retry):
                raise PermissionError('Request already used, busy, or session limit reached. Sign in again if needed.')
            if not self.infer_slots.acquire(blocking=False):raise PermissionError('LYA is busy; try again shortly.')
            s['used'].add(request_id)
            if shared_digest is not None:s.setdefault('shared_used',{})[request_id]=shared_digest
            cancel=threading.Event();s['active']=(request_id,cancel)
        try:yield s,cancel
        finally:
            with self.lock:s['active']=None
            self.infer_slots.release()

    def transcribe(self,token,request_id,audio):
        if self.transcriber is None:raise ValueError('Phone hearing is not configured yet. Use text.')
        if type(audio) is not bytes or not 44<len(audio)<=MAX_AUDIO:raise ValueError('Invalid audio length.')
        try:
            with wave.open(io.BytesIO(audio),'rb') as sound:
                if (sound.getframerate(),sound.getnchannels(),sound.getsampwidth(),sound.getcomptype())!=(16000,1,2,'NONE'):
                    raise ValueError('Use mono 16 kHz PCM16.')
                frames=sound.getnframes()
                if not 1600<=frames<=120*16000 or len(sound.readframes(frames))!=frames*2:
                    raise ValueError('Use a complete recording of 0.1 to 120 seconds.')
        except (wave.Error,EOFError):raise ValueError('Invalid audio.') from None
        with self.job(token,request_id) as (s,cancel):
            with self.lock:
                self.session(token)
                if cancel.is_set():raise InterruptedError('Cancelled.')
                self.store.reserve_speech(self.clock())
            with self.measure('asr'):
                with self.audio_job():text=self.transcriber(audio,cancel)
            with self.lock:
                if self.session(token) is not s or cancel.is_set():raise InterruptedError('Cancelled.')
                if type(text) is not str or not 1<=len(text.strip())<=4000:raise ValueError('No clear transcript.')
                return {'text':text.strip(),'id':request_id}

    def stop(self,token,request_id):
        if type(request_id) is not str or not re.fullmatch('[a-f0-9]{32}',request_id):raise ValueError('Invalid request ID.')
        with self.lock:
            s=self.session(token)
            if s['active'] and s['active'][0]==request_id:s['active'][1].set()
            elif len(s['used'])<50:s['used'].add(request_id)

    def logout(self,token):
        with self.lock:
            s=self.session(token)
            if s['active']:s['active'][1].set()
            self.sessions.pop(digest(token))

    def chat(self,token,request_id,text,spoken=False):
        if (type(text) is not str or not 1<=len(text.strip())<=4000 or type(request_id) is not str
                or not re.fullmatch('[a-f0-9]{32}',request_id)):
            raise ValueError('Use a question of up to 4000 characters.')
        if type(spoken) is not bool:raise ValueError('Invalid voice request.')
        shared=re.match(r'^shared memory\b',text.strip(),re.I) is not None
        with self.job(token,request_id,shared_digest=digest(text) if shared else None) as (s,cancel):
            with self.lock:
                self.session(token)
                if cancel.is_set():raise InterruptedError('Cancelled.')
                if shared:s['history'].clear()
                system=('You are LYA. Give a direct, helpful answer. This is public conversation only. '
                'No tools, private memories, files, cameras or web search are connected to this phone route. '
                'Never claim you executed an action or saved a fact. Say clearly when a requested action is unavailable.')
                if self.researcher is not None:
                    system=system.replace('No tools, private memories, files, cameras or web search are connected to this phone route. ',
                        'Public web research is available for routed research requests. No new search was performed on this ordinary chat turn. '
                        'No private memories, files, cameras or device actions are connected. ')
                messages=[] if shared else messages_for(system,s['history'],text.strip())
            mode=None if shared else research_mode(text) or ('smart' if needs_current_sources(text) else None)
            if shared:
                if self.shared_memory is None:raise ValueError('Shared memory is not configured on this connection.')
                from brain.conversation import phone_turn
                turn=phone_turn(self,token,{'id':request_id,'text':text},cancel)
                shared_reply=self.shared_memory.respond(turn)
                answer=shared_reply['text']
            elif mode:
                if self.researcher is None:
                    raise ValueError('Current web research is not configured on this phone route; I cannot verify this answer.')
                def check():
                    with self.lock:
                        if self.session(token) is not s or cancel.is_set():raise InterruptedError('Cancelled.')
                with self.measure('research'):
                    report=self.researcher.investigate(text.strip(),mode=mode,
                        planner=lambda plan:self.infer(plan,cancel),check=check)
                check()
                messages=messages_for(synthesis_prompt(report.records,report),[],text.strip())
                with self.measure('inference'):raw=self.infer(messages,cancel)
                answer=render_research(raw,report)
            else:
                with self.measure('inference'):answer=self.infer(messages,cancel)
            if type(answer) is not str or not answer.strip() or len(answer)>8000:raise ValueError('No usable answer.')
            result={'text':answer,'id':request_id}
            if spoken:
                with self.lock:
                    if self.session(token) is not s or cancel.is_set():raise InterruptedError('Cancelled.')
                    if shared:turn.check()
                try:
                    if self.speaker is None:raise ValueError('LYA voice unavailable.')
                    with self.measure('tts'):
                        with self.audio_job():audio=self.speaker(answer,cancel)
                    if type(audio) is not str or len(audio)>10600000:raise ValueError('Oversize voice response.')
                    raw=base64.b64decode(audio,validate=True)
                    if not 44<len(raw)<=180*22050*2+44:raise ValueError('Invalid reply audio.')
                    with wave.open(io.BytesIO(raw),'rb') as wav:
                        if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth())!=(22050,1,2):raise ValueError('Invalid reply format.')
                        if len(wav.readframes(wav.getnframes()))!=wav.getnframes()*2:raise ValueError('Incomplete reply audio.')
                    result['audio']=audio
                except InterruptedError:raise
                except Exception:result['voice_unavailable']=True
            with self.lock:
                if self.session(token) is not s or cancel.is_set():raise InterruptedError('Cancelled.')
                if shared:
                    turn.check()
                    expiry=shared_reply.get('expires_at')
                    if expiry is not None and self.clock()>=expiry:raise PermissionError('Shared memory expired before delivery.')
                if type(answer) is not str or not answer.strip() or len(answer)>8000:raise ValueError('No usable answer.')
                if shared:s['history'].clear()
                else:s['history']=completed_history(s['history'],text.strip(),answer)
                return result


class PrivateHTTP(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,app):
        self.app=app
        self.slots=threading.BoundedSemaphore(8)
        super().__init__(address,Handler)

    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request);return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise

    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(5)

    def log_message(self,*_):pass

    def send(self,code,body,mime='application/json',cookie=None):
        nonce=secrets.token_urlsafe(20)
        if type(body) is str:
            body=body.replace('__NONCE__',nonce).encode()
        else:body=json.dumps(body).encode()
        self.send_response(code)
        if hasattr(self,'started'):
            values=getattr(self.server.app.timings,'values',{})
            values['request']=max(0,(time.perf_counter()-self.started)*1000)
            # Only fixed stage names and numbers leave the worker; no content or IDs.
            self.send_header('Server-Timing',', '.join(f'{stage};dur={values[stage]:.3f}'
                for stage in ('asr','research','inference','tts','request') if stage in values))
        for name,value in {'Content-Type':mime,'Content-Length':str(len(body)),
            'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff',
            'X-Frame-Options':'DENY','Permissions-Policy':'camera=(), microphone=(self)',
            'Content-Security-Policy':f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}.items():
            self.send_header(name,value)
        if cookie is not None:
            self.send_header('Set-Cookie',f'{COOKIE}={cookie}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age={900 if cookie else 0}')
        self.end_headers();self.wfile.write(body)

    def boundary(self,post=False):
        app=self.server.app
        if (self.headers.get_all('Host')!=[urlsplit(app.origin).netloc]
                or post and self.headers.get_all('Origin')!=[app.origin]):
            raise PermissionError('Wrong origin or host.')
        if self.headers.get('Sec-Fetch-Site') in ('cross-site','same-site'):
            raise PermissionError('Cross-site request forbidden.')

    def token(self):
        headers=self.headers.get_all('Cookie',[])
        if len(headers)!=1 or headers[0].count(COOKIE+'=')!=1:raise PermissionError('Sign in first.')
        cookie=SimpleCookie();cookie.load(headers[0])
        return cookie[COOKIE].value if COOKIE in cookie else None

    def do_GET(self):
        try:
            self.boundary()
            if self.path=='/':return self.send(200,Path(__file__).with_name('mobile.html').read_text(encoding='utf-8'),'text/html; charset=utf-8')
            if self.path=='/manifest.webmanifest':
                return self.send(200,dict(name='LYA',short_name='LYA',start_url='/',display='standalone',background_color='#091016',theme_color='#091016'),'application/manifest+json')
            self.send(404,{'error':'Not available.'})
        except (ValueError,PermissionError):self.send(403,{'error':'Private connection required.'})

    def do_POST(self):
        self.started=time.perf_counter()
        self.server.app.timings.values={}
        try:
            self.boundary(post=True)
            length=self.headers.get_all('Content-Length',[])
            audio=self.path=='/transcribe'
            if (self.headers.get('Transfer-Encoding') or len(length)!=1 or not length[0].isdigit()
                    or not 2<=int(length[0])<=(MAX_AUDIO if audio else MAX_BODY)
                    or self.headers.get_all('Content-Type')!=['audio/wav' if audio else 'application/json']):
                raise ValueError('Invalid request size or format.')
            if audio:
                token=self.token();self.server.app.status(token)
                ids=self.headers.get_all('X-LYA-Request',[])
                if len(ids)!=1:raise ValueError('Invalid request ID.')
            raw=self.rfile.read(int(length[0]))
            if len(raw)!=int(length[0]):raise ValueError('Incomplete request.')
            if audio:return self.send(200,self.server.app.transcribe(token,ids[0],raw))
            def unique(pairs):
                d={}
                for k,v in pairs:
                    if k in d:raise ValueError('Duplicate field.')
                    d[k]=v
                return d
            data=json.loads(raw,object_pairs_hook=unique)
            if type(data) is not dict:raise ValueError('Invalid request.')
            app=self.server.app
            if self.path=='/auth/begin' and set(data)<= {'mode','token'} and 'mode' in data:
                return self.send(200,app.begin(data['mode'],data.get('token'),self.token() if data['mode']=='owner' else None))
            if self.path=='/auth/complete' and set(data)=={'ticket','response'} and type(data['ticket']) is str:
                body,cookie=app.complete(data['ticket'],data['response']);return self.send(200,body,cookie=cookie)
            token=self.token()
            if self.path=='/session' and not data:return self.send(200,app.status(token))
            if self.path=='/chat' and {'id','text'}<=set(data)<= {'id','text','spoken'}:
                return self.send(200,app.chat(token,data['id'],data['text'],data.get('spoken',False)))
            if self.path=='/stop' and set(data)=={'id'} and type(data['id']) is str:
                app.stop(token,data['id']);return self.send(200,{'stopped':True})
            if self.path=='/logout' and not data:
                app.logout(token);return self.send(200,{'locked':True},cookie='')
            raise ValueError('Unknown operation or fields.')
        except InterruptedError:self.send(409,{'error':'Cancelled.'})
        except PermissionError:self.send(403,{'error':'Sign in or retry the approved pairing.'})
        except (ValueError,KeyError,TypeError,RecursionError,UnicodeError) as exc:
            if getattr(exc,'shared_memory_uncertain',False):self.send(503,{'error':str(exc)})
            else:self.send(400,{'error':'Request rejected; retry.'})
        except Exception:self.send(503,{'error':'Connection unavailable; no action was taken.'})
        finally:self.server.app.timings.values=None

