"""Same-corpus local plaintext/SQLCipher comparison; fake data and workspace temps only."""
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(HERE/'.drivers'))
from brain.conversation import Context, PublicTurn
from brain.memory_prototype import SyntheticMemory
from brain.memory_recovery import SyntheticRecovery
from brain.memory_repository import SyntheticRepository


def summary(values):
    values = sorted(values)
    return dict(samples=len(values),p50_ms=round(statistics.median(values),3),
                p95_ms=round(values[math.ceil(.95*len(values))-1],3))


def qualify(folder, encrypted):
    now = 2000000000.
    key = os.urandom(32) if encrypted else None
    memory = SyntheticMemory(folder/'memory.sqlite',synthetic_only=True,encryption_key=key,clock=lambda:now)
    context = Context('a'*64,'laptop','b'*64,'a'*64,now+300,True)
    owner = memory.create_owner(context.principal)
    samples = {name:[] for name in ('save','get','search','correct','retry','forget')}
    def call(packet, name):
        turn = PublicTurn('f'*32,'SYNTHETIC_PUBLIC_FIXTURE',context,time.monotonic()+30,
                          lambda:context,lambda:now,threading.Event())
        started = time.perf_counter()
        result = memory.handle(turn,packet,approved=True)
        samples[name].append((time.perf_counter()-started)*1000)
        return result
    receipts = []
    for i in range(1000):
        packet = dict(op='save',project='fake-project',request_id=f'{i+1:032x}',kind='preference',
                      key=f'fixture{i:04d}',value={'text':f'SYNTHETIC_VALUE_{i:04d}'},retention={'mode':'permanent'})
        receipts.append(call(packet,'save'))
    for i in range(60):
        receipt = receipts[i*13]
        row = call(dict(op='get',project='fake-project',id=receipt['id']),'get')['record']
        assert row['owner'] == owner and row['revision'] == 1
        rows = call(dict(op='search',project='fake-project',query=f'fixture{i*13:04d}'),'search')['records']
        assert len(rows) == 1 and rows[0]['id'] == receipt['id']
        packet = dict(op='correct',project='fake-project',request_id=f'{2000+i:032x}',id=receipt['id'],
                      expected_revision=1,value={'text':'SYNTHETIC_CORRECTED'})
        result = call(packet,'correct');assert call(packet,'retry') == result
        assert call(dict(op='forget',project='fake-project',request_id=f'{3000+i:032x}',
                         id=receipt['id'],expected_revision=2),'forget')['revision'] == 3
    reopened = SyntheticMemory(memory.path,synthetic_only=True,encryption_key=key,clock=lambda:now)
    memory = reopened
    assert call(dict(op='get',project='fake-project',id=receipts[-1]['id']),'get')['record']['revision'] == 1
    with reopened._db() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        cipher_version = db.execute('PRAGMA cipher_version').fetchone() if encrypted else None
        if encrypted:assert not db.execute('PRAGMA cipher_integrity_check').fetchall()
        counts = {name:db.execute('SELECT count(*) FROM '+name).fetchone()[0]
                  for name in ('memories','memory_search','outbox','requests','deletions')}
        assert counts == dict(memories=1000,memory_search=940,outbox=1120,requests=1120,deletions=60)
    r = SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True,clock=lambda:now)
    repository = SyntheticRepository(folder/'repository',synthetic_only=True)
    assert repository.sync(reopened,r,approved=True)['state'] == 'verified'
    lineage,sequence = repository._state(reopened)
    restored_path = folder/'restored.sqlite'
    result = repository.restore(lineage,r,restored_path,required_sequence=sequence,approved=True,storage_key=key)
    assert result['preserved'] == 940 and result['suppressed_deleted'] == 60
    assert result['active_bindings'] == result['resumed_jobs'] == 0
    restored = SyntheticMemory(restored_path,synthetic_only=True,encryption_key=key)
    with restored._db() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        if encrypted:assert not db.execute('PRAGMA cipher_integrity_check').fetchall()
    for path in (memory.path,restored_path):
        data = path.read_bytes()
        assert data.startswith(b'SQLite format 3') != encrypted
        assert (b'SYNTHETIC_VALUE_0999' in data) != encrypted
        if key:assert key not in data
    return dict(engine='sqlcipher' if encrypted else 'stdlib_sqlite',encrypted=encrypted,
                sqlite_version=memory._driver.sqlite_version,cipher_version=cipher_version[0] if cipher_version else None,
                corpus_records=1000,database_bytes=memory.path.stat().st_size,
                timings={name:summary(values) for name,values in samples.items()},counts=counts,
                restart_integrity_and_quarantined_restore_checked=True)


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        for encrypted in (False,True):
            destination = Path(folder)/('encrypted' if encrypted else 'plaintext');destination.mkdir()
            results.append(qualify(destination,encrypted))
            print(('SQLCipher' if encrypted else 'Plaintext')+' 1,000-record qualification passed.',flush=True)
    wheel = HERE/'wheels/sqlcipher3-0.6.3-cp312-cp312-win_amd64.whl'
    expected = '9abace2cfd755184d75510f7c56e8bff5f146a204b29e926e03c81a32a514a7b'
    actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert actual == expected
    report = dict(date='2026-10-12',fake_data_only=True,results=results,
                  package_version=importlib.metadata.version('sqlcipher3'),wheel_sha256=actual,
                  postgres_tested=False,production_engine_selected=False,oracle_qualified=False,
                  actual_phone_latency_qualified=False,independent_recovery_qualified=False,
                  key_custody_configured=False,old_writer_fencing_implemented=False,deployed=False,
                  authentication='injected_synthetic_context_not_native_auth_cost',
                  run_context='one_local_sequential_run_uncontrolled_desktop_load_different_sqlite_builds')
    (HERE/'qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':main()
