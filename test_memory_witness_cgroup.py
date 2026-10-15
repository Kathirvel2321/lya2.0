"""Temporary Linux user services, fake keys and loopback only; no installed units."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from brain import memory_witness_service as rpc
import test_memory_witness_process as process
import test_memory_witness_service as protocol
import test_memory_witness_tls as tls


PROPERTIES=('MemoryMax=256M','MemorySwapMax=0','OOMPolicy=kill','TasksMax=16',
            'CPUQuota=25%','CPUQuotaPeriodSec=100ms','LimitNOFILE=64','LimitCORE=0',
            'LimitFSIZE=8M','RuntimeMaxSec=60','TimeoutStopSec=5','KillMode=control-group')
BOOTSTRAP="import json,sys; p=json.loads(sys.stdin.readline()); sys.path.insert(0,p.pop('root')); from test_memory_witness_cgroup import cgroup_worker; cgroup_worker(p)"
METRICS={}


def cgroup_worker(packet):
    import resource
    for kind,expected in ((resource.RLIMIT_NOFILE,64),(resource.RLIMIT_FSIZE,8*1024*1024),
                          (resource.RLIMIT_CORE,0),(resource.RLIMIT_CPU,resource.RLIM_INFINITY)):
        if resource.getrlimit(kind)!=(expected,expected):raise AssertionError('Unexpected service rlimit.')
    if packet.get('probe')=='descendant':
        subprocess.Popen([sys.executable,'-I','-B','-c','import time; time.sleep(60)'],
                         stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    original=rpc.SyntheticWitnessEndpoint._operation
    def operation(endpoint,db,request,request_id):
        result=original(endpoint,db,request,request_id)
        if request['op']=='prepare':
            if packet.get('probe')=='oom':bytearray(384*1024*1024)
            elif packet.get('probe')=='cpu':
                end=time.process_time()+.8
                while time.process_time()<end:pass
                print('cpu-done',flush=True)
            elif packet.get('probe')=='tasks':
                stop=threading.Event();threads=[]
                try:
                    for _ in range(40):
                        thread=threading.Thread(target=stop.wait);thread.start();threads.append(thread)
                except RuntimeError:pass
                else:raise AssertionError('Task ceiling was not enforced.')
                finally:
                    stop.set()
                    for thread in threads:thread.join(2)
        return result
    rpc.SyntheticWitnessEndpoint._operation=operation
    process.worker(packet)


def control(unit,*args):
    return subprocess.run(['systemctl','--user',*args,unit],capture_output=True,text=True,timeout=8)


def group_for(unit):
    result=control(unit,'show','--property=ControlGroup','--value')
    if result.returncode:raise AssertionError('Temporary synthetic service unavailable.')
    root=Path('/sys/fs/cgroup').resolve();group=(root/result.stdout.strip().lstrip('/')).resolve()
    if root not in group.parents or group.name!=unit:raise AssertionError('Unexpected synthetic cgroup.')
    return group


def counters(group,name):
    return {key:int(value) for key,value in (line.split() for line in (group/name).read_text().splitlines())}


@contextmanager
def managed_worker(values):
    unit='lya-synthetic-witness-'+uuid.uuid4().hex+'.service'
    prefix=['systemd-run','--user','--quiet','--pipe','--wait','--unit='+unit]
    for setting in PROPERTIES:prefix+=['--property='+setting]
    # shortcut: finite user-service lab, qualify a separate supervisor/placement before production.
    proxy=SimpleNamespace(Popen=lambda args,**kwargs:subprocess.Popen(prefix+args,**kwargs),
                          PIPE=subprocess.PIPE,DEVNULL=subprocess.DEVNULL,TimeoutExpired=subprocess.TimeoutExpired)
    group=None
    try:
        with patch.object(process,'subprocess',proxy),patch.object(process,'BOOTSTRAP',BOOTSTRAP):
            with process.process_server(values) as (child,client,signals):
                group=group_for(unit)
                yield child,client,signals,unit,group
    finally:
        stopped=control(unit,'stop')
        control(unit,'reset-failed')
        if stopped.returncode and control(unit,'is-active').stdout.strip() not in ('inactive','failed','unknown'):
            raise AssertionError('Temporary synthetic service could not be stopped.')
        if group is not None and group.exists() and counters(group,'cgroup.events')['populated']:
            raise AssertionError('Synthetic cgroup still contains processes after cleanup.')


@unittest.skipUnless(sys.platform=='linux','Actual cgroup qualification requires Linux/systemd user services.')
class LinuxWitnessCgroupChecks(unittest.TestCase):
    def fixture(self):
        f=protocol.WitnessServiceChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
        f.endpoint.enable_retirement(approved=True);tls.certificates(f.home)
        return f

    def values(self,f,**kwargs):
        values=process.packet(f.home,f.w.path,service=f.service,client=f.client_id,lineage=f.lineage,
                              key=f.key,now=f.now)
        values.update(kwargs);return values

    def test_profile_and_repeated_tls_transactions_remain_bounded(self):
        f=self.fixture()
        with managed_worker(self.values(f,probe='descendant')) as (_,client,_,_,group):
            limits={name:(group/name).read_text().strip() for name in
                    ('memory.max','memory.swap.max','memory.oom.group','pids.max','cpu.max')}
            self.assertEqual(limits,{'memory.max':'268435456','memory.swap.max':'0','memory.oom.group':'1',
                                     'pids.max':'16','cpu.max':'25000 100000'})
            self.assertGreaterEqual(int((group/'pids.current').read_text()),3)
            started=time.monotonic();state=f.initial
            for generation in range(1,41):
                self.assertEqual(client.observe()['state'],state)
                reserved=client.prepare(state,f.digest,request_id=f'{generation*2:032x}',expected_generation=generation-1)
                target=replace(state,writer_epoch=state.writer_epoch+1)
                client.finish(reserved,state,target,f.digest,request_id=f'{generation*2+1:032x}')
                self.assertEqual(client.retire(target,f.digest,generation=generation)['retired_generation'],generation)
                state=target
            current=client.observe();self.assertEqual(current['generation'],40);self.assertIsNone(current['reservation_id'])
            self.assertEqual(f.endpoint.capacity()['receipts'],0)
            self.assertLessEqual(f.endpoint.capacity()['database_bytes'],rpc.MAX_DATABASE_BYTES)
            METRICS['repeated_tls']={'rounds':40,'elapsed_seconds':round(time.monotonic()-started,3),
                'limits':limits,'memory_peak_bytes':int((group/'memory.peak').read_text()),
                'cpu':counters(group,'cpu.stat'),'database_bytes':f.endpoint.capacity()['database_bytes']}

    def test_cpu_rate_throttles_work_without_a_lifetime_cpu_kill(self):
        f=self.fixture()
        with managed_worker(self.values(f,probe='cpu')) as (child,client,signals,_,group):
            before=counters(group,'cpu.stat')
            with self.assertRaises(OSError):client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
            self.assertEqual(signals.get(timeout=10),'cpu-done')
            head=client.observe();self.assertEqual(head['reservation_id'],'1'*32)
            self.assertIsNone(child.poll())
            after=counters(group,'cpu.stat');self.assertGreater(after['nr_throttled'],before['nr_throttled'])
            METRICS['cpu_throttle']={name:after[name]-before[name] for name in ('usage_usec','nr_throttled','throttled_usec')}

    def test_task_limit_rejects_excess_threads_and_service_recovers(self):
        f=self.fixture()
        with managed_worker(self.values(f,probe='tasks')) as (_,client,_,_,group):
            before=counters(group,'pids.events')['max']
            reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
            self.assertGreater(counters(group,'pids.events')['max'],before)
            client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
            self.assertEqual(client.observe()['state'],f.target)
            METRICS['tasks']={'limit':int((group/'pids.max').read_text()),'denials':counters(group,'pids.events')['max']-before}

    def test_repeated_stalled_connections_release_service_for_healthy_requests(self):
        f=self.fixture();blocked=0
        with managed_worker(self.values(f)) as (_,client,_,_,group):
            for _ in range(3):
                with socket.create_connection(('127.0.0.1',client.port),timeout=3) as raw:
                    with client.ssl_context.wrap_socket(raw,server_hostname='127.0.0.1') as stalled:
                        stalled.sendall(b'POST /witness HTTP/1.0\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{')
                        try:self.assertEqual(client.observe()['state'],f.initial)
                        except OSError:blocked+=1
                self.assertEqual(client.observe()['state'],f.initial)
            head=client.observe();self.assertIsNone(head['reservation_id']);self.assertEqual(head['generation'],0)
            self.assertEqual(f.endpoint.capacity()['receipts'],0)
            METRICS['connection_pressure']={'waves':3,'healthy_attempts_during_stall':3,
                'healthy_attempts_timed_out':blocked,'recovery_observations_passed':3,
                'memory_peak_bytes':int((group/'memory.peak').read_text())}

    def test_memory_cgroup_kill_rolls_back_prepare_and_restart_retries(self):
        f=self.fixture()
        with managed_worker(self.values(f,probe='oom')) as (child,client,_,unit,group):
            with self.assertRaises(OSError):client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
            self.assertNotEqual(child.wait(timeout=10),0)
            result=control(unit,'show','--property=Result','--value')
            self.assertEqual(result.stdout.strip(),'oom-kill')
            METRICS['memory_failure']={'service_result':'oom-kill'}
        with managed_worker(self.values(f)) as (_,client,_,_,_):
            head=client.observe();self.assertEqual(head['state'],f.initial)
            self.assertEqual(head['generation'],0);self.assertIsNone(head['reservation_id'])
            self.assertEqual(f.endpoint.capacity()['receipts'],0)
            self.assertEqual(client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)['generation'],1)


if __name__=='__main__':unittest.main()
