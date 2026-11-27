"""Exercise vault writes with synthetic CLI responses and no real vault access."""
import base64
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from security import bitwarden_secrets as vault


class BitwardenSaveChecks(unittest.TestCase):
    title = 'LYA NVIDIA_API_KEY'
    item_id = 'ab9d1625-93f5-4795-9141-deba37954855'
    value = 'fake-nvidia-credential'

    def setUp(self):
        for context in (patch.object(vault, '_session', 'fake-vault-session'),
                        patch.object(vault, '_cache', {'NVIDIA_API_KEY': 'old-fake-key'}),
                        patch.object(vault, 'sync', return_value=True),
                        patch.object(vault, '_command', return_value=['fixture-bw'])):
            context.start()
            self.addCleanup(context.stop)

    def test_write_payload_uses_stdin_and_preserves_metadata_on_edit(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                old = dict(id=self.item_id, name=self.title, type=1, notes='keep these notes',
                           login={'username': 'LYA', 'password': 'old-fake-key'})

                def cli(args, **options):
                    self.assertNotIn(self.value, str(args) + str(options['env']))
                    if args[1] == 'list':
                        result = [old] if existing else []
                    elif args[1] == 'get':
                        result = {'username': 'LYA'} if args[3] == 'item.login' else {'type': 1}
                    else:
                        self.assertEqual(args[1], 'edit' if existing else 'create')
                        result = json.loads(base64.b64decode(options['input']))
                        self.assertEqual(result['login']['password'], self.value)
                        if existing:
                            self.assertEqual(args[3], self.item_id)
                            self.assertEqual(result['notes'], old['notes'])
                    return SimpleNamespace(stdout=json.dumps(result), returncode=0)

                with patch.object(vault.subprocess, 'run', side_effect=cli):
                    result = vault.save_nvidia_key(self.value, authorized=lambda: True)
                    self.assertEqual(result, 'NVIDIA API key saved in Bitwarden.')
                    self.assertEqual(vault.get_password('NVIDIA_API_KEY'), self.value)

    def test_cancellation_after_lookup_and_duplicate_titles_prevent_writes(self):
        old = dict(id=self.item_id, name=self.title, type=1, login={})
        for records, expected in (([old], 'cancelled'), ([old, old], 'same title')):
            with self.subTest(expected=expected), patch.object(vault, '_run', return_value=json.dumps(records)) as run:
                result = vault.save_nvidia_key(self.value, authorized=Mock(side_effect=[True, False]))
                self.assertIn(expected, result)
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0][0], 'list')
                self.assertEqual(vault.get_password('NVIDIA_API_KEY'), 'old-fake-key')
