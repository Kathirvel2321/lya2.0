"""Build only reviewed recovery Python code; no data, keys, drivers or configuration."""
import hashlib
from pathlib import Path
import zipfile

from brain.memory_custody import _approval
from brain.memory_prototype import _unlinked
from brain.memory_recovery import _publish

ROOT=Path(__file__).resolve().parents[1]
SOURCES=('brain/conversation.py','brain/memory_prototype.py','brain/memory_recovery.py',
    'brain/memory_custody.py','brain/memory_recovery_pack.py','brain/memory_recovery_trust.py',
    'brain/memory_recovery_latest.py','tools/memory_recovery_host.py')


def build(destination,*,synthetic_only=False,approved=False):
    _approval(synthetic_only,approved,lambda:False)
    files={};hashes={}
    for name in SOURCES:
        path=ROOT/name;_unlinked(path);blob=path.read_bytes()
        hashes[name]=hashlib.sha256(blob).hexdigest()
        files['__main__.py' if name==SOURCES[-1] else name]=blob
    # zipimport needs an explicit package; the working tree uses a namespace package.
    files['brain/__init__.py']=b''
    def check(path):
        with zipfile.ZipFile(path) as archive:
            if sorted(archive.namelist())!=sorted(files) or any(archive.read(name)!=blob for name,blob in files.items()):
                raise ValueError('Recovery code archive readback differs.')
    def write(stage):
        with zipfile.ZipFile(stage,'w') as archive:
            for name,blob in sorted(files.items()):
                info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,blob)
        check(stage)
    _publish(destination,write,lambda:False);check(destination)
    blob=Path(destination).read_bytes()
    return {'fake_data_only':True,'contains_runtime_data_or_keys':False,'contains_native_dependencies':False,
        'files':sorted(files),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'source_sha256':hashes}
