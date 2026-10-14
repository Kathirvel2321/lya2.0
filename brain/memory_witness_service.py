"""FAKE-DATA loopback witness protocol; not an authority adapter or deployed service."""
from dataclasses import asdict
import hashlib
import hmac
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import secrets
import sqlite3
import time

from brain.memory_custody import SyntheticWitness
from brain.memory_prototype import Conflict,_id,_json
from brain.memory_recovery import _integer,_unique

MAX_BODY = 8192
MAX_RECEIPTS = 1024
MAX_NONCES = 2048
MAX_DATABASE_BYTES = 4 * 1024 * 1024
WINDOW = 30
REQUEST_DOMAIN = b'LYA-fake-witness-request-v1\0POST /witness\0'
REPLY_DOMAIN = b'LYA-fake-witness-reply-v1\0'


def _key(key):
    if type(key) is not bytes or len(key)!=32:raise ValueError('Independent generated 32-byte protocol key required.')
    return key


def _load(raw):
    if type(raw) is not bytes or len(raw)>MAX_BODY:raise ValueError('Invalid bounded protocol body.')
    data = json.loads(raw,object_pairs_hook=_unique)
    if type(data) is not dict:raise ValueError('Protocol object required.')
    return data


def _sign(data,key,domain):
    return dict(data,mac=hmac.new(key,domain+_json(data).encode(),hashlib.sha256).hexdigest())


def _verify(data,key,domain,fields):
    if set(data)!=set(fields)|{'mac'}:raise ValueError('Unexpected protocol fields.')
    unsigned = {name:value for name,value in data.items() if name!='mac'}
    if not hmac.compare_digest(_id(data['mac'],64),_sign(unsigned,key,domain)['mac']):
        raise PermissionError('Protocol authentication failed.')
    if type(data['version']) is not int or data['version']!=1:raise ValueError('Wrong protocol version.')
    return unsigned


def _storage_limit(db):
    page_size = _integer(db.execute('PRAGMA page_size').fetchone()[0],1)
    pages = MAX_DATABASE_BYTES // page_size
    if pages<1 or db.execute(f'PRAGMA max_page_count={pages}').fetchone()[0]>pages:
        raise OSError('Witness database exceeds its storage budget.')


