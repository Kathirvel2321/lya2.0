"""Routine review fixtures: disposable metadata, real offscreen Qt, no accounts."""
import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication
from cloud.job_policy import from_dict
from cloud.routine_drafts import DraftStore, MAX_DRAFTS, Settings, from_settings, proposal
from desktop.news import quiet
from desktop.routines import RoutineDialog


class ProposalChecks(unittest.TestCase):
    def test_public_review_compiles_contract_but_has_no_activation_state(self):
        result = proposal(Settings())
        self.assertEqual(result['envelope']['state'], 'draft_not_authorized_or_scheduled')
        job = from_dict(result['envelope']['contract'])
        self.assertEqual(job.start, '13:00'); self.assertEqual(job.notify, '13:05')
        self.assertEqual(job.limits.sends, 0); self.assertEqual(job.owner, 'owner_not_connected')
        self.assertTrue(result['missing']); self.assertIn('not the entire internet', result['text'])

    def test_every_setting_changes_the_review_fingerprint(self):
        base = Settings()
        for field, value in [('provider', 'youtube_comments'), ('start', '14:00'),
                ('notify', '15:00'), ('zone', 'Etc/UTC'), ('placement', 'desktop'),
                ('lookback_hours', 24), ('catchup_minutes', 0), ('retention_hours', 1),
                ('notification_filter', 'always')]:
            with self.subTest(field=field):
                self.assertNotEqual(proposal(base)['fingerprint'], proposal(replace(base, **{field: value}))['fingerprint'])

    def test_private_server_draft_keeps_missing_consent_unresolved(self):
        result = proposal(Settings(provider='whatsapp_unspecified', start='18:00', notify='19:00', lookback_hours=24))
        self.assertIn('Personal WhatsApp or WhatsApp Business account choice', result['missing'])
        self.assertIn('Messages arriving after that snapshot are excluded', result['text'])
        self.assertFalse(result['envelope']['contract']['private_remote'])
        with self.assertRaises(ValueError): from_dict(result['envelope']['contract'])
        self.assertIn('zero outgoing replies', result['text'])

    def test_personal_business_and_youtube_are_requests_never_connection_claims(self):
        for provider in ('whatsapp_personal', 'whatsapp_business', 'youtube_comments'):
            with self.subTest(provider=provider):
                result = proposal(Settings(provider=provider, placement='desktop'))
                self.assertIn('Supported account connection, verified scopes and input adapter', result['missing'])
                self.assertEqual(result['envelope']['contract']['account'], 'account_not_connected')
                self.assertEqual(result['envelope']['contract']['send_mode'], 'draft_only')
                if provider == 'whatsapp_personal': self.assertIn('personal-inbox integration', result['text'])

    def test_next_day_notification_and_desktop_availability_are_explicit(self):
        text = proposal(Settings(start='23:00', notify='01:00', placement='desktop'))['text']
        self.assertIn('following day', text); self.assertIn('laptop awake', text)
        self.assertIn('not a guaranteed completion or delivery time', text)

    def test_ambiguous_times_unknown_fields_and_unbounded_choices_are_rejected(self):
        for changes in ({'start':'6pm'}, {'zone':'not/a/zone'}, {'lookback_hours':True},
                {'retention_hours':25}, {'catchup_minutes':121}, {'provider':'all_internet'},
                {'placement':'anywhere'}, {'notification_filter':'guess'}, {'notify':'24:00'},
                {'enabled':True}, {'account':'secret'}, {'message':'private-body'}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, KeyError)):
                from_settings({**json.loads(Settings().canonical()), **changes})


class StorageChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'drafts.sqlite'; self.store = DraftStore(self.path)

    def test_roundtrip_duplicate_and_delete_only_draft_metadata(self):
        key = self.store.save(Settings())
        self.assertEqual(self.store.save(Settings()), key)
        self.assertEqual(DraftStore(self.path).list(), [(key, Settings())])
        with sqlite3.connect(self.path) as db:
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        self.assertEqual(tables, [('drafts',)])
        self.store.delete(key); self.assertEqual(self.store.list(), [])

    def test_capacity_failure_keeps_existing_drafts_and_duplicate_is_still_allowed(self):
        for minute in range(MAX_DRAFTS): self.store.save(Settings(notify=f'14:{minute:02d}'))
        with self.assertRaises(ValueError): self.store.save(Settings(notify='15:00'))
        self.store.save(Settings(notify='14:00'))
        self.assertEqual(len(self.store.list()), MAX_DRAFTS)

    def test_unrelated_schema_and_tampered_settings_fail_closed(self):
        with sqlite3.connect(self.path) as db: db.execute('CREATE TABLE valuable(data)')
        with self.assertRaises(ValueError): self.store.list()
        self.path.unlink()
        self.store.save(Settings())
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE drafts SET settings=?', (Settings(start='16:00').canonical(),))
        with self.assertRaises(ValueError): self.store.list()

    def test_links_and_invalid_delete_references_are_refused(self):
        target = Path(self.temp.name) / 'actual.sqlite'; target.touch()
        self.path.symlink_to(target)
        with self.assertRaises(ValueError): self.store.save(Settings())
        self.assertEqual(target.read_bytes(), b'')
        with self.assertRaises(ValueError): self.store.delete('arbitrary')


class DialogChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = DraftStore(Path(self.temp.name) / 'drafts.sqlite')
        self.dialog = RoutineDialog(store=self.store); self.addCleanup(self.dialog.close)

    def test_private_template_real_widgets_show_six_and_seven_without_enabling(self):
        self.dialog.provider.setCurrentIndex(self.dialog.provider.findData('whatsapp_unspecified'))
        self.assertEqual(self.dialog.start.time(), QTime(18, 0))
        self.assertEqual(self.dialog.notify.time(), QTime(19, 0))
        self.assertIn('NOT ENABLED', self.dialog.review.toPlainText())
        self.dialog.save_button.click()
        self.assertIn('NOT enabled or scheduled', self.dialog.status.text())
        self.assertEqual(len(self.store.list()), 1)
        self.assertFalse(self.dialog.review.openExternalLinks())

    def test_saved_draft_reopens_and_edits_have_a_new_fingerprint(self):
        self.dialog.start.setTime(QTime(15, 45)); self.dialog.save()
        previous = self.store.list()[0][0]
        other = RoutineDialog(store=self.store); self.addCleanup(other.close)
        other.saved.setCurrentIndex(1); other.load_selected()
        self.assertEqual(other.start.time(), QTime(15, 45))
        self.assertIn('Saved draft', other.status.text())
        other.start.setTime(QTime(16, 0))
        self.assertIn('Unsaved', other.status.text())
        self.assertNotIn(previous, other.review.toPlainText())
        other.save(); self.assertEqual(len(self.store.list()), 2)
        other.remove(); self.assertEqual(len(self.store.list()), 1)

    def test_storage_failure_is_visible_and_does_not_claim_success(self):
        broken = Mock(); broken.list.side_effect = OSError('synthetic private exception body')
        broken.save.side_effect = OSError('synthetic private exception body')
        other = RoutineDialog(store=broken); self.addCleanup(other.close)
        self.assertIn('could not be read', other.status.text())
        other.save_button.click()
        self.assertIn('could not be saved', other.status.text())
        self.assertNotIn('private exception body', other.status.text())

    def test_visible_draft_review_prevents_automatic_news_presentation(self):
        self.dialog.show(); self.app.processEvents()
        owner = SimpleNamespace(brain_busy=False, brain=SimpleNamespace(private_mode=False),
                                routine_dialog=self.dialog)
        self.assertFalse(quiet(owner))
        self.dialog.hide(); self.assertTrue(quiet(owner))

    def test_desktop_manual_entry_points_and_dialog_reuse_without_full_assistant(self):
        # Extract only the small manual launcher; do not import/start voice or the desktop.
        source = Path(__file__).with_name('desktop') / 'app.py'
        tree = ast.parse(source.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and
                   any(isinstance(x, ast.FunctionDef) and x.name == 'show_routine_drafts' for x in node.body))
        method = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == 'show_routine_drafts')
        namespace = {}; exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
        from unittest.mock import patch
        with patch('desktop.routines.RoutineDialog') as factory:
            owner = SimpleNamespace()
            namespace['show_routine_drafts'](owner); namespace['show_routine_drafts'](owner)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(owner.routine_dialog.show.call_count, 2)
        self.assertIn('menu.addAction("Routine drafts", self.show_routine_drafts)', source.read_text())


if __name__ == '__main__': unittest.main()
