"""Finite FAKE-DATA B2 worker. Ciphertext/pins only; never an unlock key or timer."""
from dataclasses import asdict
import base64
import hashlib
import http.client
import json
from pathlib import Path
import re
import ssl
import time
from urllib.parse import quote,urlsplit

from brain.memory_custody import _approval
from brain.memory_prototype import Conflict,_json,_unlinked
from brain.memory_recovery import _publish,_unique
from brain.memory_recovery_pack import NAMES,MAX_PACK_BYTES,RecoveryPins,_paths

CAPABILITIES={'listBuckets','readFiles','writeFiles'}


class B2RequestRefused(ValueError):
    def __init__(self,status):
        self.status=status if type(status) is int and 100<=status<=599 else None
        super().__init__('B2 request refused; remote details withheld.')


def _token(value):
    if type(value) is not str or not re.fullmatch(r'[!-~]{1,4096}',value):
        raise ValueError('Invalid bounded service token.')
    return value


def _url(value,role):
    if type(value) is not str or len(value)>2048 or any(ord(c)<33 for c in value) or '\\' in value:
        raise ValueError('Invalid B2 destination.')
    try:
        u=urlsplit(value);port=u.port
    except ValueError:raise ValueError('Invalid B2 destination.') from None
    hosts={'api':r'api\d+\.backblazeb2\.com','download':r'f\d+\.backblazeb2\.com',
           'upload':r'pod-[a-z0-9-]+\.backblaze\.com'}
    if (u.scheme!='https' or u.username or u.password or port not in (None,443) or u.fragment
            or not re.fullmatch(hosts[role],u.hostname or '')):raise ValueError('Untrusted B2 destination.')
    if role!='upload' and (u.path not in ('','/') or u.query):raise ValueError('B2 origin required.')
    if role=='upload' and not re.fullmatch(r'/b2api/v[234]/b2_upload_file(?:/[a-zA-Z0-9_/-]+)?',u.path):
        raise ValueError('Unexpected B2 upload path.')
    return value.rstrip('/') if role!='upload' else value


class _B2:
    def __init__(self,cancelled):
        self.cancelled=cancelled;self.deadline=time.monotonic()+45;self.calls=0

    def check(self):
        if self.cancelled():raise InterruptedError('Backup cancelled.')
        if time.monotonic()>=self.deadline:raise TimeoutError('Backup worker deadline reached.')

    def request(self,method,url,*,limit=65536,missing=False,headers=None,data=None,metadata=None):
        self.check();self.calls+=1
        if self.calls>16:raise ValueError('Backup request budget exceeded.')
        u=urlsplit(url);headers=dict(headers or {})
        if metadata is not None:
            data=_json(metadata).encode();headers['Content-Type']='application/json'
        connection=http.client.HTTPSConnection(u.hostname,timeout=min(4,self.deadline-time.monotonic()),
                                               context=ssl.create_default_context())
        try:
            connection.request(method,u.path+('?' + u.query if u.query else ''),body=data,headers=headers)
            response=connection.getresponse();blob=bytearray()
            if response.getheader('Content-Encoding') not in (None,'identity'):
                raise ValueError('Encoded B2 responses are refused.')
            while True:
                self.check();chunk=response.read(min(8192,limit-len(blob)+1))
                if not chunk:break
                blob.extend(chunk)
                if len(blob)>limit:raise ValueError('B2 response byte budget exceeded.')
            self.check()
            if response.status==404 and missing:
                if self.decode(blob).get('code') in ('not_found','file_not_present'):return None
            if response.status!=200:raise B2RequestRefused(response.status)
            return bytes(blob)
        except InterruptedError:raise
        except TimeoutError:raise TimeoutError('Backup transport/deadline timed out.') from None
        except (OSError,http.client.HTTPException):
            raise OSError('B2 transport failed; service credentials/details withheld.') from None
        finally:connection.close()

    @staticmethod
    def decode(data):
        try:value=json.loads(data,object_pairs_hook=_unique)
        except (ValueError,UnicodeError):raise ValueError('Malformed B2 metadata.') from None
        if type(value) is not dict:raise ValueError('B2 metadata object required.')
        return value

    def authorize(self,key_id,key,bucket_id,bucket_name,prefix):
        basic=base64.b64encode((_token(key_id)+':'+_token(key)).encode()).decode()
        raw=self.request('GET','https://api.backblazeb2.com/b2api/v4/b2_authorize_account',
                         headers={'Authorization':'Basic '+basic})
        try:
            auth=self.decode(raw);storage=auth['apiInfo']['storageApi'];allowed=storage['allowed']
            caps=allowed['capabilities']
            if (type(caps) is not list or set(caps)!=CAPABILITIES or len(caps)!=len(CAPABILITIES)
                    or allowed['buckets']!=[{'id':bucket_id,'name':bucket_name}] or allowed['namePrefix']!=prefix):
                raise ValueError('One exact bucket/prefix and minimal service capabilities required.')
            expiry=auth['applicationKeyExpirationTimestamp']
            if type(expiry) is not int or not time.time()+60<=expiry/1000<=time.time()+86400:
                raise ValueError('Pilot service key must expire within one day, with at least one minute remaining.')
            self.api=_url(storage['apiUrl'],'api');self.download=_url(storage['downloadUrl'],'download')
            self.headers={'Authorization':_token(auth['authorizationToken'])}
            self.bucket_id=bucket_id;self.bucket_name=bucket_name
            data=self.call('b2_list_buckets',{'accountId':_token(auth['accountId']),'bucketId':bucket_id})
            buckets=data['buckets']
            if (type(buckets) is not list or len(buckets)!=1 or buckets[0]['bucketId']!=bucket_id
                    or buckets[0]['bucketName']!=bucket_name or buckets[0]['bucketType']!='allPrivate'):
                raise ValueError('Exact private destination required.')
        except (KeyError,TypeError):raise ValueError('Malformed B2 authorization/bucket metadata.') from None
        return expiry

    def call(self,name,data):
        return self.decode(self.request('POST',self.api+'/b2api/v4/'+name,headers=self.headers,metadata=data))

    def get(self,name,size):
        return self.request('GET',self.download+'/file/'+self.bucket_name+'/'+quote(name,safe='/'),
                            headers=self.headers,limit=max(1024,size),missing=True)

    def put(self,name,blob):
        # Fetch a scoped upload URL per file; a lost reply is reconciled by the next worker's reads.
        try:
            upload=self.call('b2_get_upload_url',{'bucketId':self.bucket_id})
            if upload['bucketId']!=self.bucket_id:raise ValueError('Upload destination changed.')
            url=_url(upload['uploadUrl'],'upload')
            headers={'Authorization':_token(upload['authorizationToken']),'X-Bz-File-Name':quote(name,safe='/'),
                'Content-Type':'application/octet-stream','X-Bz-Content-Sha1':hashlib.sha1(blob).hexdigest(),
                'X-Bz-Server-Side-Encryption':'AES256'}
            result=self.decode(self.request('POST',url,headers=headers,data=blob))
            if (result['bucketId']!=self.bucket_id or result['fileName']!=name
                    or type(result['contentLength']) is not int or result['contentLength']!=len(blob)
                    or result['contentSha1']!=headers['X-Bz-Content-Sha1']
                    or result['serverSideEncryption']!={'algorithm':'AES256','mode':'SSE-B2'}):
                raise ValueError('B2 upload acknowledgement differs from the requested artifact.')
        except (KeyError,TypeError):raise ValueError('Malformed B2 upload metadata.') from None


