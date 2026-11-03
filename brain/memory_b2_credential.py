"""Explicit Windows provisioning for the fake-data B2 pilot; no automatic access."""
import base64
import getpass
from pathlib import Path
import re
import sys
import time
import warnings

from brain.memory_b2_backup import CAPABILITIES,B2RequestRefused,_B2,_token,_url,backup_once
from brain.memory_custody import _approval
from brain.memory_prototype import _json,_unlinked
from brain.memory_recovery import _publish

PREFIX='lya-memory-lab/worker/'
ENTROPY=b'LYA-B2-LAB-CREDENTIAL-1'
MAGIC=b'LYA-B2-LAB-DPAPI-1\n'
UNCERTAIN='Pilot key may exist. Do not retry automatically; inspect B2 Application Keys or wait for the requested one-hour expiry. Secret details withheld.'


def _scope(bucket_id,bucket_name):
    if (type(bucket_id) is not str or not re.fullmatch(r'[a-zA-Z0-9]{6,64}',bucket_id)
            or type(bucket_name) is not str or not re.fullmatch(r'lya-(?:memory-lab|fake)-[a-zA-Z0-9-]{1,40}',bucket_name)):
        raise ValueError('Explicit LYA lab bucket ID/name required.')


def _key_id(value):
    if type(value) is not str or not re.fullmatch(r'[a-zA-Z0-9]{6,64}',value):
        raise ValueError('Invalid bounded application key ID.')
    return value


def _protect(raw):
    if sys.platform!='win32':raise OSError('Windows DPAPI is required; no plaintext fallback.')
    import win32crypt
    return win32crypt.CryptProtectData(raw,'LYA B2 lab credential',ENTROPY,None,None,1)


def _unprotect(blob):
    if sys.platform!='win32':raise OSError('Windows DPAPI is required; no plaintext fallback.')
    import win32crypt
    return win32crypt.CryptUnprotectData(blob,ENTROPY,None,None,1)[1]


def _expiry(value):
    now=int(time.time()*1000)
    if type(value) is not int or not now+60000<=value<=now+3660000:
        raise ValueError('A one-hour pilot credential with at least a minute remaining is required.')
    return value


def _destination(path):
    path=Path(path).absolute();_unlinked(path)
    if path.exists():raise FileExistsError('Credential destination must be new.')
    if not path.parent.is_dir():raise FileNotFoundError('Local credential folder must exist.')
    return path


