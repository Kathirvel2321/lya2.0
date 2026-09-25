"""T02 fault injection, fake credentials and disposable SQLite only."""
import io
import json
from pathlib import Path
import tempfile
import threading
import sys
import time
import unittest
from unittest.mock import Mock
import urllib.error
from cloud.router import State, route_request
from cloud.inference import infer


class BackupChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'state.sqlite'
        self.state=State(self.path)
        self.packet={'messages':[{'role':'user','content':'Synthetic'}],'sensitivity':'public'}
        self.config={'version':2,'routes':[{'id':p,'provider':p,'failure_domain':p,'model':'fixture','enabled':True,'tasks':['general'],'allow_private':False} for p in ['groq','nvidia']]}

    def tearDown(self): self.tmp.cleanup()

    def test_malformed_empty_and_exception_reach_backup(self):
        for bad in (None, {}, {'text':''}, {'error':'invalid_provider_response'}):
            with tempfile.TemporaryDirectory() as folder:
                call=Mock(side_effect=[bad,{'text':'Backup'}])
                result=route_request(self.packet,self.config,call,State(Path(folder)/'state'))
                self.assertEqual(result['route'],'nvidia')
                self.assertEqual(call.call_count,2)

    def test_direct_provider_labels_cannot_fake_independence(self):
        self.config['routes'][1].update(provider='groq', failure_domain='unrelated-label')
        call=Mock(return_value={'error':'provider_http_503'})
        route_request(self.packet,self.config,call,self.state)
        self.assertEqual(call.call_count,1)

    def test_token_allowance_is_atomic_and_persistent(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda n:self.state.reserve(str(n),100,2000000000,100,100),range(8)))
        self.assertEqual(results.count('ok'),1)
        self.assertEqual(State(self.path).reserve('x',100,2000000000,1,100),'daily_token_budget_exhausted')

    def test_no_backup_or_late_answer_after_cancellation(self):
        stop=threading.Event()
        def first(*_):
            stop.set()
            return {'error':'provider_http_503'}
        call=Mock(side_effect=first)
        result=route_request(self.packet,self.config,call,self.state,cancelled=stop.is_set)
        self.assertEqual(result['error'],'cancelled')
        self.assertEqual(call.call_count,1)

    def test_reservation_cannot_start_request_after_deadline(self):
        now=[0]
        reserve=self.state.reserve
        def slow(*args):
            result=reserve(*args)
            now[0]=19
            return result
        self.state.reserve=slow
        call=Mock()
        result=route_request(self.packet,self.config,call,self.state,monotonic=lambda:now[0])
        self.assertEqual(result['error'],'deadline_exceeded')
        call.assert_not_called()

    def test_success_after_deadline_is_discarded(self):
        now=[0]
        def slow(*_):
            now[0]=19
            return {'text':'Late'}
        result=route_request(self.packet,self.config,slow,self.state,monotonic=lambda:now[0])
        self.assertEqual(result['error'],'deadline_exceeded')

    def test_retry_after_respected_across_state_reload(self):
        result=route_request(self.packet,self.config,lambda *_:{'error':'provider_http_429','retry_after_seconds':300},self.state,clock=lambda:2000000000)
        self.assertEqual(len(result['attempts']),2)
        call=Mock()
        route_request(self.packet,self.config,call,State(self.path),clock=lambda:2000000100)
        call.assert_not_called()

    def test_invalid_body_and_retry_header_are_sanitized(self):
        config={'provider':'groq','model':'fixture','api_key':'FAKE'}
        result=infer(self.packet,config,lambda *_ ,**kw:io.BytesIO(b'not json FAKE'))
        self.assertEqual(result,{'error':'invalid_provider_response'})
        def limited(*a,**kw):
            raise urllib.error.HTTPError('https://example.invalid',429,'FAKE',{'Retry-After':'120'},None)
        result=infer(self.packet,config,limited)
        self.assertEqual(result,{'error':'provider_http_429','retry_after_seconds':120})

    def test_private_routes_and_pre_cancel_send_nothing(self):
        call=Mock()
        result=route_request({**self.packet,'sensitivity':'private'},self.config,call,self.state)
        self.assertEqual(result['error'],'no_eligible_route')
        result=route_request(self.packet,self.config,call,self.state,cancelled=lambda:True)
        self.assertEqual(result['error'],'cancelled')
        call.assert_not_called()

    def test_cooldown_cannot_be_shortened_by_concurrent_failure(self):
        self.state.fail('groq', 2000000300)
        self.state.fail('groq', 2000000030)
        self.assertEqual(self.state.reserve('groq', 100, 2000000100), 'cooldown')


    def test_openrouter_evaluation_requires_free_model_and_pinned_upstream(self):
        from cloud.evaluate_models import evaluate
        values={'OPENROUTER_API_KEY':'FAKE'}
        with self.assertRaises(ValueError):
            evaluate('openrouter','paid/model',values,lambda *a,**k: {'text':'x'},'nvidia')
        seen=[]
        def fake(packet,config,timeout):
            seen.append(config.copy())
            return {'text':'Synthetic answer'}
        report=evaluate('openrouter','deepseek/deepseek-v4-flash-0731:free',values,fake,'nvidia')
        self.assertTrue(report['completed'])
        self.assertEqual(len(seen),8)
        self.assertTrue(all(c['upstream_provider']=='nvidia' for c in seen))


class SessionChecks(unittest.TestCase):
    def test_line_protocol_completes_with_stdin_open(self):
        from cloud.ssh_session import exchange
        result = exchange([sys.executable, '-c', 'import sys; print(sys.stdin.readline().strip())'], 'synthetic', timeout=3)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'synthetic')

    def test_cancel_terminates_waiting_process(self):
        from cloud.ssh_session import exchange
        event = threading.Event()
        timer = threading.Timer(.2, event.set)
        start = time.monotonic()
        timer.start()
        try:
            with self.assertRaises(InterruptedError):
                exchange([sys.executable, '-c', 'import time; time.sleep(20)'], '{}', event, timeout=3)
        finally:
            timer.cancel()
        self.assertLess(time.monotonic() - start, 3)

    def test_timeout_terminates_waiting_process(self):
        from cloud.ssh_session import exchange
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            exchange([sys.executable, '-c', 'import time; time.sleep(20)'], '{}', timeout=.2)
        self.assertLess(time.monotonic() - start, 3)

    def test_pre_cancel_does_not_spawn(self):
        from cloud.ssh_session import exchange
        event = threading.Event()
        event.set()
        spawn = Mock()
        with self.assertRaises(InterruptedError):
            exchange([], '{}', event, popen=spawn)
        spawn.assert_not_called()

if __name__=='__main__': unittest.main()
