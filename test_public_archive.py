"""Synthetic documents, temporary folders and fake pinned SSH only."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storage.public_archive import PublicArchive, PublicCache, encoded
from cloud.public_archive import OraclePublicArchive, ArchiveUnavailable


def document(**changes):
    item = dict(owner='operator', project='atlas', id='python-doc', revision=1,
                title='Synthetic Python guide', source='https://example.invalid/guide',
                text='Synthetic turtles use asyncio for concurrent network tasks.',
                expires_at=None, sensitivity='public')
    return dict(item, **changes)


def put(item, expected=0, **changes):
    return dict(dict(op='put', owner=item['owner'], project=item['project'], record=item,
                     expected_revision=expected, reviewed_public=True), **changes)


def get(**changes):
    return dict(dict(op='get', owner='operator', project='atlas', id='python-doc', revision=1), **changes)


class ArchiveChecks(unittest.TestCase):
    def test_lifecycle_conflicts_restart_delete_and_independent_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            archive = PublicArchive(Path(root) / 'primary/archive.sqlite')
            item = document()
            self.assertEqual(archive.handle(put(item)), {'acknowledged': True, 'revision': 1})
            self.assertEqual(archive.handle(put(item))['revision'], 1)
            corrected = document(revision=2, text='Synthetic guide now uses threads.')
            with self.assertRaises(ValueError):
                archive.handle(put(corrected))
            archive.handle(put(corrected, 1))
            archive = PublicArchive(archive.path)
            self.assertIsNone(archive.handle(get())['record'])
            self.assertEqual(archive.handle(get(revision=2))['record'], corrected)
            archive.backup(Path(root) / 'independent.sqlite')
            with self.assertRaises(ValueError):
                archive.backup(Path(root) / 'independent.sqlite')
            deletion = dict(op='delete', owner='operator', project='atlas', id='python-doc', expected_revision=2)
            self.assertEqual(archive.handle(deletion)['revision'], 3)
            self.assertEqual(archive.handle(deletion)['revision'], 3)
            self.assertIsNone(archive.handle(get(revision=2))['record'])
            with self.assertRaises(ValueError):
                archive.handle(put(corrected, 1))
            recovered = PublicArchive(Path(root) / 'independent.sqlite')
            self.assertEqual(recovered.handle(get(revision=2))['record'], corrected)

    def test_rejections_happen_before_file_creation(self):
        packets = [put(document(sensitivity='private')), put(document(sensitivity='restricted')),
                   put(document(), reviewed_public=1), put(document(), reviewed_public=False),
                   put(document(), project='other'), put(document(), extra='secret'),
                   get(project='../escape'), get(revision=True), get(owner='x; echo fail'),
                   put(document(expires_at=float('nan'))), put(document(expires_at=1)),
                   put(document(text='x' * 24001)), put(document(revision=2)),
                   dict(op='execute', owner='operator', project='atlas'),
                   get(path='/other/store.sqlite')]
        with tempfile.TemporaryDirectory() as root:
            archive = PublicArchive(Path(root) / 'not-created/db.sqlite')
            for packet in packets:
                with self.subTest(packet=packet.get('op')):
                    with self.assertRaises((ValueError, PermissionError)):
                        archive.handle(packet)
                    self.assertFalse(archive.path.parent.exists())

    def test_search_scopes_expiry_and_no_query_operators(self):
        with tempfile.TemporaryDirectory() as root:
            now = [100]
            archive = PublicArchive(Path(root) / 'db.sqlite', clock=lambda: now[0])
            for owner, project in [('operator', 'atlas'), ('other', 'atlas'), ('operator', 'beta')]:
                archive.handle(put(document(owner=owner, project=project)))
            archive.handle(put(document(id='expiring', expires_at=101)))
            now[0] = 102
            request = dict(op='search', owner='operator', project='atlas', query='asyncio OR turtles NEAR(foo)')
            hits = archive.handle(request)['records']
            self.assertEqual([r['id'] for r in hits], ['python-doc'])
            self.assertTrue(all((r['owner'], r['project']) == ('operator', 'atlas') for r in hits))
            self.assertIsNone(archive.handle(get(id='expiring'))['record'])
            archive.handle(put(document(revision=2, text='Replacement guide about cooking.'), 1))
            self.assertEqual(archive.handle(dict(request, query='asyncio'))['records'], [])

    def test_quota_and_failed_write_are_atomic(self):
        with tempfile.TemporaryDirectory() as root, patch('storage.public_archive.MAX_ROWS', 1):
            archive = PublicArchive(Path(root) / 'db.sqlite')
            archive.handle(put(document()))
            with self.assertRaises(ValueError):
                archive.handle(put(document(id='another')))
            with patch('storage.public_archive.MAX_CONTENT', 1), self.assertRaises(ValueError):
                archive.handle(put(document(revision=2), 1))
            self.assertEqual(archive.handle(get())['record'], document())

    def test_bounded_cache_checksum_scope_revision_expiry_and_invalidation(self):
        with tempfile.TemporaryDirectory() as root:
            cache = PublicCache(root, budget=600, clock=lambda: 100)
            self.assertTrue(cache.put(document()))
            self.assertEqual(cache.get('operator', 'atlas', 'python-doc', 1)['freshness'], 'offline_unverified')
            self.assertIsNone(cache.get('other', 'atlas', 'python-doc', 1))
            self.assertIsNone(cache.get('operator', 'atlas', 'python-doc', 2))
            cache.put(document(id='second'))
            self.assertLessEqual(sum(p.stat().st_size for p in Path(root).glob('*')), 600)
            self.assertIsNone(cache.get('operator', 'atlas', 'python-doc', 1))
            path = next(Path(root).glob('*.json'))
            envelope = json.loads(path.read_text())
            envelope['record']['text'] = 'Changed cache body'
            path.write_text(json.dumps(envelope))
            self.assertIsNone(cache.get('operator', 'atlas', 'second', 1))
            cache.put(document(expires_at=99))
            self.assertIsNone(cache.get('operator', 'atlas', 'python-doc', 1))
            cache.put(document())
            cache.invalidate('operator', 'atlas', 'python-doc')
            self.assertIsNone(cache.get('operator', 'atlas', 'python-doc', 1))
            self.assertFalse(cache.put(document(text='x'*2000)))

    def test_fake_ssh_roundtrip_and_outage_never_claims_success_or_uses_stale_cache(self):
        with tempfile.TemporaryDirectory() as root:
            archive = PublicArchive(Path(root) / 'remote.sqlite')
            cache = PublicCache(Path(root) / 'cache')
            called = []
            def exchange(command, body, cancelled, **kwargs):
                called.append(json.loads(body))
                self.assertEqual(kwargs, {'timeout': 12, 'close_stdin': True})
                self.assertIn('StrictHostKeyChecking=yes', command)
                self.assertIn('ForwardAgent=no', command)
                self.assertNotIn(document()['text'], str(command))
                return SimpleNamespace(returncode=0, stdout=encoded(archive.handle(json.loads(body))).decode())
            gates = {key: True for key in ('enabled', 'free_allowance_verified', 'isolated_access_verified', 'recovery_verified')}
            gates['key_file'] = 'fake-archive.key'
            config = dict(host='192.0.2.1', key_file='fake.key', public_archive=gates)
            client = OraclePublicArchive(config, cache=cache, exchange=exchange)
            with patch.object(Path, 'is_file', return_value=True):
                client.put(document(), expected_revision=0, reviewed_public=True)
                self.assertEqual(client.get('operator', 'atlas', 'python-doc', 1)['record'], document())
                self.assertEqual(len(client.search('operator', 'atlas', 'asyncio')['records']), 1)
                def unavailable(*args, **kwargs):
                    raise TimeoutError('FAKE_SECRET_DO_NOT_ECHO')
                client.exchange = unavailable
                with self.assertRaises(ArchiveUnavailable) as failure:
                    client.get('operator', 'atlas', 'python-doc', 1)
                self.assertNotIn('FAKE_SECRET', str(failure.exception))
                self.assertIsNotNone(cache.get('operator', 'atlas', 'python-doc', 1))
                with self.assertRaises(ArchiveUnavailable):
                    client.delete('operator', 'atlas', 'python-doc', expected_revision=1)
                self.assertIsNone(cache.get('operator', 'atlas', 'python-doc', 1))
                client.exchange = exchange
                client.delete('operator', 'atlas', 'python-doc', expected_revision=1)
                self.assertIsNone(client.get('operator', 'atlas', 'python-doc', 1)['record'])
                before = len(called)
                with self.assertRaises(PermissionError):
                    client.put(document(), expected_revision=0)
                with self.assertRaises(ValueError):
                    client.request(dict(get(), extra='private text'))
                with self.assertRaises(ValueError):
                    client.put(document(sensitivity='private'), expected_revision=0, reviewed_public=True)
                config['public_archive']['enabled'] = False
                with self.assertRaises(ArchiveUnavailable):
                    client.search('operator', 'atlas', 'asyncio')
                self.assertEqual(len(called), before)

    def test_malformed_remote_result_cannot_cross_scope(self):
        gates = {key: True for key in ('enabled', 'free_allowance_verified', 'isolated_access_verified', 'recovery_verified')}
        gates['key_file'] = 'fake-archive.key'
        config = dict(host='192.0.2.1', key_file='fake.key', public_archive=gates)
        with patch.object(Path, 'is_file', return_value=True):
            for payload in ({'record': document(owner='other')}, {'record': document(sensitivity='private')},
                            {'error': 'FAKE_SECRET'}, {'arbitrary': True}):
                client = OraclePublicArchive(config, exchange=lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(payload)))
                with self.assertRaises((ValueError, ArchiveUnavailable)):
                    client.get('operator', 'atlas', 'python-doc', 1)

    def test_native_commands_require_exact_owner_approval_and_never_use_a_model(self):
        from cryptography.fernet import Fernet
        from security import vault
        from security.policy import Session
        from storage import store
        from brain.workflow import Brain
        from cloud.public_archive import acknowledged
        with tempfile.TemporaryDirectory() as temporary, patch.object(vault, '_F', Fernet(Fernet.generate_key())):
            root = Path(temporary)
            db = root / 'protected.enc'
            pid = store.create_person('Synthetic operator', 'admin', db_path=db)
            now = 2000000000
            session = Session('admin', 'Fixture', 'fake-session', pid, now+1000)
            server = PublicArchive(root / 'fake-remote.sqlite', clock=lambda: now)
            commands, packets = [], []
            class FakeClient(OraclePublicArchive):
                def request(self, packet, **kwargs):
                    packets.append(packet)
                    return server.handle(packet)
            def approve(action, text, current):
                commands.append((action, text))
                return True
            def no_model(*args, **kwargs):
                self.fail('Archive command called a model')
            client = FakeClient({})
            brain = Brain(session, approve=approve, client=no_model, local_client=no_model,
                          archive=client, db_path=db, clock=lambda: now)
            command = 'public archive atlas: save guide 0 permanent | Synthetic title | https://example.invalid | Synthetic asyncio guide.'
            self.assertEqual(brain.respond(command).route, 'public-archive')
            self.assertEqual(commands[-1], ('memory_write', command))
            self.assertEqual(brain.respond(command).route, 'public-archive')
            self.assertNotIn(pid, json.dumps(packets))
            self.assertEqual(brain.respond('public archive atlas: find asyncio').route, 'public-archive')
            self.assertIn('Synthetic asyncio', brain.respond('public archive atlas: read guide 1').text)
            self.assertNotIn('Synthetic asyncio', brain.respond('public archive beta: find asyncio').text)
            brain.respond('public archive atlas: delete guide 1')
            self.assertIn('missing', brain.respond('public archive atlas: read guide 1').text)
            before = len(packets)
            brain.private_mode = True
            self.assertEqual(brain.respond(command).route, 'blocked')
            brain.private_mode = False
            brain.approve = lambda *args: 1
            self.assertEqual(brain.respond(command).route, 'blocked')
            brain.bind_session(Session(id='guest'))
            self.assertEqual(brain.respond('public archive atlas: find asyncio').route, 'blocked')
            self.assertEqual(brain.respond('public archive ../bad: find asyncio').route, 'blocked')
            self.assertEqual(len(packets), before)
            for invalid in ({'revision': 1, 'acknowledged': 1}, {'revision': True, 'acknowledged': True}):
                with self.assertRaises(ArchiveUnavailable):
                    acknowledged(invalid, 1)


if __name__ == '__main__':
    unittest.main()