def backup_once(folder,receipt,*,pins,observe,key_id,key,bucket_id,bucket_name,prefix,
                synthetic_only=False,approved=False,cancelled=lambda:False):
    """Explicit single-worker invocation; independent fresh pins come from the trusted caller."""
    _approval(synthetic_only,approved,cancelled)
    if type(pins) is not RecoveryPins:raise ValueError('Independent recovery pins required.')
    pins.__post_init__()
    if (type(bucket_id) is not str or not re.fullmatch(r'[a-zA-Z0-9]{6,64}',bucket_id)
            or type(bucket_name) is not str or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]{4,61}[a-zA-Z0-9]',bucket_name)
            or type(prefix) is not str or not re.fullmatch(r'lya-memory-lab/[a-z0-9-]{1,40}/',prefix)):
        raise ValueError('Explicit disposable bucket/prefix required.')
    receipt=Path(receipt).absolute();_unlinked(receipt)
    if receipt.exists():raise FileExistsError('A receipt must be new; never use an old receipt as fresh trust.')
    current=observe()
    if type(current) is not RecoveryPins or current!=pins:raise Conflict('Source differs from fresh independent pins.')
    expected=dict(zip(NAMES,(pins.backup_sha256,pins.state.anchor.sha256,pins.keys_digest)))
    blobs={};remaining=MAX_PACK_BYTES
    for name,path in _paths(folder).items():
        _unlinked(path)
        with path.open('rb') as source:blob=source.read(remaining+1)
        if len(blob)>remaining or hashlib.sha256(blob).hexdigest()!=expected[name]:
            raise ValueError('Ciphertext differs from bounded independent fingerprints.')
        blobs[name]=blob;remaining-=len(blob)
    pack_id=hashlib.sha256(_json(asdict(pins)).encode()).hexdigest()
    scope=prefix+pins.state.anchor.lineage+'/'+pack_id+'/'
    client=_B2(cancelled)
    client.authorize(key_id,key,bucket_id,bucket_name,prefix)
    missing=[]
    for name,blob in blobs.items():
        seen=client.get(scope+name,len(blob))
        if seen is None:missing.append(name)
        elif seen!=blob:raise Conflict('Existing remote artifact differs; refusing overwrite.')
    for name in missing:client.put(scope+name,blobs[name])
    for name,blob in blobs.items():
        if client.get(scope+name,len(blob))!=blob:raise ValueError('Remote byte readback failed.')
    client.check()
    current=observe()
    if type(current) is not RecoveryPins or current!=pins:raise Conflict('Trust advanced during transfer; no fresh backup acknowledgement.')
    result={'verified':True,'synthetic_only':True,'pack_id':pack_id,'object_prefix':scope,
            'encrypted_bytes':sum(map(len,blobs.values())),'sha256':expected}
    _publish(receipt,lambda path:path.write_text(_json(result),encoding='utf-8'),cancelled)
    return result
