"""Synthetic failover tests: fake providers, temporary counters, no network."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from cloud.router import State, route_request, validate_config
from cloud.inference import infer


class RouterChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.sqlite'
        self.state = State(self.path)
        self.config = {'version': 2, 'daily_attempt_limit': 10, 'routes': [
            {'id': name, 'provider': provider, 'model': 'fixture', 'tasks': ['general'],
             'enabled': True, 'failure_domain': name, 'allow_private': False}
            for name, provider in [('primary', 'groq'), ('backup', 'nvidia'), ('third', 'groq')]]}
        self.packet = {'messages': [{'role': 'user', 'content': 'SYNTHETIC'}], 'sensitivity': 'public'}
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, route, timeout):
        self.assertLessEqual(timeout, 8)
        self.calls.append(route['id'])
        return {'error': 'provider_http_429'} if route['id'] == 'primary' else {'text': 'Fixture answer'}

    def run_route(self, **kw):
        return route_request(kw.get('packet', self.packet), self.config, kw.get('call', self.call),
                             kw.get('state', self.state), clock=lambda: 2000000000)

    def test_fallback_and_cooldown_survive_new_process_state(self):
        result = self.run_route()
        self.assertEqual(result['route'], 'backup')
        self.assertEqual(self.calls, ['primary', 'backup'])
        self.calls.clear()
        self.run_route(state=State(self.path))
        self.assertEqual(self.calls, ['backup'])

    def test_private_context_never_reaches_unapproved_backup(self):
        self.config['routes'][0]['allow_private'] = True
        result = self.run_route(packet={**self.packet, 'sensitivity': 'private'})
        self.assertEqual(self.calls, ['primary'])
        self.assertIn('error', result)
        self.calls.clear()
        self.run_route(packet={'messages': self.packet['messages']})
        self.assertFalse(self.calls)  # conservative default private, primary cooled down

    def test_shared_upstream_is_not_independent_backup(self):
        self.config['routes'][1].update(provider='huggingface', model='fixture:groq', failure_domain='groq', upstream_pinned=True)
        self.config['routes'][2].update(provider='nvidia', failure_domain='nvidia')
        self.run_route()
        self.assertEqual(self.calls, ['primary', 'third'])

    def test_daily_budget_counts_failures_and_persists(self):
        self.config['daily_attempt_limit'] = 1
        result = self.run_route()
        self.assertEqual(result['error'], 'daily_budget_exhausted')
        self.calls.clear()
        self.assertEqual(self.run_route(state=State(self.path))['error'], 'daily_budget_exhausted')
        self.assertFalse(self.calls)

    def test_two_attempt_limit_on_total_outage(self):
        def outage(route, timeout):
            self.calls.append(route['id'])
            return {'error': 'provider_http_503'}
        self.assertEqual(len(self.run_route(call=outage)['attempts']), 2)
        self.assertEqual(self.calls, ['primary', 'backup'])

    def test_concurrent_reservations_cannot_exceed_budget(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: self.state.reserve(str(i), 1, 2000000000), range(8)))
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(results.count('daily_budget_exhausted'), 7)

    def test_deadline_stops_second_attempt(self):
        now = [0]
        def late(route, timeout):
            now[0] = 20
            return self.call(route, timeout)
        result = route_request(self.packet, self.config, late, self.state,
                               clock=lambda: 2000000000, monotonic=lambda: now[0])
        self.assertEqual(len(result['attempts']), 1)
        self.assertEqual(result['error'], 'deadline_exceeded')

    def test_no_fallback_for_auth_refusal_or_invalid_input(self):
        for error in ('provider_http_401', 'provider_http_403', 'provider_http_400',
                      'provider_output_content_filter'):
            result = self.run_route(call=lambda *a: {'error': error})
            self.assertEqual(len(result['attempts']), 1)
            self.assertEqual(result['error'], error)

    def test_task_and_gateway_pinning_are_required(self):
        self.assertEqual(self.run_route(packet={**self.packet, 'task': 'coding'})['error'], 'no_eligible_route')
        self.config['routes'] = [dict(self.config['routes'][0], provider='huggingface', model='fixture:fastest', upstream_pinned=True)]
        self.assertEqual(self.run_route()['error'], 'no_eligible_route')
        self.assertFalse(self.calls)

    def test_invalid_config_cannot_make_request(self):
        self.config['routes'][0]['id'] = 'bad\nlabel'
        with self.assertRaises(ValueError):
            self.run_route()
        self.assertFalse(self.calls)

    def test_reasoning_and_nvidia_request_parameters(self):
        bodies = []
        def opener(req, **kw):
            bodies.append((req.full_url, json.loads(req.data)))
            return io.BytesIO(b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}')
        cfg = {'provider': 'groq', 'model': 'openai/gpt-oss-120b', 'api_key': 'FAKE', 'max_tokens': 1024}
        infer(self.packet, cfg, opener)
        self.assertEqual(bodies[-1][1]['reasoning_format'], 'hidden')
        infer(self.packet, dict(cfg, provider='nvidia', model='fixture'), opener)
        self.assertIn('max_tokens', bodies[-1][1])
        self.assertNotIn('reasoning_format', bodies[-1][1])

    def test_openrouter_free_route_pins_and_verifies_upstream(self):
        route = {'id': 'or-backup', 'provider': 'openrouter',
                 'model': 'nvidia/nemotron-3-ultra-550b-a55b:free', 'tasks': ['general'],
                 'enabled': True, 'failure_domain': 'openrouter-fixture-host',
                 'upstream_pinned': True, 'upstream_provider': 'fixture-host',
                 'allow_private': False}
        validate_config({'version': 2, 'routes': [route]})
        bodies = []
        def opener(req, **kw):
            bodies.append(json.loads(req.data))
            self.assertEqual(req.headers['X-openrouter-metadata'], 'enabled')
            return io.BytesIO(b'{"openrouter_metadata":{"endpoints":{"available":[{"provider":"Fixture Host","selected":true}]}},"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}')
        result = infer(self.packet, {**route, 'api_key': 'FAKE'}, opener)
        self.assertEqual(result['text'], 'ok')
        self.assertEqual(result['upstream_provider'], 'fixture-host')
        self.assertEqual(bodies[0]['provider'], {'order': ['fixture-host'], 'allow_fallbacks': False})
        wrong = lambda *a, **k: io.BytesIO(b'{"provider":"Other","choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}')
        self.assertEqual(infer(self.packet, {**route, 'api_key': 'FAKE'}, wrong)['error'], 'invalid_provider_response')
        self.assertEqual(infer(self.packet, {**route, 'model': 'paid/model', 'api_key': 'FAKE'}, opener)['error'], 'invalid_endpoint')

    def test_truncation_is_not_reported_as_complete_answer(self):
        def opener(*a, **k):
            return io.BytesIO(b'{"choices":[{"message":{"content":"partial"},"finish_reason":"length"}]}')
        result = infer(self.packet, {'provider': 'groq', 'model': 'fixture', 'api_key': 'FAKE'}, opener)
        self.assertEqual(result['error'], 'provider_output_length')

    def test_plain_http_gateway_is_only_allowed_on_loopback(self):
        cfg = {'provider': 'omniroute', 'model': 'fixture', 'api_key': 'FAKE', 'endpoint': 'http://example.invalid/v1/chat/completions'}
        self.assertEqual(infer(self.packet, cfg, lambda *a: self.fail('network'))['error'], 'invalid_endpoint')


if __name__ == '__main__':
    unittest.main()
