"""Explicit, bounded provider failover. State contains counters only, never prompts."""
import json
import os
from pathlib import Path
import re
import sqlite3
import time

TASKS = {'general', 'coding', 'research', 'security', 'council'}
PROVIDERS = {'groq', 'nvidia', 'huggingface', 'openrouter', 'omniroute'}


def upstream(route):
    if route['provider'] in {'groq', 'nvidia'}:
        return route['provider']  # A label cannot make two direct routes independent.
    if route.get('upstream_pinned') is not True:
        return None
    if route['provider'] == 'openrouter':
        provider = route.get('upstream_provider', '')
        slug = re.sub(r'[^a-z0-9]+', '-', provider.casefold()).strip('-')
        expected = 'openrouter-' + slug
        if not slug or route.get('failure_domain') != expected or not route['model'].endswith(':free'):
            return None
    if route['provider'] == 'huggingface':
        parts = route['model'].rsplit(':', 1)
        if len(parts) != 2 or parts[1] in {'auto', 'fastest', 'cheapest', 'preferred'}:
            return None
        if parts[1] != route['failure_domain']:
            return None
    return route['failure_domain']


def validate_config(config):
    if config.get('version') != 2:
        raise ValueError('Unsupported router configuration')
    routes = config.get('routes', [])
    if not isinstance(routes, list) or len(routes) > 20:
        raise ValueError('Invalid routes')
    seen = set()
    for route in routes:
        rid = route.get('id', '')
        if not re.fullmatch(r'[a-z0-9_-]{1,40}', rid) or rid in seen:
            raise ValueError('Invalid route ID')
        seen.add(rid)
        if route.get('provider') not in PROVIDERS or not isinstance(route.get('model'), str):
            raise ValueError('Invalid provider/model')
        if not route['model'] or len(route['model']) > 160:
            raise ValueError('Invalid model')
        if not isinstance(route.get('tasks'), list) or not route['tasks'] or not set(route['tasks']) <= TASKS:
            raise ValueError('Invalid tasks')
        if type(route.get('enabled', False)) is not bool or type(route.get('allow_private', False)) is not bool:
            raise ValueError('Invalid policy flags')
        if route.get('provider') == 'openrouter' and not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', route.get('upstream_provider', '')):
            raise ValueError('OpenRouter requires one declared upstream provider')
        if not re.fullmatch(r'[a-z0-9_-]{1,40}', route.get('failure_domain', '')):
            raise ValueError('Declare upstream failure domain')
        if type(route.get('max_tokens', 1024)) is not int or not 128 <= route.get('max_tokens', 1024) <= 2048:
            raise ValueError('Invalid output budget')
    if type(config.get('daily_attempt_limit', 100)) is not int or not 1 <= config.get('daily_attempt_limit', 100) <= 1000:
        raise ValueError('Invalid daily limit')
    if type(config.get('daily_token_limit', 200000)) is not int or not 1 <= config.get('daily_token_limit', 200000) <= 2000000:
        raise ValueError('Invalid daily token allowance')


class State:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = self.connect()
        try:
            db.execute('CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, attempts INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS cooldown(domain TEXT PRIMARY KEY, until REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS allowance(day TEXT PRIMARY KEY, reserved INTEGER NOT NULL)')
            db.commit()
        finally:
            db.close()
        os.chmod(self.path, 0o600)

    def connect(self):
        return sqlite3.connect(self.path, timeout=1)

    def reserve(self, domain, cap, now, tokens=0, token_cap=200000):
        day = time.strftime('%Y-%m-%d', time.gmtime(now))
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT until FROM cooldown WHERE domain=?', (domain,)).fetchone()
            if row and row[0] > now:
                return 'cooldown'
            row = db.execute('SELECT attempts FROM usage WHERE day=?', (day,)).fetchone()
            if row and row[0] >= cap:
                return 'daily_budget_exhausted'
            row = db.execute('SELECT reserved FROM allowance WHERE day=?', (day,)).fetchone()
            if (row[0] if row else 0) + tokens > token_cap:
                return 'daily_token_budget_exhausted'
            db.execute('INSERT INTO allowance VALUES (?,?) ON CONFLICT(day) DO UPDATE SET reserved=reserved+excluded.reserved', (day, tokens))
            db.execute('INSERT INTO usage VALUES (?,1) ON CONFLICT(day) DO UPDATE SET attempts=attempts+1', (day,))
            db.execute('DELETE FROM usage WHERE day < ?', (day,))
            db.execute('DELETE FROM allowance WHERE day < ?', (day,))
            db.execute('DELETE FROM cooldown WHERE until <= ?', (now,))
            db.commit()
            return 'ok'
        finally:
            db.close()

    def fail(self, domain, until):
        db = self.connect()
        try:
            db.execute('INSERT INTO cooldown VALUES (?,?) ON CONFLICT(domain) DO UPDATE SET until=MAX(cooldown.until, excluded.until)', (domain, until))
            db.commit()
        finally:
            db.close()


