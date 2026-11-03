"""Real ENOSPC in an 8 MiB private tmpfs; fake data, no host mount or real stores."""
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from brain import memory_witness_service as rpc
from brain.memory_prototype import Conflict
import test_memory_witness_process as process
import test_memory_witness_cgroup as cgroup
import test_memory_witness_service as protocol
import test_memory_witness_tls as tls
import test_memory_network_authority as network

QUOTA_BYTES=8*1024*1024
QUOTA_INODES=128
ACTIONS=('prepare_bytes','prepare_inodes','finish','retire','committed_reply_loss','authority')
BOOTSTRAP="import json,sys; p=json.loads(sys.stdin.readline()); sys.path.insert(0,p['root']); from test_memory_witness_disk import namespace_worker; namespace_worker(p)"
WORKER="import json,sys; p=json.loads(sys.stdin.readline()); sys.path.insert(0,p.pop('root')); from test_memory_witness_disk import disk_worker; disk_worker(p)"
METRICS={}


def fill(volume,kind='bytes'):
    for index in range(256):
        try:
            with (volume/f'.pressure-{index:03d}').open('xb',buffering=0) as output:
                if kind=='bytes':output.write(b'x'*(1024*1024))
        except OSError as error:
            if error.errno!=errno.ENOSPC:raise
            return {'errno':error.errno,'mode':kind,'attempted_files':index+1}
    raise AssertionError('Private filesystem did not enforce its quota.')


def release(volume):
    for index in range(256):(volume/f'.pressure-{index:03d}').unlink(missing_ok=True)


def disk_worker(packet):
    original=rpc.SyntheticWitnessEndpoint.exchange;armed=[True]
    def exchange(endpoint,raw):
        finish=json.loads(raw)['operation']['op']=='finish' and armed[0]
        if finish and packet.get('disk_fault')=='before_finish':
            fill(Path(packet['volume']));armed[0]=False;print('enospc',flush=True)
        reply=original(endpoint,raw)
        if finish and packet.get('disk_fault')=='after_finish':
            if reply[0]!=200:raise AssertionError('Expected committed finish.')
            fill(Path(packet['volume']));print('enospc',flush=True);os._exit(74)
        return reply
    rpc.SyntheticWitnessEndpoint.exchange=exchange
    process.worker(packet)


@contextmanager
def serving(values):
    with patch.object(process,'BOOTSTRAP',WORKER),process.process_server(values) as result:yield result


def namespace_worker(packet):
    volume=Path(packet['volume']);fixture=volume.parent;root=Path(packet['root']).resolve()
    if (packet.get('synthetic_only') is not True or packet.get('approved') is not True
            or volume.name!='volume' or not fixture.name.startswith('.fixtures-disk-')
            or fixture.parent.resolve()!=root or volume.is_symlink() or fixture.is_symlink()
            or any(volume.iterdir()) or os.readlink('/proc/self/ns/mnt')==packet['parent_mount_ns']):
        raise PermissionError('Explicit empty fake fixture in a private mount namespace required.')
    group=Path('/sys/fs/cgroup')/next(line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines()
                                    if line.startswith('0::')).lstrip('/')
    limits={name:(group/name).read_text().strip() for name in ('memory.max','memory.swap.max','pids.max','cpu.max')}
    assert limits=={'memory.max':'268435456','memory.swap.max':'0','pids.max':'16','cpu.max':'25000 100000'}
    subprocess.run(['mount','-t','tmpfs','-o','size=8m,nr_inodes=128,nosuid,nodev,noexec,mode=0700',
                    'tmpfs',str(volume)],check=True,capture_output=True)
    stats=os.statvfs(volume)
    assert stats.f_blocks*stats.f_frsize==QUOTA_BYTES and stats.f_files==QUOTA_INODES
    # shortcut: volatile private tmpfs proves quota errors, qualify durable target storage separately.
    outside=fixture/'host';outside.mkdir();tempfile.tempdir=str(outside);os.environ['SQLITE_TMPDIR']=str(volume)
    check=unittest.TestCase();action=packet['action'];pressure=None
    f=(network.NetworkAuthorityChecks if action=='authority' else protocol.WitnessServiceChecks)(methodName='runTest')
    try:
        f.setUp();f.endpoint.enable_retirement(approved=True)
        home=f.f.home if action=='authority' else f.home
        tls.certificates(home)
        shutil.copyfile(f.w.path,volume/'witness.sqlite');f.w.path=volume/'witness.sqlite'
        values=process.packet(home,f.w.path,service='a'*32,client='b'*32,
            lineage=f.lineage,key=f.protocol_key if action=='authority' else f.key,
            now=f.f.now if action=='authority' else f.now)
        values['volume']=str(volume)
        if action=='authority':
            values['disk_fault']='before_finish';request=f.f.packet()
            with serving(values) as (_,client,signals):
                f.client=client;f.a=f.open()
                with check.assertRaises(OSError):f.call(request)
                check.assertEqual(signals.get(timeout=5),'enospc')
            committed=f.local();check.assertEqual(f.journal()['phase'],'committed')
            check.assertGreater(committed.anchor.sequence,f.initial.anchor.sequence)
            release(volume);values.pop('disk_fault')
            with serving(values) as (_,client,_):
                f.client=client;f.a=f.open()
                with check.assertRaises(Conflict):f.a.head(f.lineage)
                reply=f.reconcile();check.assertEqual(reply['anchor'],committed.anchor)
                check.assertNotIn('result',reply);check.assertNotIn('grant',reply)
                check.assertEqual(f.journal()['phase'],'idle')
                saved=f.call(request);check.assertEqual(f.call(request),saved)
                check.assertEqual(f.local(),committed)
                generation=client.observe()['generation']
                client.retire(committed,f.digest,generation=generation)
            pressure={'errno':errno.ENOSPC,'phase':'witness_finish_after_encrypted_source_commit'}
        else:
            reserved=None
            if action not in ('prepare_bytes','prepare_inodes'):
                with serving(values) as (_,client,_):
                    reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
                    if action=='retire':client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
            if action=='committed_reply_loss':
                values['disk_fault']='after_finish'
                with serving(values) as (child,client,signals):
                    with check.assertRaises(OSError):client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
                    check.assertEqual(signals.get(timeout=5),'enospc');check.assertEqual(child.wait(timeout=5),74)
                pressure={'errno':errno.ENOSPC,'phase':'after_finish_commit_before_reply'}
                values.pop('disk_fault')
            else:
                with serving(values) as (_,client,_):
                    pressure=fill(volume,'inodes' if action=='prepare_inodes' else 'bytes')
                    full=os.statvfs(volume)
                    check.assertEqual(full.f_favail if action=='prepare_inodes' else full.f_bavail,0)
                    with check.assertRaises(OSError):
                        if action.startswith('prepare'):client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
                        elif action=='finish':client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
                        else:client.retire(f.target,f.digest,generation=1)
            release(volume)
            with serving(values) as (_,client,_):
                head=client.observe();counters=f.endpoint.capacity()
                check.assertEqual(head['generation'],0 if action.startswith('prepare') else 1)
                check.assertEqual(head['state'],f.target if action in ('retire','committed_reply_loss') else f.initial)
                check.assertEqual(head['reservation_id'],'1'*32 if action=='finish' else None)
                check.assertEqual(counters['receipts'],0 if action.startswith('prepare') else 1 if action=='finish' else 2)
                check.assertEqual(counters['retired_generation'],0)
                if action.startswith('prepare'):
                    reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
                if action!='retire':client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
                check.assertEqual(client.retire(f.target,f.digest,generation=1)['retired_generation'],1)
            check.assertEqual(f.w.head(f.lineage),(f.target,f.digest))
        check.assertEqual(f.endpoint.capacity()['receipts'],0)
        print(json.dumps({'action':action,'passed':True,'pressure':pressure,'quota_bytes':QUOTA_BYTES,
                          'quota_inodes':QUOTA_INODES,'cgroup_limits':limits,'database_bytes':f.w.path.stat().st_size}))
    finally:
        f.doCleanups();release(volume)


