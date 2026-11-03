"""Signed fake sessions, injected exact approvals and temporary encrypted memory."""
import base64
from dataclasses import asdict
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

from brain.conversation import desktop_turn
from brain.shared_memory import SharedMemoryService, SharedMemoryUncertain, parse_command
from cloud.shared_memory import OracleSharedMemory, configured_service, desktop_request
from cloud.mobile import Connection
from test_conversation_contract import ContractChecks
from tools.prepare_shared_memory import prepare


class SharedMemoryChecks(unittest.TestCase):
    def setUp(self):
        self.f = ContractChecks(methodName='runTest'); self.addCleanup(self.f.doCleanups); self.f.setUp()
        temp = tempfile.TemporaryDirectory(prefix='sm-'); self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.config = prepare(self.home / 'state', self.f.binding, synthetic_only=True, approved=True, clock=lambda: self.f.now)
        self.service = configured_service(self.config, clock=lambda: self.f.now)
        self.f.brain.shared_memory = self.service
        self.f.brain.approve = lambda *args: True  # Trusted verifier stub; sessions above use real fake-key signatures.
        self.f.phone.app.shared_memory = self.service
        self.f.fresh_phone_owner()
        self.number = 0

    def phone(self, command, **kwargs):
        self.number += 1
        return self.f.phone.app.chat(self.f.token, f'{self.number:032x}', 'shared memory demo: ' + command, **kwargs)

    def desktop(self, command):
        answer = self.f.brain.respond('shared memory demo: ' + command)
        self.assertEqual(answer.route, 'shared-memory', answer.text)
        return answer.text

    def turn(self, text, request_id='e' * 32):
        return desktop_turn(self.f.brain, dict(id=request_id, text='shared memory demo: ' + text))

    def test_shared_two_clients_correct_restart_forget_and_no_public_model_history(self):
        self.desktop('remember permanent colour = SYNTHETIC_BLUE')
        self.assertIn('SYNTHETIC_BLUE', self.phone('recall colour')['text'])
        self.phone('correct colour = SYNTHETIC_GREEN')
        self.assertIn('SYNTHETIC_GREEN', self.desktop('recall colour'))
        restarted = configured_service(self.config, clock=lambda: self.f.now)
        self.f.brain.shared_memory = restarted
        old = self.f.phone.app
        self.f.phone.app = Connection(old.origin, old.store, old.infer, clock=old.clock, shared_memory=restarted)
        ticket = self.f.phone.app.begin('login')['ticket']
        _, self.f.token = self.f.phone.app.complete(ticket, self.f.phone.response(ticket))
        self.f.fresh_phone_owner()
        self.assertIn('SYNTHETIC_GREEN', self.phone('recall colour')['text'])
        self.phone('forget colour')
        self.assertNotIn('SYNTHETIC_GREEN', self.desktop('recall colour'))
        self.assertEqual(self.f.brain.history, [])
        self.assertEqual(self.f.phone.app.session(self.f.token)['history'], [])
        self.assertEqual(self.f.phone.calls, [])
        calls = []
        self.f.brain.client = lambda messages: calls.append(messages) or 'Public reply.'
        self.f.phone.app.infer = lambda messages, cancelled: calls.append(messages) or 'Public reply.'
        self.f.brain.respond('Hello there')
        self.f.phone.app.chat(self.f.token, 'd' * 32, 'Hello there')
        self.assertNotIn('SYNTHETIC_BLUE', str(calls)); self.assertNotIn('SYNTHETIC_GREEN', str(calls))
        for path in (self.home / 'state/authority/objects').glob('*/live.sqlite'):
            self.assertFalse(path.read_bytes().startswith(b'SQLite format 3'))

    def test_shared_native_pinned_transport_and_control_binding_use_one_authority(self):
        (self.home / 'fake-key').write_bytes(b'FAKE_SSH_KEY_NOT_USED')
        (self.home / 'oracle_known_hosts.local').write_text('FAKE_PIN_NOT_USED')
        runtime_config=self.home/'runtime.json'
        runtime_config.write_text(json.dumps(dict(self.config,origin=self.f.phone.app.origin)))
        seen = []
        def exchange(command, body, cancelled, **kwargs):
            seen.append((command, body))
            root=Path(__file__).resolve().parent
            packet=dict(request=json.loads(body),config=str(runtime_config),auth=str(self.f.phone.store.path),
                        now=self.f.now,imports=[str(root),str(root/'review/2026-10-12-memory-hardening/.drivers')])
            program='''import json,pathlib,sys,time
p=json.load(sys.stdin);sys.path[:0]=p['imports'];time.time=lambda:p['now']
from cloud import mobile_runtime as runtime
import io
runtime.CONFIG=pathlib.Path(p['config']);runtime.STATE=pathlib.Path(p['auth'])
sys.argv=['control.py','shared-memory'];sys.stdin=io.TextIOWrapper(io.BytesIO(json.dumps(p['request']).encode()))
runtime.main()
'''
            run=subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(packet),text=True,
                               capture_output=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,0,'Isolated shared runtime failed; raw output withheld.')
            self.assertEqual(run.stderr,'')
            return SimpleNamespace(returncode=run.returncode,stdout=run.stdout)
        client = OracleSharedMemory(dict(enabled=True, mode='synthetic', host='192.0.2.1', key_file='fake-key'), exchange=exchange)
        with patch('cloud.shared_memory.ROOT', self.home):
            self.f.brain.shared_memory = client
            self.desktop('remember permanent colour = SYNTHETIC_TRANSPORT')
        self.assertIn('SYNTHETIC_TRANSPORT', self.phone('recall colour')['text'])
        self.assertNotIn('SYNTHETIC_TRANSPORT', str(seen[0][0]))
        self.assertIn('StrictHostKeyChecking=yes', seen[0][0])
        self.assertTrue(seen[0][0][-1].endswith('control.py shared-memory'))
        packet = json.loads(seen[0][1]); packet['context']['principal'] = 'b' * 64
        with self.assertRaises(PermissionError):desktop_request(packet, self.f.phone.store, self.service, clock=lambda: self.f.now)

    def test_shared_exact_retry_is_idempotent_and_changed_text_is_rejected(self):
        self.desktop('remember permanent colour = blue')
        rid = 'a' * 32; text = 'shared memory demo: correct colour = green'
        first = self.f.phone.app.chat(self.f.token, rid, text)
        self.assertEqual(self.f.phone.app.chat(self.f.token, rid, text), first)
        with self.assertRaises(PermissionError):self.f.phone.app.chat(self.f.token, rid, text + ' changed')
        turn = self.turn('forget colour')
        self.assertEqual(self.service.respond(turn), self.service.respond(turn))
        with self.assertRaises(ValueError):self.service.respond(self.turn('forget another label'))
        with self.service.authority._repository._db() as db:
            _, _, memory, *_ = self.service.authority._entry(db, self.service.grant.lineage)
            with memory._db() as source:
                self.assertEqual(source.execute('SELECT revision,deleted FROM memories').fetchone()['revision'], 3)
                self.assertEqual(source.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 3)

    def test_shared_interrupted_publication_keeps_native_request_and_blocks_other_writes(self):
        command = 'shared memory demo: remember permanent colour = SYNTHETIC_COMMITTED'
        with patch.object(self.service.authority, '_stage', side_effect=OSError('FAKE unavailable')):
            answer = self.f.brain.respond(command)
        self.assertEqual(answer.route, 'blocked'); self.assertIn('unconfirmed', answer.text)
        request_id = self.f.brain._shared_pending[1]
        self.assertEqual(self.f.brain.respond('shared memory demo: remember permanent other = new').route, 'blocked')
        self.service.authority.reconcile_publication(self.service.grant.lineage, approved=True)
        self.assertEqual(self.f.brain.respond(command).route, 'shared-memory')
        self.assertIsNone(self.f.brain._shared_pending)
        self.assertIn('SYNTHETIC_COMMITTED', self.phone('recall colour')['text'])
        with self.service.authority._repository._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM shared_requests WHERE request_id=?', (request_id,)).fetchone()[0], 1)

    def test_shared_delayed_correction_does_not_overwrite_newer_phone_update(self):
        self.desktop('remember permanent colour = blue')
        turn = self.turn('correct colour = delayed')
        with patch.object(self.service.authority, 'handle', side_effect=OSError('FAKE dispatch loss')):
            with self.assertRaises(SharedMemoryUncertain):self.service.respond(turn)
        self.phone('correct colour = newer')
        with self.assertRaises(SharedMemoryUncertain):self.service.respond(turn)
        self.service.authority.reconcile_publication(self.service.grant.lineage, approved=True)
        self.assertIn('newer', self.phone('recall colour')['text'])

    def test_shared_owner_expiry_cancellation_binding_and_private_mode_fail_closed(self):
        self.f.phone.app.session(self.f.token)['owner_until'] = 0
        with self.assertRaises(PermissionError):self.phone('remember permanent colour = blocked')
        self.f.fresh_phone_owner()
        turn = self.turn('remember permanent colour = blocked')
        turn._cancelled.set()
        with self.assertRaises(InterruptedError):self.service.respond(turn)
        self.f.brain.private_mode = True
        self.assertEqual(self.f.brain.respond('shared memory demo: recall colour').route, 'blocked')
        self.f.brain.private_mode = False
        self.f.brain.approve = lambda *args: False
        self.assertEqual(self.f.brain.respond('shared memory demo: remember permanent colour = blocked').route, 'blocked')
        with self.f.phone.store.db() as db:db.execute('UPDATE binding SET owner=?', ('b' * 64,))
        with self.assertRaises(PermissionError):self.phone('recall colour')
        self.assertEqual(self.f.phone.calls, [])

    def test_shared_voice_rechecks_owner_before_delivery_and_disabled_route_never_infers(self):
        self.desktop('remember permanent colour = blue')
        def speak(text, cancelled):
            self.f.now += 301
            output = io.BytesIO()
            with wave.open(output, 'wb') as wav:
                wav.setparams((1, 2, 22050, 0, 'NONE', 'not compressed')); wav.writeframes(b'\0' * 4410)
            return base64.b64encode(output.getvalue()).decode()
        self.f.phone.app.speaker = speak
        with self.assertRaises(PermissionError):self.phone('recall colour', spoken=True)
        self.f.phone.app.shared_memory = None
        with self.assertRaises(ValueError):self.phone('recall colour')
        self.assertEqual(self.f.phone.calls, [])

    def test_shared_preparation_and_parser_refuse_unsafe_or_implicit_configuration(self):
        for flags in ({'approved': False, 'synthetic_only': True}, {'approved': True, 'synthetic_only': 1}):
            with self.assertRaises(PermissionError):prepare(self.home / 'refused', self.f.binding, **flags)
        self.assertFalse((self.home / 'refused').exists())
        with self.assertRaises(FileExistsError):prepare(self.home / 'state', self.f.binding, approved=True, synthetic_only=True)
        with self.assertRaises(ValueError):configured_service({'shared_memory': {'mode': 'production', 'state_file': 'unused'}})
        with self.assertRaises(PermissionError):SharedMemoryService(self.service.authority, self.service.grant)
        for command in ('shared memory', 'shared memory demo: erase everything',
                        'shared memory demo: remember session colour = blue', 'shared memory demo: remember permanent password = hidden'):
            with self.assertRaises((ValueError, PermissionError)):parse_command(command, 'f' * 32)
        packet, label, action = parse_command('shared memory Demo: remember permanent நிறம் = நீலம்', 'f' * 32)
        self.assertEqual((packet['project'], label, action), ('demo', 'நிறம்', 'memory_write'))


if __name__ == '__main__':unittest.main()
