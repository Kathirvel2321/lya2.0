"""Synthetic local SQLite timing only; no production auth/network/model/store."""
import importlib.util
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from brain.conversation import Context, PublicTurn
from brain.memory_prototype import SyntheticMemory


def summary(values):
    values = sorted(values)
    return {'samples': len(values), 'p50_ms': round(statistics.median(values), 3),
            'p95_ms': round(values[math.ceil(.95 * len(values)) - 1], 3)}


def main():
    now = 2000000000.
    context = Context('a'*64, 'laptop', 'b'*64, 'a'*64, now + 300, True)
    def turn():
        return PublicTurn('f'*32, 'SYNTHETIC_PUBLIC_FIXTURE', context, time.monotonic()+30,
                          lambda: context, lambda: now, threading.Event())
    def measured(packet, samples):
        started = time.perf_counter()
        result = memory.handle(turn(), packet, approved=True)
        samples.append((time.perf_counter()-started)*1000)
        return result
    timings = {key: [] for key in ('save', 'get', 'search', 'correct', 'retry', 'forget')}
    with tempfile.TemporaryDirectory(prefix='lya-memory-qualification-') as temp:
        path = Path(temp)/'fake.sqlite'
        memory = SyntheticMemory(path, synthetic_only=True, clock=lambda: now)
        owner = memory.create_owner(context.principal)
        receipts = []
        for i in range(1000):
            packet = dict(op='save', project='fake-project', request_id=f'{i+1:032x}', kind='preference',
                          key=f'fixture{i:04d}', value={'text': f'synthetic value fixture{i:04d}'}, retention={'mode':'permanent'})
            receipts.append(measured(packet, timings['save']))
        for i in range(60):
            receipt = receipts[i*13]
            record = measured(dict(op='get', project='fake-project', id=receipt['id']), timings['get'])['record']
            assert record['owner'] == owner and record['revision'] == 1
            hits = measured(dict(op='search', project='fake-project', query=f'fixture{i*13:04d}'), timings['search'])['records']
            assert len(hits) == 1 and hits[0]['id'] == receipt['id']
            packet = dict(op='correct', project='fake-project', request_id=f'{2000+i:032x}', id=receipt['id'], expected_revision=1, value={'text':'synthetic corrected'})
            result = measured(packet, timings['correct'])
            assert measured(packet, timings['retry']) == result
            deleted = measured(dict(op='forget', project='fake-project', request_id=f'{3000+i:032x}', id=receipt['id'], expected_revision=2), timings['forget'])
            assert deleted['revision'] == 3
            assert memory.handle(turn(), dict(op='get', project='fake-project', id=receipt['id']), approved=True)['record'] is None
        reopened = SyntheticMemory(path, synthetic_only=True, clock=lambda: now)
        assert reopened.handle(turn(), dict(op='get', project='fake-project', id=receipts[-1]['id']), approved=True)['record']['revision'] == 1
        with memory._db() as db:
            counts = {name: db.execute('SELECT count(*) FROM '+name).fetchone()[0]
                      for name in ('memories','memory_search','outbox','requests','deletions')}
            assert counts == dict(memories=1000, memory_search=940, outbox=1120, requests=1120, deletions=60)
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
        report = dict(date='2026-10-11', engine='stdlib_sqlite_plaintext_fake_only', sqlite_version=sqlite3.sqlite_version,
                      corpus_records=1000, timings={k:summary(v) for k,v in timings.items()},
                      database_bytes=path.stat().st_size, counts=counts, restart_checked=True,
                      integrity_checked=True, foreign_keys_checked=True,
                      authentication='injected_synthetic_context_not_native_auth_cost',
                      encrypted=False, real_phone_latency_qualified=False, provider_called=False,
                      engine_comparison_complete=False,
                      run_context='concurrent_isolated_checks_uncontrolled_desktop_load',
                      optional_drivers={name:importlib.util.find_spec(name) is not None
                                        for name in ('psycopg','psycopg2','sqlcipher3','pysqlcipher3')})
        target = Path(__file__).with_name('qualification.json')
        target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':main()
