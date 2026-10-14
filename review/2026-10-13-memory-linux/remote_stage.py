"""Disposable ARM64 driver qualification; executed via pinned SSH, never imported by runtime."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

WHEEL = 'sqlcipher3-0.6.3-cp312-cp312-manylinux_2_28_aarch64.whl'
URL = 'https://files.pythonhosted.org/packages/26/75/5dbf4ea0543ec163ca039de3ad07535a0bfe1317a2746628e270205bc8de/'+WHEEL
SHA256 = '96b89544616cb71284c89bedc5519c42ca34027016638678ba607f7189ead248'
SOURCES = {'brain/__init__.py','brain/conversation.py','brain/memory_prototype.py',
           'brain/memory_recovery.py','brain/memory_repository.py','brain/memory_authority.py','test_qualification.py'}

RUNNER = r'''
import io,json,pathlib,sys,tempfile,time,unittest
root=pathlib.Path.cwd();sys.path[:0]=[str(root/'drivers'),str(root)]
tempfile.tempdir=str(root/'fixtures')
from sqlcipher3 import dbapi2 as cipher
import test_qualification
start=time.monotonic();log=io.StringIO()
result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_qualification))
with cipher.connect(':memory:') as db:version=db.execute('PRAGMA cipher_version').fetchone()[0]
print(json.dumps(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
    skipped=len(result.skipped),passed=result.wasSuccessful() and not result.skipped,
    cipher_version=version,sqlite_version=cipher.sqlite_version,elapsed_seconds=round(time.monotonic()-start,3),
    tests=log.getvalue())))
'''


def mobile_state():
    run = subprocess.run(['systemctl','show','lya-connect.service','-p','ActiveState','-p','MemoryMax'],
                         capture_output=True,text=True,check=True,timeout=5)
    state = dict(line.split('=',1) for line in run.stdout.splitlines() if '=' in line)
    base = Path('/opt/lya-connect')
    state['hashes'] = {name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in
        ('cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py')}
    return state


def bounds():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(90,90))
    resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024**2,128*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def main():
    os.umask(0o077);packet = json.load(sys.stdin)
    if packet['owner_confirmed_free'] is not True:raise ValueError('Owner-confirmed free allowance required.')
    if platform.machine()!='aarch64' or sys.version_info[:2]!=(3,12):raise ValueError('Wrong pinned target platform.')
    sources = packet['sources']
    if set(sources)!=SOURCES or set(packet['sha256'])!=SOURCES:raise ValueError('Unexpected qualification source.')
    for name,source in sources.items():
        if type(source) is not str or len(source.encode())>100000:raise ValueError('Invalid bounded source.')
        compile(source,name,'exec')
        if hashlib.sha256(source.encode()).hexdigest()!=packet['sha256'][name]:raise ValueError('Source digest mismatch.')
    if shutil.disk_usage('/tmp').free<1024**3:raise ValueError('Insufficient staging disk headroom.')
    before = mobile_state();start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='lya-memory-qualification-',dir='/tmp') as folder:
        root = Path(folder);wheel = root/WHEEL
        with urllib.request.urlopen(URL,timeout=20) as response:blob = response.read(16*1024**2+1)
        if len(blob)>16*1024**2 or hashlib.sha256(blob).hexdigest()!=SHA256:raise ValueError('Pinned wheel verification failed.')
        wheel.write_bytes(blob);drivers = root/'drivers';drivers.mkdir()
        with zipfile.ZipFile(wheel) as archive:
            if sum(item.file_size for item in archive.infolist())>64*1024**2:raise ValueError('Oversized wheel contents.')
            for item in archive.infolist():
                path = PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or (item.external_attr>>16)&0o170000==0o120000:
                    raise ValueError('Linked or escaping wheel entry.')
            archive.extractall(drivers)
        for name,source in sources.items():
            target = root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
        (root/'fixtures').mkdir();(root/'run_tests.py').write_text(RUNNER,encoding='utf-8')
        run = subprocess.run([sys.executable,'-I','-B','run_tests.py'],cwd=root,capture_output=True,text=True,
                             timeout=120,preexec_fn=bounds)
        if run.returncode:raise RuntimeError('Qualification process failed; raw output withheld.')
        result = json.loads(run.stdout)
        result.update(wheel=WHEEL,wheel_sha256=SHA256,source_sha256=packet['sha256'],
                      platform='Linux aarch64 CPython 3.12',fake_data_only=True,
                      native_identity_tested=False,private_memory_or_keys_transferred=False)
    result.update(temporary_stage_removed=not root.exists(),mobile_state_and_source_unchanged=mobile_state()==before,
                  production_activated=False,system_packages_changed=False,
                  owner_confirmed_free=True,billing_api_verified=False,
                  total_seconds=round(time.monotonic()-start,3),
                  child_max_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024)
    print(json.dumps(result))


if __name__=='__main__':main()
