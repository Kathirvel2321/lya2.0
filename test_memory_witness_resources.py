"""Linux resource ceilings in owned fake-data children only; never cap the runner."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

from brain import memory_witness_budget as budget
from brain import memory_witness_service as rpc
import test_memory_witness_process as process
import test_memory_witness_service as protocol
import test_memory_witness_tls as tls


PROBE = r'''
import errno,json,mmap,os,resource,sys
p=json.loads(sys.stdin.readline());sys.path.insert(0,p['root'])
from brain.memory_witness_budget import apply_synthetic_budget,ADDRESS_SPACE_BYTES
if p['action']=='preallocated':
    with mmap.mmap(-1,ADDRESS_SPACE_BYTES):
        try:apply_synthetic_budget(synthetic_only=True,approved=True)
        except OSError:print(json.dumps({'rejected':'preallocated'}))
        else:raise AssertionError('Already oversized worker was accepted')
    sys.exit(0)
if p['action']=='stricter':resource.setrlimit(resource.RLIMIT_NOFILE,(32,48))
limits=apply_synthetic_budget(synthetic_only=True,approved=True)
if p['action']=='memory':
    try:bytearray(ADDRESS_SPACE_BYTES)
    except MemoryError:print(json.dumps({'rejected':'memory'}))
    else:raise AssertionError('Allocation unexpectedly succeeded')
elif p['action']=='files':
    handles=[]
    try:
        for _ in range(128):handles.append(open(os.devnull,'rb'))
    except OSError as error:
        assert error.errno==errno.EMFILE
        print(json.dumps({'rejected':'files','opened':len(handles)}))
    else:raise AssertionError('Descriptor allocation unexpectedly succeeded')
    finally:
        for handle in handles:handle.close()
else:print(json.dumps(limits))
'''

BOUNDED_BOOTSTRAP = "import json,sys; p=json.loads(sys.stdin.readline()); sys.path.insert(0,p.pop('root')); from test_memory_witness_resources import bounded_worker; bounded_worker(p)"


def bounded_worker(packet):
    """Inject a resource fault inside a real signed prepare transaction."""
    original=rpc.SyntheticWitnessEndpoint._operation
    def fault(endpoint,db,operation,request_id):
        result=original(endpoint,db,operation,request_id)
        if operation['op']=='prepare':
            if packet['probe']=='memory':bytearray(budget.ADDRESS_SPACE_BYTES)
            elif packet['probe']=='file':
                with (Path(packet['home'])/'bounded-output.bin').open('wb',buffering=0) as output:
                    for _ in range(10):output.write(b'x'*(1024*1024))
            elif packet['probe']=='cpu':
                while True:pass
        return result
    rpc.SyntheticWitnessEndpoint._operation=fault
    process.worker(packet)


class BudgetContractChecks(unittest.TestCase):
    def test_explicit_opt_in_and_supported_platform_are_required_before_limits_change(self):
        for values in ({},{'synthetic_only':True},{'approved':True},
                       {'synthetic_only':1,'approved':True},{'synthetic_only':True,'approved':1}):
            with self.assertRaises(PermissionError):budget.apply_synthetic_budget(**values)
        with patch.object(budget.sys,'platform','win32'):
            with self.assertRaises(OSError):budget.apply_synthetic_budget(synthetic_only=True,approved=True)


@unittest.skipUnless(sys.platform=='linux','Actual process limits require Linux.')
class LinuxWitnessResourceChecks(unittest.TestCase):
    def fixture(self):
        f=protocol.WitnessServiceChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
        f.endpoint.enable_retirement(approved=True);tls.certificates(f.home)
        return f

    def values(self,f,**kwargs):
        values=process.packet(f.home,f.w.path,service=f.service,client=f.client_id,lineage=f.lineage,
                              key=f.key,now=f.now)
        values.update(process_budget=True,**kwargs)
        return values

    def probe(self,action):
        packet=dict(root=str(Path(__file__).resolve().parent),action=action)
        result=subprocess.run([sys.executable,'-I','-B','-c',PROBE],input=json.dumps(packet)+'\n',
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,'Synthetic budget probe failed; raw output withheld.')
        return json.loads(result.stdout)

    def test_profile_is_applied_and_normal_tls_operations_work_under_it(self):
        self.assertEqual(self.probe('profile'),{name:[ceiling,ceiling] for name,ceiling in budget.LIMITS})
        self.assertEqual(self.probe('preallocated'),{'rejected':'preallocated'})
        f=self.fixture()
        with process.process_server(self.values(f)) as (_,client,_):
            for _ in range(20):self.assertEqual(client.observe()['state'],f.initial)
            reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
            client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
            self.assertEqual(client.retire(f.target,f.digest,generation=1)['retired_generation'],1)
        self.assertEqual(f.w.head(f.lineage),(f.target,f.digest))

    def test_address_space_and_descriptor_exhaustion_are_rejected_by_kernel_limits(self):
        self.assertEqual(self.probe('memory'),{'rejected':'memory'})
        result=self.probe('files');self.assertEqual(result['rejected'],'files')
        self.assertLessEqual(result['opened'],budget.OPEN_FILES)
        self.assertEqual(self.probe('stricter')['RLIMIT_NOFILE'],[32,48])

    def test_memory_and_file_limit_failures_roll_back_a_signed_prepare(self):
        for probe in ('memory','file'):
            with self.subTest(probe=probe):
                f=self.fixture()
                with patch.object(process,'BOOTSTRAP',BOUNDED_BOOTSTRAP),process.process_server(self.values(f,probe=probe)) as (_,client,_):
                    with self.assertRaises(OSError):client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
                    head=client.observe();self.assertEqual(head['state'],f.initial)
                    self.assertIsNone(head['reservation_id']);self.assertEqual(head['generation'],0)
                    self.assertEqual(f.endpoint.capacity()['receipts'],0)
                    if probe=='file':self.assertLessEqual((f.home/'bounded-output.bin').stat().st_size,budget.FILE_BYTES)
                with process.process_server(self.values(f)) as (_,client,_):
                    self.assertEqual(client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)['generation'],1)

    def test_cpu_ceiling_terminates_only_owned_worker_and_restart_rolls_back_pending_changes(self):
        f=self.fixture()
        with patch.object(process,'BOOTSTRAP',BOUNDED_BOOTSTRAP),process.process_server(self.values(f,probe='cpu')) as (child,client,_):
            with self.assertRaises(OSError):client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
            self.assertEqual(child.wait(timeout=20),-signal.SIGKILL)
        with process.process_server(self.values(f)) as (_,client,_):
            head=client.observe();self.assertEqual(head['state'],f.initial)
            self.assertIsNone(head['reservation_id']);self.assertEqual(head['generation'],0)
            self.assertEqual(f.endpoint.capacity()['receipts'],0)
            self.assertEqual(client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)['generation'],1)


if __name__=='__main__':unittest.main()
