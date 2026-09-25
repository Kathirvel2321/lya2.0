import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import privacy


class ClassificationTests(unittest.TestCase):
    def test_public_text_stays_public(self):
        level, findings = privacy.classify('The backup finished and the report is ready.')
        self.assertEqual(level, 'public')
        self.assertEqual(findings, ())

    def test_credentials_are_private(self):
        cases = ('my password is hunter2',
                 'the api key is sk-abcdefghijklmnop1234',
                 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz123',
                 '-----BEGIN RSA PRIVATE KEY-----',
                 'Aadhaar 2345 6789 0123')
        for text in cases:
            self.assertEqual(privacy.classify(text)[0], 'private', text)

    def test_personal_identifiers(self):
        self.assertEqual(privacy.classify('mail me at ravi.k@example.com')[0], 'personal')
        self.assertEqual(privacy.classify('call +91 9876543210 now')[0], 'personal')
        self.assertEqual(privacy.classify(r'open C:\Users\ravi\Documents\keys.txt')[0], 'personal')

    def test_luhn_is_enforced_for_cards(self):
        self.assertEqual(privacy.classify('card 4111 1111 1111 1111')[0], 'private')
        # Same shape, failing the checksum: no longer classed as a card.
        self.assertNotIn('credit_card', [f.kind for f in privacy.classify('card 4111 1111 1111 1112')[1]])

    def test_ipv4_range_is_checked(self):
        self.assertIn('ipv4', [f.kind for f in privacy.classify('host 192.168.0.10')[1]])
        self.assertNotIn('ipv4', [f.kind for f in privacy.classify('host 999.1.1.1')[1]])

    def test_findings_never_contain_the_secret(self):
        secret = 'hunter2sosecret'
        level, findings = privacy.classify('my password: %s' % secret)
        self.assertEqual(level, 'private')
        for finding in findings:
            self.assertNotIn(secret, finding.preview)

    def test_redaction_masks_and_keeps_the_rest(self):
        text = 'Mail ravi.k@example.com about the backup, then call +91 9876543210.'
        redacted, findings = privacy.redact(text)
        self.assertIn('<email>', redacted)
        self.assertNotIn('ravi.k@example.com', redacted)
        self.assertIn('about the backup', redacted)
        self.assertGreaterEqual(len(findings), 2)

    def test_fingerprint_is_stable_short_and_not_reversible(self):
        first = privacy.fingerprint('a private phrase', 'salt')
        self.assertEqual(first, privacy.fingerprint('a private phrase', 'salt'))
        self.assertNotEqual(first, privacy.fingerprint('a private phrase', 'other'))
        self.assertEqual(len(first), 16)
        self.assertNotIn('private', first)

    def test_highest_sensitivity(self):
        self.assertEqual(privacy.highest_sensitivity(['public', 'private', 'personal']), 'private')
        self.assertEqual(privacy.highest_sensitivity([]), 'public')


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = privacy.Policy()

    def test_remote_is_disabled_by_default(self):
        decision = self.policy.decide('cloud_edge', 'public', allow_remote=True)
        self.assertFalse(decision.allowed)
        self.assertIn('disabled by policy', decision.reason)

    def test_local_engines_are_allowed(self):
        self.assertTrue(self.policy.decide('offline_piper').allowed)
        self.assertTrue(self.policy.decide('offline_sapi').allowed)

    def test_unknown_engine_is_denied(self):
        self.assertFalse(self.policy.decide('some_new_engine').allowed)

    def test_ladder_excludes_remote_while_disabled(self):
        ladder = self.policy.ladder('offline_piper', 'public')
        self.assertEqual(ladder, ['offline_piper', 'offline_sapi'])
        self.assertNotIn('cloud_edge', ladder)

    def test_ladder_for_private_text_is_local_only(self):
        self.assertEqual(self.policy.ladder('offline_piper', 'private'),
                         ['offline_piper', 'offline_sapi'])

    def _opt_in_policy(self, sensitivity_limit=('public',)):
        payload = json.loads(Path(self.policy.source).read_text(encoding='utf-8'))
        payload['remote'] = 'opt_in'
        payload['remote_allow_sensitivity'] = list(sensitivity_limit)
        folder = tempfile.mkdtemp(prefix='alya-policy-')
        path = Path(folder) / 'policy.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return privacy.Policy(path)

    def test_opt_in_requires_an_explicit_per_run_flag(self):
        policy = self._opt_in_policy()
        self.assertFalse(policy.decide('cloud_edge', 'public').allowed)
        self.assertTrue(policy.decide('cloud_edge', 'public', allow_remote=True).allowed)

    def test_opt_in_still_refuses_personal_text(self):
        policy = self._opt_in_policy()
        decision = policy.decide('cloud_edge', 'personal', allow_remote=True)
        self.assertFalse(decision.allowed)
        self.assertIn('never leaves the device', decision.reason)

    def test_opt_in_ladder_puts_remote_first(self):
        policy = self._opt_in_policy()
        self.assertEqual(policy.ladder('cloud_edge', 'public', allow_remote=True)[0], 'cloud_edge')


if __name__ == '__main__':
    unittest.main()