class SyntheticWitnessEndpoint:
    """One configured service/client/lineage, with durable non-expiring reservations."""
    def __init__(self,witness,*,service,client,lineage,key,synthetic_only=False,clock=time.time):
        if synthetic_only is not True:raise PermissionError('Explicit fake-data endpoint opt-in required.')
        if type(witness) is not SyntheticWitness:raise ValueError('Existing synthetic witness required.')
        self.witness,self.service,self.client,self.lineage = witness,_id(service),_id(client),_id(lineage)
        self._key,self.clock = _key(key),clock
        with witness._db() as db:self._schema(db)

    @classmethod
    def enable(cls,witness,*,service,client,lineage,key,synthetic_only=False,approved=False,clock=time.time):
        if synthetic_only is not True or approved is not True:raise PermissionError('Explicit fake-data setup approval required.')
        if type(witness) is not SyntheticWitness:raise ValueError('Existing synthetic witness required.')
        _id(service);_id(client);_id(lineage);_key(key)
        with witness._db() as db:
            _storage_limit(db)
            witness._head(db,lineage)
            if db.execute("SELECT 1 FROM sqlite_master WHERE name GLOB 'rpc_*'").fetchone():
                raise Conflict('Protocol state already exists; never silently reset it.')
            db.execute('CREATE TABLE rpc_meta(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER,service TEXT,client TEXT,lineage TEXT,key_sha256 TEXT,generation INTEGER)')
            db.execute('INSERT INTO rpc_meta VALUES(1,1,?,?,?,?,0)',(service,client,lineage,hashlib.sha256(key).hexdigest()))
            db.execute('CREATE TABLE rpc_nonces(nonce TEXT PRIMARY KEY,issued_at INTEGER NOT NULL)')
            db.execute('CREATE TABLE rpc_receipts(request_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,result TEXT NOT NULL)')
            db.execute('CREATE TABLE rpc_reservation(id INTEGER PRIMARY KEY CHECK(id=1),operation TEXT NOT NULL,generation INTEGER NOT NULL,previous TEXT NOT NULL,digest TEXT NOT NULL)')
        return cls(witness,service=service,client=client,lineage=lineage,key=key,synthetic_only=True,clock=clock)

    def _schema(self,db):
        _storage_limit(db)
        rows = db.execute('SELECT id,version,service,client,lineage,key_sha256,generation FROM rpc_meta').fetchall()
        version = rows[0][1] if len(rows)==1 else None
        if version not in (1,2) or tuple(rows[0][:6])!=(1,version,self.service,self.client,self.lineage,hashlib.sha256(self._key).hexdigest()):
            raise ValueError('Wrong pinned protocol identity or key.')
        generation = _integer(rows[0][6])
        db.execute('SELECT nonce,issued_at FROM rpc_nonces LIMIT 0')
        db.execute('SELECT request_id,fingerprint,result FROM rpc_receipts LIMIT 0')
        db.execute('SELECT id,operation,generation,previous,digest FROM rpc_reservation LIMIT 0')
        columns = [row[1] for row in db.execute('PRAGMA table_info(rpc_receipts)')]
        if columns!=['request_id','fingerprint','result']+(['generation'] if version==2 else []):
            raise ValueError('Wrong receipt schema; never downgrade retirement state.')
        if version==2:
            floor = self._floor(db)
            if floor>generation:raise ValueError('Retirement floor exceeds the witness generation.')
            if db.execute('SELECT 1 FROM rpc_receipts WHERE generation<=? OR generation>? LIMIT 1',(floor,generation)).fetchone():
                raise ValueError('Receipt generation differs from the retirement journal.')
            if db.execute('SELECT 1 FROM rpc_reservation WHERE generation<=?',(floor,)).fetchone():
                raise ValueError('A retired generation cannot remain reserved.')
        elif db.execute("SELECT 1 FROM sqlite_master WHERE name='rpc_retirement'").fetchone():
            raise ValueError('Retirement state cannot be downgraded.')
        return version

    @staticmethod
    def _floor(db):
        rows = db.execute('SELECT id,retired_generation FROM rpc_retirement').fetchall()
        if len(rows)!=1 or rows[0][0]!=1:raise ValueError('Missing retirement floor; never recreate it.')
        return _integer(rows[0][1])

    def enable_retirement(self,*,approved=False):
        """Explicit fresh-store opt-in; no migration of existing receipt history."""
        if approved is not True:raise PermissionError('Explicit fake-data retirement setup approval required.')
        with self.witness._db() as db:
            if self._schema(db)!=1:raise Conflict('Retirement already enabled; never reset its floor.')
            head = self._head(db)
            if head['generation']!=0 or head['reservation_id'] is not None or db.execute('SELECT 1 FROM rpc_receipts').fetchone():
                raise Conflict('Retirement setup requires a fresh unused protocol store.')
            db.execute('ALTER TABLE rpc_receipts ADD COLUMN generation INTEGER NOT NULL DEFAULT 0')
            db.execute('CREATE TABLE rpc_retirement(id INTEGER PRIMARY KEY CHECK(id=1),retired_generation INTEGER NOT NULL CHECK(retired_generation>=0))')
            db.execute('INSERT INTO rpc_retirement VALUES(1,0)')
            db.execute('UPDATE rpc_meta SET version=2 WHERE id=1')
        return self.capacity()

    def _generation_gate(self,db,operation):
        if type(operation) is not dict:raise ValueError('Operation required.')
        op = operation.get('op');floor = self._floor(db)
        if op=='prepare':
            generation = _integer(_integer(operation['expected_generation'])+1,1)
            if generation<=floor:raise Conflict('Prepare belongs to a retired generation.')
        elif op=='finish':
            if _integer(operation['generation'],1)<=floor:raise Conflict('Finish belongs to a retired generation.')
        elif op not in ('observe','retire'):raise ValueError('Retiring stores require observations and generation-scoped mutations.')

    def _head(self,db):
        state,digest = self.witness._head(db,self.lineage)
        reservation = db.execute('SELECT operation,generation FROM rpc_reservation WHERE id=1').fetchone()
        generation = _integer(db.execute('SELECT generation FROM rpc_meta WHERE id=1').fetchone()[0])
        if reservation and _integer(reservation[1])!=generation:raise ValueError('Reservation generation differs.')
        return dict(state=asdict(state),keys_digest=digest,reservation_id=_id(reservation[0]) if reservation else None,generation=generation)

    def capacity(self):
        """Local operator counters only; no keys, records or promise of disk availability."""
        with self.witness._db() as db:
            version = self._schema(db);now = _integer(int(self.clock()))
            receipts = db.execute('SELECT count(*) FROM rpc_receipts').fetchone()[0]
            nonces = db.execute('SELECT count(*) FROM rpc_nonces WHERE issued_at>=?',(now-WINDOW,)).fetchone()[0]
            result = dict(receipts=receipts,receipt_limit=MAX_RECEIPTS,live_nonces=nonces,nonce_limit=MAX_NONCES,
                reservation_pending=db.execute('SELECT 1 FROM rpc_reservation').fetchone() is not None,
                prepare_receipt_capacity=receipts+2<=MAX_RECEIPTS,
                database_bytes=db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0],
                database_limit_bytes=MAX_DATABASE_BYTES,synthetic_only=True)
            if version==2:result['retired_generation'] = self._floor(db)
            return result

    def _operation(self,db,operation,request_id):
        if type(operation) is not dict:raise ValueError('Operation required.')
        op = operation.get('op');head = self._head(db)
        if op=='retire' and set(operation)=={'op','state','keys_digest','generation'}:
            if self._schema(db)!=2:raise ValueError('Explicit retirement mode required.')
            state = self.witness._state(self.witness._decode(_json(operation['state']),self.lineage))
            generation = _integer(operation['generation']);digest = _id(operation['keys_digest'],64)
            if head!=dict(state=asdict(state),keys_digest=digest,reservation_id=None,generation=generation):
                raise Conflict('Retirement requires the exact completed witness generation.')
            if generation<self._floor(db):raise Conflict('Retirement cannot move backwards.')
            db.execute('UPDATE rpc_retirement SET retired_generation=? WHERE id=1',(generation,))
            db.execute('DELETE FROM rpc_receipts WHERE generation<=?',(generation,))
            return dict(head,retired_generation=generation)
        if op=='head' and set(operation)=={'op'}:return head
        if op=='observe' and set(operation) in ({'op'},{'op','prepare_capacity'}):
            if 'prepare_capacity' in operation:
                if operation['prepare_capacity'] is not True:raise ValueError('Exact capacity request required.')
                if db.execute('SELECT count(*) FROM rpc_receipts').fetchone()[0]+2>MAX_RECEIPTS:
                    raise OSError('Insufficient prepare and finish receipt capacity.')
            return head
        if op=='prepare' and set(operation) in ({'op','previous','keys_digest'},{'op','previous','keys_digest','expected_generation'}):
            previous = self.witness._decode(_json(operation['previous']),self.lineage)
            if head['state']!=asdict(previous) or head['keys_digest']!=_id(operation['keys_digest'],64):
                raise Conflict('Prepare does not match the trusted head.')
            if 'expected_generation' in operation and _integer(operation['expected_generation'])!=head['generation']:
                raise Conflict('Prepare generation changed.')
            if head['reservation_id'] is not None:raise Conflict('A transition is already reserved.')
            generation = _integer(head['generation']+1)
            db.execute('UPDATE rpc_meta SET generation=? WHERE id=1',(generation,))
            db.execute('INSERT INTO rpc_reservation VALUES(1,?,?,?,?)',
                       (request_id,generation,_json(asdict(previous)),operation['keys_digest']))
            return self._head(db)
        if op=='finish' and set(operation)=={'op','reservation_id','generation','previous','state','keys_digest'}:
            reservation = db.execute('SELECT operation,generation,previous,digest FROM rpc_reservation WHERE id=1').fetchone()
            previous = self.witness._decode(_json(operation['previous']),self.lineage)
            target = self.witness._decode(_json(operation['state']),self.lineage)
            expected = (_id(operation['reservation_id']),_integer(operation['generation'],1),
                        _json(asdict(previous)),_id(operation['keys_digest'],64))
            if not reservation or tuple(reservation)!=expected:raise Conflict('Reservation changed or is unavailable.')
            self.witness._advance(db,previous,target,operation['keys_digest'])
            db.execute('DELETE FROM rpc_reservation WHERE id=1')
            return self._head(db)
        raise ValueError('Unsupported operation or fields.')

    def exchange(self,raw):
        """Authenticate before state access; errors contain no request data or exception text."""
        try:
            request = _verify(_load(raw),self._key,REQUEST_DOMAIN,
                {'version','service','client','nonce','issued_at','request_id','operation'})
            _id(request['nonce']);_id(request['request_id']);_integer(request['issued_at'])
            if request['service']!=self.service or request['client']!=self.client:
                raise PermissionError('Wrong audience or client.')
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError,PermissionError):
            return 401,b'{"error":"rejected"}'
        status,result = 200,None
        try:
            now = _integer(int(self.clock()))
            if abs(now-request['issued_at'])>WINDOW:raise PermissionError('Stale request.')
            fingerprint = hashlib.sha256(_json(request['operation']).encode()).hexdigest()
            with self.witness._db() as db:
                version = self._schema(db)
                if version==2:self._generation_gate(db,request['operation'])
                if db.execute('SELECT 1 FROM rpc_nonces WHERE nonce=?',(request['nonce'],)).fetchone():
                    raise Conflict('Replayed transport nonce.')
                db.execute('DELETE FROM rpc_nonces WHERE issued_at<?',(now-WINDOW,))
                if db.execute('SELECT count(*) FROM rpc_nonces').fetchone()[0]>=MAX_NONCES:raise OSError('Nonce budget exhausted.')
                db.execute('INSERT INTO rpc_nonces VALUES(?,?)',(request['nonce'],request['issued_at']))
                fields = 'fingerprint,result,generation' if version==2 else 'fingerprint,result'
                prior = db.execute('SELECT '+fields+' FROM rpc_receipts WHERE request_id=?',(request['request_id'],)).fetchone()
                if prior:
                    if prior[0]!=fingerprint:raise Conflict('Request ID changed meaning.')
                    result = json.loads(prior[1],object_pairs_hook=_unique)
                    if version==2 and _integer(prior[2],1)!=result['generation']:raise ValueError('Receipt generation mismatch.')
                    if result!=self._head(db):raise Conflict('Receipt is no longer the current state; refresh explicitly.')
                else:
                    observing = type(request['operation']) is dict and request['operation'].get('op') in ('observe','retire')
                    if not observing:
                        count = db.execute('SELECT count(*) FROM rpc_receipts').fetchone()[0]
                        pending = db.execute('SELECT 1 FROM rpc_reservation').fetchone() is not None
                        op = request['operation'].get('op') if type(request['operation']) is dict else None
                        # Keep one receipt slot for finishing the sole durable reservation.
                        needed = 2 if op=='prepare' or (pending and op!='finish') else 1
                        if count+needed>MAX_RECEIPTS:raise OSError('Receipt budget exhausted.')
                    result = self._operation(db,request['operation'],request['request_id'])
                    if not observing:
                        values = (request['request_id'],fingerprint,_json(result))
                        if version==2:db.execute('INSERT INTO rpc_receipts VALUES(?,?,?,?)',(*values,result['generation']))
                        else:db.execute('INSERT INTO rpc_receipts VALUES(?,?,?)',values)
                if abs(int(self.clock())-request['issued_at'])>WINDOW:raise PermissionError('Request expired during operation.')
        except PermissionError:status,result = 401,{'error':'rejected'}
        except Conflict:status,result = 409,{'error':'conflict'}
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):status,result = 400,{'error':'invalid'}
        except (OSError,sqlite3.DatabaseError):status,result = 503,{'error':'unavailable'}
        reply = dict(version=1,service=self.service,client=self.client,nonce=request['nonce'],
                     request_id=request['request_id'],request_sha256=hashlib.sha256(raw).hexdigest(),status=status,result=result)
        return status,_json(_sign(reply,self._key,REPLY_DOMAIN)).encode()


class WitnessHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(2)

    def log_message(self,*args):pass

    def send(self,status,body=b'{"error":"rejected"}'):
        self.close_connection = True
        self.send_response_only(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('Connection','close')
        self.end_headers();self.wfile.write(body)

    def do_GET(self):self.send(405)

    def do_POST(self):
        lengths = self.headers.get_all('Content-Length',[])
        if (self.path!='/witness' or self.headers.get_all('Content-Type')!=['application/json']
                or self.headers.get('Transfer-Encoding') is not None or len(lengths)!=1
                or len(lengths[0])>4 or not lengths[0].isascii() or not lengths[0].isdecimal()
                or not 0<int(lengths[0])<=MAX_BODY):
            self.send(400);return
        try:
            body = self.rfile.read(int(lengths[0]))
            if len(body)!=int(lengths[0]):self.send(400);return
            status,reply = self.server.endpoint.exchange(body)
            self.send(status,reply)
        except (OSError,TimeoutError):self.close_connection = True


def loopback_server(endpoint,*,synthetic_only=False):
    if synthetic_only is not True or type(endpoint) is not SyntheticWitnessEndpoint:
        raise PermissionError('Explicit fake-data loopback server required.')
    # shortcut: bounded single-request lab server; qualify TLS, admission and service lifecycle before remote use.
    server = HTTPServer(('127.0.0.1',0),WitnessHandler);server.endpoint = endpoint
    return server


class SyntheticWitnessClient:
    def __init__(self,port,*,service,client,lineage,key,synthetic_only=False,clock=time.time):
        if synthetic_only is not True:raise PermissionError('Explicit fake-data client opt-in required.')
        if type(port) is not int or not 1<=port<=65535:raise ValueError('Loopback port required.')
        self.port,self.service,self.client,self.lineage = port,_id(service),_id(client),_id(lineage)
        self._key,self.clock = _key(key),clock

    def _packet(self,operation,request_id):
        return _sign(dict(version=1,service=self.service,client=self.client,nonce=secrets.token_hex(16),
            issued_at=_integer(int(self.clock())),request_id=_id(request_id),operation=operation),self._key,REQUEST_DOMAIN)

    def _reply(self,raw,status,request):
        reply = _verify(_load(raw),self._key,REPLY_DOMAIN,
            {'version','service','client','nonce','request_id','request_sha256','status','result'})
        sent = _load(request)
        if (reply['service']!=self.service or reply['client']!=self.client or reply['nonce']!=sent['nonce']
                or reply['request_id']!=sent['request_id'] or reply['request_sha256']!=hashlib.sha256(request).hexdigest()
                or type(reply['status']) is not int or reply['status']!=status):raise PermissionError('Reply does not match this request.')
        if status==401:raise PermissionError('Witness rejected authentication.')
        if status==409:raise Conflict('Witness state or request changed; inspect before retry.')
        if status==503:raise OSError('Witness unavailable; outcome may require reconciliation.')
        if status!=200:raise ValueError('Witness rejected the request.')
        result = reply['result']
        retiring = type(sent['operation']) is dict and sent['operation'].get('op')=='retire'
        fields = {'state','keys_digest','reservation_id','generation'}|({'retired_generation'} if retiring else set())
        if type(result) is not dict or set(result)!=fields:
            raise ValueError('Malformed witness reply.')
        result['state'] = SyntheticWitness._decode(_json(result['state']),self.lineage)
        _id(result['keys_digest'],64);_integer(result['generation'])
        if result['reservation_id'] is not None:_id(result['reservation_id'])
        if retiring and (result['reservation_id'] is not None or _integer(result['retired_generation'])!=result['generation']
                         or result['retired_generation']!=sent['operation']['generation']):
            raise ValueError('Retirement confirmation differs from the requested generation.')
        return result

    def request(self,operation,*,request_id=None):
        raw = _json(self._packet(operation,request_id if request_id is not None else secrets.token_hex(16))).encode()
        if len(raw)>MAX_BODY:raise ValueError('Protocol body too large.')
        connection = HTTPConnection('127.0.0.1',self.port,timeout=2)
        try:
            connection.request('POST','/witness',body=raw,headers={'Content-Type':'application/json'})
            reply = connection.getresponse()
            if reply.getheader('Content-Type')!='application/json':raise ValueError('Wrong reply type.')
            data = reply.read(MAX_BODY+1)
            return self._reply(data,reply.status,raw)
        finally:connection.close()

    def head(self):return self.request({'op':'head'})

    def observe(self,*,require_prepare_capacity=False):
        if type(require_prepare_capacity) is not bool:raise ValueError('Exact capacity flag required.')
        operation = {'op':'observe'}
        if require_prepare_capacity:operation['prepare_capacity'] = True
        return self.request(operation)

    def prepare(self,previous,keys_digest,*,request_id,expected_generation=None):
        SyntheticWitness._state(previous);_id(keys_digest,64)
        operation = dict(op='prepare',previous=asdict(previous),keys_digest=keys_digest)
        if expected_generation is not None:operation['expected_generation'] = _integer(expected_generation)
        return self.request(operation,request_id=request_id)

    def finish(self,reservation,previous,state,keys_digest,*,request_id):
        SyntheticWitness._state(previous);SyntheticWitness._state(state);_id(keys_digest,64)
        return self.request(dict(op='finish',reservation_id=reservation['reservation_id'],generation=reservation['generation'],
            previous=asdict(previous),state=asdict(state),keys_digest=keys_digest),request_id=request_id)

    def retire(self,state,keys_digest,*,generation):
        SyntheticWitness._state(state);_id(keys_digest,64);_integer(generation)
        return self.request(dict(op='retire',state=asdict(state),keys_digest=keys_digest,generation=generation))
