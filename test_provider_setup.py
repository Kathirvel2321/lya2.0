"""Credential parsing and evaluation boundary checks; fake keys, no network."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cloud.probe_models import load_values
from cloud.evaluate_models import evaluate


class ProviderSetupChecks(unittest.TestCase):
    def test_dotenv_quotes_comments_export_and_no_expansion(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {}, clear=True):
            path = Path(folder) / '.env'
            path.write_text('export GROQ_API_KEY="FAKE#key" # comment\nNVIDIA_API_KEY=FAKE_other # note\nLYA_GROQ_MODEL=${DO_NOT_EXPAND}\nUNRELATED_SECRET=DO_NOT_READ\n')
            result = load_values(path)
            self.assertEqual(result['GROQ_API_KEY'], 'FAKE#key')
            self.assertEqual(result['NVIDIA_API_KEY'], 'FAKE_other')
            self.assertEqual(result['LYA_GROQ_MODEL'], '${DO_NOT_EXPAND}')
            self.assertNotIn('UNRELATED_SECRET', result)
            path.write_text('GROQ_API_KEY="FAKE_UNCLOSED\n')
            with self.assertRaises(ValueError):
                load_values(path)

    def test_failed_evaluation_stops_without_leaking_configuration(self):
        calls = []
        def fake(packet, config, timeout):
            calls.append(packet)
            self.assertEqual(packet['sensitivity'], 'public')
            self.assertEqual(timeout, 8)
            return {'error': 'provider_http_429'}
        report = evaluate('groq', 'fixture', {'GROQ_API_KEY': 'FAKE_SECRET'}, call=fake)
        self.assertEqual(len(calls), 1)
        self.assertFalse(report['completed'])
        self.assertNotIn('FAKE_SECRET', json.dumps(report))
        self.assertIsNone(report['cases'][0]['pass'])

    def test_complete_evaluation_still_requires_review_and_never_runs_code(self):
        report = evaluate('groq', 'fixture', {'GROQ_API_KEY': 'FAKE_SECRET'},
                          call=lambda *a, **k: {'text': 'raise RuntimeError("DO NOT EXECUTE")'})
        self.assertTrue(report['completed'])
        self.assertEqual(len(report['cases']), 8)
        self.assertEqual(report['review_status'], 'human_review_required')
        self.assertTrue(all(r['pass'] is None for r in report['cases']))


if __name__ == '__main__':
    unittest.main()