def provision(destination,*,issuer_id,issuer_key,bucket_id,bucket_name,
              synthetic_only=False,approved=False,cancelled=lambda:False,
              check_only=False,progress=lambda stage:None):
    """One create request only; issuer stays in memory; return no secrets."""
    _approval(synthetic_only,approved,cancelled);_scope(bucket_id,bucket_name)
    if type(check_only) is not bool:raise ValueError('Explicit boolean check-only mode required.')
    progress('local protected storage');destination=_destination(destination)
    if _unprotect(_protect(b'LYA DPAPI preflight'))!=b'LYA DPAPI preflight':
        raise ValueError('Local protection preflight failed.')
    progress('issuer key ID format');issuer_id=_key_id(issuer_id)
    progress('issuer application key format');issuer_key=_token(issuer_key)
    basic=base64.b64encode((issuer_id+':'+issuer_key).encode()).decode()
    issuer=_B2(cancelled)
    progress('B2 issuer authentication')
    auth=issuer.decode(issuer.request('GET','https://api.backblazeb2.com/b2api/v4/b2_authorize_account',
                                    headers={'Authorization':'Basic '+basic}))
    progress('issuer permissions')
    try:
        storage=auth['apiInfo']['storageApi'];caps=storage['allowed']['capabilities']
        if type(caps) is not list or not CAPABILITIES.union({'writeKeys'}).issubset(caps):
            raise ValueError('Issuer lacks required creation/child permissions.')
        account=_key_id(auth['accountId']);issuer.api=_url(storage['apiUrl'],'api')
        issuer.headers={'Authorization':_token(auth['authorizationToken'])}
    except (KeyError,TypeError):raise ValueError('Malformed issuer metadata.') from None
    progress('private lab bucket')
    buckets=issuer.call('b2_list_buckets',{'accountId':account,'bucketId':bucket_id})
    try:
        if (len(buckets['buckets'])!=1 or buckets['buckets'][0]['bucketId']!=bucket_id
                or buckets['buckets'][0]['bucketName']!=bucket_name
                or buckets['buckets'][0]['bucketType']!='allPrivate'):
            raise ValueError('Exact existing private lab destination required.')
    except (KeyError,TypeError):raise ValueError('Malformed issuer bucket metadata.') from None
    if check_only:
        issuer.headers.clear()
        return {'preflight_passed':True,'key_created':False}
    request=dict(accountId=account,keyName='lya-memory-lab-worker-pilot',
        capabilities=sorted(CAPABILITIES),validDurationInSeconds=3600,bucketIds=[bucket_id],namePrefix=PREFIX)
    # A lost create reply can leave a live key; B2 has no idempotent create token.
    try:
        progress('one-hour key creation')
        created=issuer.call('b2_create_key',request)
        if (created['accountId']!=account or created['keyName']!=request['keyName']
                or created['bucketIds']!=[bucket_id] or created['namePrefix']!=PREFIX
                or type(created['capabilities']) is not list
                or sorted(created['capabilities'])!=sorted(CAPABILITIES)):
            raise ValueError('Created key differs from approved scope.')
        key_id=_key_id(created['applicationKeyId']);key=_token(created['applicationKey'])
        if len(key)>512:raise ValueError('Oversized pilot secret.')
        expiry=_expiry(created['expirationTimestamp'])
        child=_B2(cancelled)
        if child.authorize(key_id,key,bucket_id,bucket_name,PREFIX)!=expiry:
            raise ValueError('Created and independently authorized key expiry differ.')
        data=dict(version=1,key_id=key_id,key=key,bucket_id=bucket_id,bucket_name=bucket_name,
                  prefix=PREFIX,expires_ms=expiry)
        raw=_json(data).encode();blob=MAGIC+_protect(raw)
        if _unprotect(blob[len(MAGIC):])!=raw:raise ValueError('Protected credential readback failed.')
        _publish(destination,lambda path:path.write_bytes(blob),cancelled)
        if destination.read_bytes()!=blob:raise ValueError('Published credential differs.')
        return {'stored':True,'expires_ms':expiry,'synthetic_only':True}
    except (Exception,KeyboardInterrupt):raise RuntimeError(UNCERTAIN) from None
    finally:
        # shortcut: Python/OS buffers cannot be reliably zeroed; qualify host/process isolation before private use.
        issuer.headers.clear()


def _load(path,bucket_id,bucket_name):
    _scope(bucket_id,bucket_name);path=Path(path).absolute();_unlinked(path)
    with path.open('rb') as source:blob=source.read(16385)
    if len(blob)>16384 or not blob.startswith(MAGIC):raise ValueError('Invalid bounded protected credential.')
    try:
        data=_B2.decode(_unprotect(blob[len(MAGIC):]))
        if (set(data)!={'version','key_id','key','bucket_id','bucket_name','prefix','expires_ms'}
                or type(data['version']) is not int or data['version']!=1
                or data['bucket_id']!=bucket_id or data['bucket_name']!=bucket_name or data['prefix']!=PREFIX):
            raise ValueError('Protected credential scope differs.')
        _key_id(data['key_id']);_token(data['key']);_expiry(data['expires_ms'])
        if len(data['key'])>512:raise ValueError('Oversized pilot secret.')
        return data
    except Exception:raise ValueError('Protected credential is unavailable, invalid, expired or out of scope.') from None


