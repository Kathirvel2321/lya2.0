"""One inference per SSH invocation. No HTTP listener, tools or memory database."""
import json
import os
from pathlib import Path
import re
import sys
import time
import threading
from email.utils import parsedate_to_datetime
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_BYTES = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _provider_slug(value):
    if not isinstance(value, str):
        return None
    slug = re.sub(r'[^a-z0-9]+', '-', value.casefold()).strip('-')
    return slug or None


def _provider_identity(value):
    slug = _provider_slug(value)
    return slug.replace('-', '') if slug else None


def _openrouter_provider(decoded):
    """Read opt-in routing metadata; never infer an upstream from the model name."""
    direct = _provider_slug(decoded.get('provider'))
    if direct:
        return direct
    metadata = decoded.get('openrouter_metadata')
    if not isinstance(metadata, dict):
        return None
    for key in ('provider', 'provider_name', 'provider_slug'):
        found = _provider_slug(metadata.get(key))
        if found:
            return found
    endpoints = metadata.get('endpoints')
    available = endpoints.get('available') if isinstance(endpoints, dict) else None
    if isinstance(available, list):
        selected = [_provider_slug(item.get('provider')) for item in available
                    if isinstance(item, dict) and item.get('selected') is True]
        selected = [item for item in selected if item]
        if len(selected) == 1:
            return selected[0]
    return None


def validate(packet):
    messages = packet.get('messages') if isinstance(packet, dict) else None
    if not isinstance(messages, list) or not 1 <= len(messages) <= 12:
        raise ValueError('Invalid messages')
    for message in messages:
        if not isinstance(message, dict) or set(message) != {'role', 'content'}:
            raise ValueError('Invalid message fields')
        if message['role'] not in {'system', 'user', 'assistant'} or not isinstance(message['content'], str):
            raise ValueError('Invalid message')
    if len(json.dumps(messages).encode()) > MAX_BYTES:
        raise ValueError('Request too large')
    return messages


def infer(packet, config, opener=None, timeout=18):
    messages = validate(packet)
    endpoints = {'groq': 'https://api.groq.com/openai/v1/chat/completions',
                 'nvidia': 'https://integrate.api.nvidia.com/v1/chat/completions',
                 'huggingface': 'https://router.huggingface.co/v1/chat/completions',
                 'openrouter': 'https://openrouter.ai/api/v1/chat/completions'}
    provider = config.get('provider')
    endpoint = endpoints.get(provider)
    if provider == 'omniroute':
        endpoint = config.get('endpoint', '')
        url = urlsplit(endpoint)
        if url.username or url.password or url.query or url.fragment or not url.hostname:
            return {'error': 'invalid_endpoint'}
        if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in {'127.0.0.1', '::1'}):
            return {'error': 'invalid_endpoint'}
        if not url.path.endswith('/chat/completions'):
            return {'error': 'invalid_endpoint'}
    if not endpoint or not config.get('api_key') or not config.get('model'):
        return {'error': 'provider_not_configured'}
    budget = config.get('max_tokens', 400)
    if type(budget) is not int or not 128 <= budget <= 2048:
        return {'error': 'invalid_output_budget'}
    payload = {'model': config['model'], 'messages': messages, 'stream': False,
               'max_completion_tokens' if provider == 'groq' else 'max_tokens': budget}
    if provider == 'openrouter':
        upstream_provider = config.get('upstream_provider')
        if not config['model'].endswith(':free') or not isinstance(upstream_provider, str) or not upstream_provider:
            return {'error': 'invalid_endpoint'}
        payload['provider'] = {'order': [upstream_provider], 'allow_fallbacks': False}
    if provider == 'groq' and config['model'].startswith('openai/gpt-oss-'):
        payload.update(reasoning_effort='low', reasoning_format='hidden')
    else:
        payload['temperature'] = 0.2
    if provider == 'nvidia' and config['model'].startswith('nvidia/nemotron-3.5-lightning-'):
        payload['chat_template_kwargs'] = {'enable_thinking': False}
    body = json.dumps(payload).encode()
    headers = {'Authorization': 'Bearer ' + config['api_key'],
               'Content-Type': 'application/json', 'User-Agent': 'LYA/1.0'}
    if provider == 'openrouter':
        headers['X-OpenRouter-Metadata'] = 'enabled'
    req = urllib.request.Request(endpoint, data=body, headers=headers)
    try:
        if opener is None:
            opener = urllib.request.build_opener(NoRedirect).open
        with opener(req, timeout=timeout) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return {'error': 'invalid_provider_response'}
        decoded = json.loads(raw)
        actual_upstream = None
        if provider == 'openrouter':
            actual_upstream = _openrouter_provider(decoded)
            if _provider_identity(actual_upstream) != _provider_identity(config['upstream_provider']):
                return {'error': 'invalid_provider_response'}
        choice = decoded['choices'][0]
        if choice.get('finish_reason') in {'content_filter', 'length', 'tool_calls'}:
            return {'error': 'provider_output_' + choice['finish_reason']}
        answer = choice['message']['content']
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 8000:
            return {'error': 'invalid_provider_response'}
        result = {'text': answer[:8000], 'provider': provider, 'model': config['model']}
        if actual_upstream:
            result['upstream_provider'] = config['upstream_provider']
        return result
    except urllib.error.HTTPError as exc:
        result = {'error': 'provider_http_' + str(exc.code)}
        retry = exc.headers.get('Retry-After') if exc.headers else None
        if retry:
            try:
                seconds = int(retry) if retry.isdigit() else int(parsedate_to_datetime(retry).timestamp() - time.time())
                if 0 <= seconds <= 86400:
                    result['retry_after_seconds'] = seconds
            except (TypeError, ValueError, OverflowError):
                pass
        return result
    except (ValueError, KeyError, IndexError, TypeError):
        return {'error': 'invalid_provider_response'}
    except Exception:
        return {'error': 'provider_unavailable'}


def bounded_infer(packet, route, timeout):
    """Linux SSH entry point: wall-clock bound covers DNS, headers and body reads."""
    import signal
    def expired(*_):
        raise TimeoutError('Provider deadline')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return infer(packet, route, timeout=timeout)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    os.umask(0o077)
    try:
        session = '--session' in sys.argv
        raw = sys.stdin.buffer.readline(MAX_BYTES + 1) if session else sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Request too large')
        packet = json.loads(raw)
        config_path = Path(__file__).with_name('provider.json')
        if not config_path.exists():
            result = {'error': 'provider_not_configured'}
        elif config_path.stat().st_mode & 0o077:
            result = {'error': 'unsafe_provider_file_permissions'}
        else:
            config = json.loads(config_path.read_text())
            if config.get('version') == 2:
                validate(packet)
                try:
                    from .router import route_request, State
                except ImportError:
                    from router import route_request, State
                cancelled = threading.Event()
                if session:
                    def watch_cancel():
                        # Raw descriptor avoids a daemon holding Python's buffered
                        # stdin lock during interpreter shutdown after success.
                        os.read(sys.stdin.fileno(), 1)  # CANCEL byte or EOF.
                        cancelled.set()
                    threading.Thread(target=watch_cancel, daemon=True).start()
                result = route_request(packet, config,
                    lambda route, timeout: bounded_infer(packet, route, timeout),
                    State(config_path.with_name('router-state.sqlite')), cancelled=cancelled.is_set)
            else:
                result = infer(packet, config)
    except Exception:
        result = {'error': 'invalid_request_or_configuration'}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
