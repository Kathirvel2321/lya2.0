"""One-time reviewed installation on the existing free VM, synthetic acceptance.

Run only with --confirmed-free-allowance. No provider API keys or private corpus.
Existing inference files/users/services are never modified. Repeat runs refuse
an existing archive account/path rather than overwriting an unknown installation.
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cloud.public_archive import OraclePublicArchive
from storage.public_archive import PublicArchive, PublicCache, encoded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirmed-free-allowance', action='store_true', required=True)
    parser.parse_args()
    config_path = ROOT / 'desktop/oracle.local.json'
    config = json.loads(config_path.read_text())
    host = str(ipaddress.ip_address(config['host']))
    operator_key = (ROOT / config['key_file']).resolve()
    operator_key.relative_to(ROOT)
    pins = ROOT / 'oracle_known_hosts.local'
    assert operator_key.is_file() and pins.is_file()
    options = ['-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=7',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no', '-o', 'ForwardAgent=no',
               '-o', 'ClearAllForwardings=yes', '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
               '-o', 'UserKnownHostsFile='+str(pins), '-i', str(operator_key)]

    def operator(program, body=b''):
        run = subprocess.run(['ssh', *options, 'ubuntu@'+host,
                              'sudo -n /usr/bin/python3 -c '+shlex.quote(program)],
                             input=body, capture_output=True, timeout=25,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if run.returncode:
            raise RuntimeError('Archive installation/check failed; raw SSH errors withheld. Existing inference is unchanged.')
        return json.loads(run.stdout)

    preflight = operator("import os,pwd,json\ntry: pwd.getpwnam('lya-archive'); exists=True\nexcept KeyError: exists=False\nprint(json.dumps({'clear':not exists and not os.path.lexists('/opt/lya-public') and not os.path.lexists('/var/lib/lya-public')}))")
    if preflight != {'clear': True}:
        raise RuntimeError('Archive path/account is already present. Inspect the existing deployment before proceeding.')
    identity = ROOT / 'security/public-archive-identity.local'
    if identity.exists():
        raise RuntimeError('Archive identity already exists. Review rather than regenerate it.')
    identity.mkdir()
    if os.name != 'nt':
        identity.chmod(0o700)
    else:
        sid_run = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                                  '[Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],
                                 capture_output=True, text=True, timeout=10)
        sid = sid_run.stdout.strip()
        if sid_run.returncode or not re.fullmatch(r'S-1-[0-9-]+', sid):
            raise RuntimeError('Could not establish local identity ACL.')
        acl = subprocess.run(['icacls', str(identity), '/inheritance:r', '/grant:r', '*'+sid+':(OI)(CI)F'],
                             capture_output=True, timeout=10)
        if acl.returncode:
            raise RuntimeError('Could not protect local archive identity directory.')
    key = identity / 'archive.key'
    made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'lya-public-archive', '-f', str(key)],
                          capture_output=True, timeout=10,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if made.returncode:
        raise RuntimeError('Restricted archive identity creation failed; no secret output emitted.')
    public = key.with_suffix('.key.pub').read_text().strip()
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+ lya-public-archive', public):
        raise RuntimeError('Unexpected archive public key format.')
    source = (ROOT / 'storage/public_archive.py').read_text()
    compile(source, 'public_archive.py', 'exec')
    digest = hashlib.sha256(source.encode()).hexdigest()
    installer = '''import hashlib,json,os,pathlib,pwd,subprocess,sys
os.umask(0o077)
body=json.load(sys.stdin)
source=body['source']; key=body['public_key']
assert hashlib.sha256(source.encode()).hexdigest()==body['sha256']
compile(source,'public_archive.py','exec')
base=pathlib.Path('/opt/lya-public'); home=pathlib.Path('/var/lib/lya-public')
assert not base.exists() and not home.exists()
try: pwd.getpwnam('lya-archive'); raise RuntimeError('account_exists')
except KeyError: pass
subprocess.run(['useradd','--system','--user-group','--home-dir',str(home),'--shell','/bin/sh','lya-archive'],check=True,capture_output=True)
account=pwd.getpwnam('lya-archive')
base.mkdir(mode=0o755); base.chmod(0o755)
worker=base/'public_archive.py'; worker.write_text(source); worker.chmod(0o644)
home.mkdir(mode=0o755); home.chmod(0o755)
ssh=home/'.ssh'; ssh.mkdir(mode=0o755); ssh.chmod(0o755)
auth=ssh/'authorized_keys'
auth.write_text('restrict,command="/usr/bin/python3 -I /opt/lya-public/public_archive.py" '+key+'\\n')
auth.chmod(0o644)
data=home/'.local/share/lya-public'; data.mkdir(mode=0o700,parents=True)
for path in (home/'.local',home/'.local/share',data):
 os.chown(path,account.pw_uid,account.pw_gid); path.chmod(0o700)
print(json.dumps({'installed':True,'worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'forced_command':True,'new_account_only':True}))'''
    installed = operator(installer, encoded({'source': source, 'public_key': public, 'sha256': digest}))
    assert installed['installed'] and installed['worker_sha256'] == digest
    gates = dict(enabled=True, free_allowance_verified=True, isolated_access_verified=True,
                 recovery_verified=True, key_file=str(key.relative_to(ROOT)).replace('\\', '/'))
    trial_config = dict(config, public_archive=gates)
    timings = []
    calls = []
    from cloud.ssh_session import exchange
    def measured(command, body, cancelled, **kwargs):
        started = time.perf_counter()
        result = exchange(command, body, cancelled, **kwargs)
        timings.append(round((time.perf_counter()-started)*1000, 3))
        calls.append(json.loads(body)['op'])
        return result
    with tempfile.TemporaryDirectory(prefix='lya-public-deploy-') as temporary:
        cache = PublicCache(Path(temporary)/'cache', budget=4096)
        client = OraclePublicArchive(trial_config, cache=cache, exchange=measured)
        item = dict(owner='synthetic-check', project='acceptance', id='guide', revision=1,
                    title='Synthetic archive check', source='https://example.invalid/archive-check',
                    text='Synthetic turtles use asyncio. This document contains no owner data.',
                    expires_at=time.time()+86400, sensitivity='public')
        client.put(item, expected_revision=0, reviewed_public=True)
        client.put(item, expected_revision=0, reviewed_public=True)
        assert client.get(item['owner'],item['project'],item['id'],1)['record']==item
        assert len(client.search(item['owner'],item['project'],'asyncio')['records'])==1
        assert client.search(item['owner'],'other','asyncio')['records']==[]
        # The root-controlled forced command must ignore a shell command.
        restricted_options=list(options)
        restricted_options[-1]=str(key)
        packet=dict(op='search',owner=item['owner'],project=item['project'],query='asyncio')
        run=subprocess.run(['ssh',*restricted_options,'lya-archive@'+host,'echo UNRESTRICTED_SHELL'],
                           input=encoded(packet),capture_output=True,timeout=15,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert run.returncode==0 and 'UNRESTRICTED_SHELL' not in run.stdout.decode()
        assert len(json.loads(run.stdout)['records'])==1
        recovery_program='''import base64,json,pathlib,pwd,sqlite3,tempfile,os
root=pathlib.Path('/var/lib/lya-public/.local/share/lya-public')
source=root/'archive.sqlite'; account=pwd.getpwnam('lya-archive')
worker=pathlib.Path('/opt/lya-public/public_archive.py')
auth=pathlib.Path('/var/lib/lya-public/.ssh/authorized_keys')
assert worker.stat().st_uid==0 and auth.stat().st_uid==0
assert worker.stat().st_mode & 0o022==0 and auth.stat().st_mode & 0o022==0
assert source.stat().st_uid==account.pw_uid and source.stat().st_mode & 0o077==0
fd,path=tempfile.mkstemp(prefix='lya-public-recovery-',suffix='.sqlite'); os.close(fd)
try:
 src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True); dst=sqlite3.connect(path)
 try: src.backup(dst); assert dst.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 finally: src.close(); dst.close()
 data=pathlib.Path(path).read_bytes(); assert len(data)<1048576
 print(json.dumps({'snapshot':base64.b64encode(data).decode(),'filesystem_permissions':True}))
finally: pathlib.Path(path).unlink()'''
        backup = operator(recovery_program)
        import base64
        snapshot = Path(temporary)/'independent-public-check.sqlite'
        snapshot.write_bytes(base64.b64decode(backup['snapshot'], validate=True))
        recovered = PublicArchive(snapshot)
        assert recovered.handle(dict(op='get',owner=item['owner'],project=item['project'],id=item['id'],revision=1))['record']==item
        client.delete(item['owner'],item['project'],item['id'],expected_revision=1)
        assert client.get(item['owner'],item['project'],item['id'],1)['record'] is None
        assert cache.get(item['owner'],item['project'],item['id'],1) is None
    # The existing config is preserved; add only the explicit archive feature gates.
    updated=dict(config,public_archive=dict(gates,verified_on='2026-10-07',
                                          free_verification='owner_confirmed_existing_vm_and_storage'))
    fd,path=tempfile.mkstemp(dir=config_path.parent,prefix='.oracle-archive-',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as output:
            json.dump(updated,output,indent=2); output.write('\n'); output.flush(); os.fsync(output.fileno())
        os.replace(path,config_path)
    finally:
        Path(path).unlink(missing_ok=True)
    evidence=dict(status='deployed_synthetic_live_checks_passed',worker_sha256=digest,
                  free_allowance='owner_confirmed',forced_command_verified=True,filesystem_permissions=True,
                  independent_synthetic_snapshot_restored=True,remote_private_data_transferred=False,
                  synthetic_document_deleted=True,provider_api_called=False,background_service_added=False,
                  ssh_operation_ms=timings,operations=calls,
                  limitations=['Actual LYA owner authorization not live accepted',
                               'Full archive backup automation not implemented',
                               'Semantic retrieval not implemented',
                               'Restricted account is not an OS sandbox or a complete penetration test'])
    (Path(__file__).parent/'deployment.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':
    main()