def backup_with_credential(folder,receipt,*,credential_path,bucket_id,bucket_name,pins,observe,
                           synthetic_only=False,approved=False,cancelled=lambda:False):
    _approval(synthetic_only,approved,cancelled)
    data=_load(credential_path,bucket_id,bucket_name)
    return backup_once(folder,receipt,pins=pins,observe=observe,key_id=data['key_id'],key=data['key'],
        bucket_id=bucket_id,bucket_name=bucket_name,prefix=PREFIX,
        synthetic_only=synthetic_only,approved=approved,cancelled=cancelled)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true',help='Check local storage, issuer access and bucket; create no key or file.')
    parser.add_argument('destination',help='New local DPAPI credential file; contains only the restricted child key.')
    args=parser.parse_args()
    if sys.platform!='win32' or not sys.stdin.isatty() or not sys.stderr.isatty():
        parser.error('Use an interactive Windows owner terminal; redirected secret input is refused.')
    stage='local protected storage'
    def progress(value):
        nonlocal stage
        stage=value;print('Checking '+value+'...')
    try:
        _destination(args.destination)
        stage='lab bucket input'
        bucket_id=input('Existing disposable lab bucket ID: ').strip()
        bucket_name=input('Existing disposable lab bucket name: ').strip();_scope(bucket_id,bucket_name)
        if args.check_only:print('Read-only check: no key creation, credential file or upload.')
        else:
            print('Create ONE key for '+bucket_name+', prefix '+PREFIX+', exactly listBuckets/readFiles/writeFiles, for 3600 seconds. No upload.')
            if input('Type CREATE ONE-HOUR LAB KEY to approve: ')!='CREATE ONE-HOUR LAB KEY':
                print('Cancelled before credential entry or network access.');return 1
        stage='private credential entry'
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            print('Type the key ID manually. For the application key, use the terminal Paste action; Ctrl+V may enter a control character.')
            issuer_id=getpass.getpass('Issuer key ID (hidden, local only): ')
            stage='issuer key ID format';_key_id(issuer_id)
            stage='private credential entry'
            issuer_key=getpass.getpass('Existing issuer key with writeKeys (hidden, local only): ')
            stage='issuer application key format';_token(issuer_key)
        provision(args.destination,issuer_id=issuer_id,issuer_key=issuer_key,bucket_id=bucket_id,
                  bucket_name=bucket_name,synthetic_only=True,approved=True,
                  check_only=args.check_only,progress=progress)
        if args.check_only:
            print('Read-only checks passed. No key created, credential file written or upload performed.');return 0
        print('Restricted pilot credential stored with Windows DPAPI. No upload performed.');return 0
    except KeyboardInterrupt:
        print('Cancelled.');return 130
    except RuntimeError:
        print(UNCERTAIN);return 1
    except FileExistsError:
        print('Setup refused: local credential file already exists and was preserved. No key creation requested.');return 1
    except FileNotFoundError:
        print('Setup refused: local credential folder is missing. Create it first. No key creation requested.');return 1
    except B2RequestRefused as error:
        status=str(error.status) if error.status is not None else 'unavailable'
        print('Setup refused at '+stage+' (HTTP '+status+'). No key creation requested; secret details withheld.');return 1
    except Exception:
        hints={'issuer key ID format':'Key ID needs 6-64 letters/digits. Type only the ID manually, without labels, spaces or quotes.',
               'issuer application key format':'Application key must be nonempty without spaces/control characters. Use the terminal Paste action, not Ctrl+V; paste only the saved key value.',
               'issuer permissions':'Issuer needs writeKeys, listBuckets, readFiles and writeFiles.',
               'private lab bucket':'Check the exact lab bucket ID/name and private setting.',
               'private credential entry':'Hidden input was unavailable; use an interactive Windows PowerShell window.',
               'B2 issuer authentication':'Check connectivity, certificate trust and the saved issuer ID/key locally.',
               'local protected storage':'Check Windows DPAPI, folder access and unlinked paths.',
               'lab bucket input':'Check the lab bucket ID and name.'}
        print('Setup refused at '+stage+'. '+hints.get(stage,'Check the local setup.')+' No key creation requested; secret details withheld.');return 1


if __name__=='__main__':raise SystemExit(main())
