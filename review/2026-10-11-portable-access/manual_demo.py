"""Guided fake-data walkthrough; no real app/store, provider, sensors or deployment."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from brain.memory_prototype import SyntheticMemory
from brain.memory_recovery import SyntheticRecovery
from test_memory_prototype import MemoryChecks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auto',action='store_true',help='Run the same assertions without pausing.')
    args = parser.parse_args()
    def step(label):
        print('\n'+label,flush=True)
        if not args.auto:input('Press Enter to perform this step; Ctrl+C ends and removes the fake stores. ')
    fixture = MemoryChecks(methodName='runTest')
    try:
        fixture.setUp()
        print('SIMULATION ONLY: laptop/phone adapters use generated fake signed passkeys.')
        print('Records, encryption keys and backups are disposable. Do not enter personal information.')
        step('1. Save a fake preference through the laptop adapter; recall it through the phone adapter.')
        saved = fixture.call(fixture.save_packet(key='demo colour',value='SYNTHETIC_BLUE'))
        record = fixture.get(saved['id'],phone=True)
        assert record['value'] == {'text':'SYNTHETIC_BLUE'}
        print('Phone recalled:',record['value'],'revision',record['revision'])
        fixture.call(fixture.save_packet(key='demo expiry',value='SYNTHETIC_TEMPORARY',
                     retention={'mode':'until','expires_at':fixture.now+30}))
        recovery = SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True,clock=lambda:fixture.now)
        backup = fixture.path.parent/'snapshot.enc'
        recovery.backup(fixture.m,backup,approved=True)
        step('2. Correct through the phone adapter; reopen the database and read through the laptop adapter.')
        fixture.call(dict(op='correct',project='alpha',request_id=fixture.rid(),id=saved['id'],
                          expected_revision=1,value={'text':'SYNTHETIC_GREEN'}),phone=True)
        fixture.m = SyntheticMemory(fixture.path,synthetic_only=True,clock=lambda:fixture.now)
        record = fixture.get(saved['id'])
        assert record['value'] == {'text':'SYNTHETIC_GREEN'} and record['revision'] == 2
        print('Laptop recalled after reopen:',record['value'],'revision',record['revision'])
        step('3. Forget through the phone adapter; verify the laptop gets no record or search result.')
        fixture.call(dict(op='forget',project='alpha',request_id=fixture.rid(),id=saved['id'],expected_revision=2),phone=True)
        assert fixture.get(saved['id']) is None and not fixture.search('SYNTHETIC_GREEN')
        print('Laptop recall: None. Search: empty.')
        checkpoint = fixture.path.parent/'checkpoint.enc'
        anchor = recovery.checkpoint(fixture.m,checkpoint,approved=True)
        step('4. Advance the fake clock by 31 seconds; restore the old backup using the latest trusted checkpoint.')
        fixture.now += 31
        restored = fixture.path.parent/'restored.sqlite'
        result = recovery.restore(backup,checkpoint,restored,trusted_anchor=anchor,approved=True)
        recovered = SyntheticMemory(restored,synthetic_only=True,clock=lambda:fixture.now)
        with recovered._db() as db:
            assert db.execute('SELECT count(*) FROM memories WHERE deleted=0').fetchone()[0] == 0
            assert db.execute('SELECT count(*) FROM memory_search').fetchone()[0] == 0
            assert db.execute('SELECT count(*) FROM bindings').fetchone()[0] == 0
            assert db.execute('SELECT count(*) FROM outbox').fetchone()[0] == 0
        assert result['suppressed_deleted'] == result['suppressed_expired'] == 1
        print('Restore result:',result)
        print('\nPASS: save, cross-adapter recall, correction, reopen, forgetting, expiry and safe restore.')
        print('This proves the isolated fixture path, not two physical devices or live shared memory.')
    finally:
        fixture.doCleanups()
        print('Disposable fixtures cleaned up.',flush=True)


if __name__ == '__main__':main()