def run_probe(action):
    if sys.platform!='linux':raise OSError('Linux private namespaces/cgroups required; no unbounded fallback.')
    if action not in ACTIONS:raise ValueError('Unknown finite fake-data disk probe.')
    root=Path(__file__).resolve().parent;unit='lya-synthetic-disk-'+uuid.uuid4().hex+'.service'
    prefix=['systemd-run','--user','--quiet','--pipe','--wait','--collect','--unit='+unit]
    for setting in cgroup.PROPERTIES:prefix+=['--property='+setting]
    with tempfile.TemporaryDirectory(prefix='.fixtures-disk-',dir=root) as folder:
        volume=Path(folder)/'volume';volume.mkdir()
        packet={'action':action,'root':str(root),'volume':str(volume),'synthetic_only':True,'approved':True,
                'parent_mount_ns':os.readlink('/proc/self/ns/mnt')}
        try:
            result=subprocess.run(prefix+['unshare','--user','--map-root-user','--mount','--pid','--fork',
                '--kill-child=KILL','--propagation','private',sys.executable,'-I','-B','-c',BOOTSTRAP],
                input=json.dumps(packet)+'\n',capture_output=True,text=True,timeout=65)
            if result.returncode:raise AssertionError('Fake disk probe failed: '+result.stderr[-3500:])
            report=json.loads(result.stdout)
            if any(volume.iterdir()):raise AssertionError('Namespace mount leaked files into the host volume directory.')
            METRICS[action]=report;return report
        finally:
            cgroup.control(unit,'stop');cgroup.control(unit,'reset-failed')


class DiskContractChecks(unittest.TestCase):
    def test_unsupported_platform_and_unknown_probe_refuse_before_launch(self):
        with patch.object(sys,'platform','win32'):
            with self.assertRaises(OSError):run_probe('prepare_bytes')
        with patch.object(sys,'platform','linux'):
            with self.assertRaises(ValueError):run_probe('not_a_probe')


@unittest.skipUnless(sys.platform=='linux','Actual ENOSPC qualification requires Linux private namespaces.')
class LinuxWitnessDiskChecks(unittest.TestCase):
    def test_bytes_and_inode_exhaustion_block_prepare_without_a_receipt(self):
        for action in ('prepare_bytes','prepare_inodes'):
            with self.subTest(action=action):self.assertTrue(run_probe(action)['passed'])

    def test_disk_full_preserves_pending_finish_and_exact_retry(self):
        self.assertTrue(run_probe('finish')['passed'])

    def test_disk_full_cannot_advance_retirement_floor_or_discard_receipts(self):
        self.assertTrue(run_probe('retire')['passed'])

    def test_committed_finish_with_disk_full_reply_loss_retries_after_restart(self):
        self.assertTrue(run_probe('committed_reply_loss')['passed'])

    def test_encrypted_source_commit_reconciles_after_witness_disk_full(self):
        self.assertTrue(run_probe('authority')['passed'])


if __name__=='__main__':unittest.main()
