"""Run on Oracle from /home/ubuntu/lya; synthetic providers, no credentials."""
import json
from pathlib import Path
import tempfile
from router import State, route_request, validate_config

template = json.loads(Path('provider.example.json').read_text())
validate_config(template)
assert all(not r['enabled'] for r in template['routes'])
with tempfile.TemporaryDirectory(prefix='lya-router-check-') as tmp:
    calls = []
    routes = [{**r, 'enabled': True, 'tasks': ['general']} for r in template['routes']]
    config = {'version': 2, 'daily_attempt_limit': 2, 'routes': routes}
    def fake_call(route, timeout):
        calls.append(route['id'])
        return {'error': 'provider_http_503'} if len(calls) == 1 else {'text': 'Synthetic backup response'}
    result = route_request({'task': 'general', 'sensitivity': 'public'}, config,
                           fake_call, State(Path(tmp) / 'state.sqlite'))
    assert result['text'] == 'Synthetic backup response' and len(calls) == 2
print('Oracle router smoke check passed: synthetic failover; template disabled; no provider call.')
