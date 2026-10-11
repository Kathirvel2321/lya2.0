"""Explicit owner-approved mobile control over the existing pinned operator SSH."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re

from cloud.mobile import checked_origin

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'desktop/mobile.local.json'


def control(operation,session,db_path=None,cancelled=None):
    from storage import store
    from cloud.ssh_session import exchange
    if operation not in ('invite','revoke'):raise ValueError('Invalid connection operation.')
    try:
        config=json.loads(CONFIG.read_text())
        origin=checked_origin(config['origin'])
        if config.get('enabled') is not True:raise ValueError('Not enabled')
    except Exception:
        raise ValueError('The mobile connection is awaiting private Tailscale setup. No pairing was started.') from None
    oracle=json.loads((ROOT/'desktop/oracle.local.json').read_text())
    key=(ROOT/oracle['key_file']).resolve();key.relative_to(ROOT)
    if not key.is_file():raise ValueError('Pinned connection unavailable.')
    with store.store_connection(db_path,read_only=True) as db:
        credential=store._profile_owner(db,session)
    binding=hashlib.sha256(credential.encode()).hexdigest()
    command=['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=7',
        '-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ForwardAgent=no',
        '-o','ClearAllForwardings=yes','-o','ControlMaster=no','-o','ControlPath=none',
        '-o','UserKnownHostsFile='+str(ROOT/'oracle_known_hosts.local'),'-i',str(key),
        'ubuntu@'+str(ipaddress.ip_address(oracle['host'])),
        'sudo -n -u lya-connect /opt/lya-connect/venv/bin/python -I /opt/lya-connect/control.py '+operation]
    try:
        run=exchange(command,json.dumps({'binding':binding}),cancelled,timeout=15,close_stdin=True)
        if run.returncode or len(run.stdout)>4096:raise ValueError()
        result=json.loads(run.stdout)
        with store.store_connection(db_path,read_only=True) as db:store._profile_owner(db,session,credential)
        if operation=='revoke':
            if result!={'revoked':True}:raise ValueError()
            return result
        url=result.get('url')
        if (set(result) not in ({'url'},{'url','paired'}) or type(url) is not str
                or not (url==origin+'/' or re.fullmatch(re.escape(origin)+r'/#[A-Za-z0-9_-]{43}',url))):
            raise ValueError()
        return {'url':url,'origin':origin}
    except InterruptedError:raise
    except Exception:
        raise ValueError('Mobile connection unavailable or owner proof expired. No access was unlocked; retry after setup.') from None
