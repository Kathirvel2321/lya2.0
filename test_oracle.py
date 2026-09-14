"""Offline inference bridge checks with fake keys and mocked transport only."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
from cloud.inference import infer, validate
from brain.oracle import OracleModel
from brain.workflow import Brain, ModelUnavailable


class OracleChecks(unittest.TestCase):
    messages = [{'role': 'user', 'content': 'Synthetic hello'}]
    config = {'provider': 'groq', 'api_key': 'FAKE_KEY', 'model': 'test-model'}

    def test_valid_provider_request_is_bounded(self):
        def opener(req, timeout):
            body = json.loads(req.data)
            self.assertEqual(body['max_completion_tokens'], 400)
            self.assertNotIn('tools', body)
            self.assertEqual(timeout, 18)
            self.assertEqual(req.full_url, 'https://api.groq.com/openai/v1/chat/completions')
            return io.BytesIO(b'{"choices":[{"message":{"content":"Synthetic reply"}}]}')
        self.assertEqual(infer({'messages': self.messages}, self.config, opener)['text'], 'Synthetic reply')

    def test_no_provider_and_invalid_messages_make_no_network_call(self):
        def denied(*a, **k):
            self.fail('network called')
        self.assertEqual(infer({'messages': self.messages}, {}, denied)['error'], 'provider_not_configured')
        for packet in ({'messages': []}, {'messages': [{'role': 'tool', 'content': 'x'}]},
                       {'messages': [{'role': 'user', 'content': 'x', 'tools': []}]},
                       {'messages': [{'role': 'user', 'content': 'x'*66000}]}):
            with self.assertRaises(ValueError):
                infer(packet, self.config, denied)

    def test_provider_errors_do_not_echo_secret_or_retry(self):
        calls = []
        def denied(*a, **k):
            calls.append(1)
            raise urllib.error.HTTPError('https://example.invalid', 429, 'FAKE_KEY', {}, None)
        result = infer({'messages': self.messages}, self.config, denied)
        self.assertEqual(result, {'error': 'provider_http_429'})
        self.assertEqual(len(calls), 1)

    def test_bridge_and_brain_use_mock_ssh(self):
        def runner(command, **kwargs):
            self.assertIn('StrictHostKeyChecking=yes', command)
            self.assertEqual(kwargs['timeout'], 30)
            self.assertNotIn('Synthetic hello', str(command))
            return SimpleNamespace(returncode=0, stdout='{"text":"Synthetic reply"}')
        model = OracleModel({'host': '192.0.2.1', 'key_file': 'fake.key'}, runner)
        with patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(Brain(client=model).respond('Synthetic hello').text, 'Synthetic reply')
        self.assertEqual(Brain(client=model).respond('show memories').route, 'blocked')

    def test_bridge_rejects_host_injection_and_redacts_failure(self):
        model = OracleModel({'host': 'host; echo bad', 'key_file': 'fake.key'}, lambda *a, **k: self.fail('ssh called'))
        with self.assertRaises(ModelUnavailable):
            model(self.messages)
        model = OracleModel({'host': '192.0.2.1', 'key_file': 'fake.key'},
                            lambda *a, **k: SimpleNamespace(returncode=0, stdout='{"error":"FAKE_SECRET"}'))
        with patch.object(Path, 'is_file', return_value=True):
            with self.assertRaises(ModelUnavailable) as caught:
                model(self.messages)
        self.assertNotIn('FAKE_SECRET', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