def route_request(packet, config, call, state, clock=time.time, monotonic=time.monotonic, cancelled=lambda: False):
    validate_config(config)
    try:
        from .inference import validate
    except ImportError:  # Deployed as two flat files on Oracle.
        from inference import validate
    messages = validate(packet)
    # Conservative reservation, not a tokenizer measurement or a dollar cap.
    input_allowance = len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) + 256
    task = packet.get('task', 'general')
    sensitivity = packet.get('sensitivity', 'private')
    if task not in TASKS or sensitivity not in {'public', 'private'}:
        return {'error': 'invalid_routing_policy'}
    candidates = [r for r in config['routes'] if r.get('enabled') and task in r['tasks']
                  and (sensitivity == 'public' or r.get('allow_private') is True)]
    attempts, domains = [], set()
    deadline = monotonic() + 18
    last_error = 'no_eligible_route'
    for route in candidates:
        if cancelled():
            return {'error': 'cancelled', 'attempts': attempts}
        if monotonic() >= deadline:
            return {'error': 'deadline_exceeded', 'attempts': attempts}
        if len(attempts) >= 2:
            break
        domain = upstream(route)
        if domain is None or domain in domains:
            continue
        reservation = state.reserve(domain, config.get('daily_attempt_limit', 100), clock(),
                                    input_allowance + route.get('max_tokens', 1024), config.get('daily_token_limit', 200000))
        if reservation in {'daily_budget_exhausted', 'daily_token_budget_exhausted'}:
            return {'error': reservation, 'attempts': attempts}
        if reservation != 'ok':
            last_error = reservation
            continue
        domains.add(domain)
        remaining = deadline - monotonic()
        if remaining <= 0 or cancelled():
            return {'error': 'cancelled' if cancelled() else 'deadline_exceeded', 'attempts': attempts}
        try:
            result = call(route, min(8, remaining))
        except Exception:
            result = {'error': 'provider_unavailable'}
        if not isinstance(result, dict) or not result.get('error') and (not isinstance(result.get('text'), str) or not result['text'].strip()):
            result = {'error': 'invalid_provider_response'}
        error = result.get('error')
        attempts.append({'route': route['id'], 'status': error or 'ok'})
        if cancelled() or monotonic() >= deadline:
            return {'error': 'cancelled' if cancelled() else 'deadline_exceeded', 'attempts': attempts}
        if not error:
            return {**result, 'route': route['id'], 'attempts': attempts}
        last_error = error
        if error not in {'provider_unavailable', 'provider_http_408', 'provider_http_429',
                         'provider_http_500', 'provider_http_502', 'provider_http_503', 'provider_http_504', 'invalid_provider_response'}:
            # No retry for refusal, invalid credentials or invalid input.
            return {'error': error, 'attempts': attempts}
        delay = 60 if error == 'provider_http_429' else 30
        retry_after = result.get('retry_after_seconds')
        if type(retry_after) is int and 0 <= retry_after <= 86400:
            delay = max(delay, retry_after)
        state.fail(domain, clock() + delay)
    return {'error': last_error, 'attempts': attempts}
