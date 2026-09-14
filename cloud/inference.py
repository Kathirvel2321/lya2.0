"""One inference per SSH invocation. No HTTP listener, tools or memory database."""
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_BYTES = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
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
                 'huggingface': 'https://router.huggingface.co/v1/chat/completions'}
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
    if provider == 'groq' and config['model'].startswith('openai/gpt-oss-'):
        payload.update(reasoning_effort='low', reasoning_format='hidden')
    else:
        payload['temperature'] = 0.2
    body = json.dumps(payload).encode()
    req = urllib.request.Request(endpoint, data=body,
        headers={'Authorization': 'Bearer ' + config['api_key'], 'Content-Type': 'application/json', 'User-Agent': 'LYA/1.0'})
    try:
        if opener is None:
            opener = urllib.request.build_opener(NoRedirect).open
        with opener(req, timeout=timeout) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return {'error': 'invalid_provider_response'}
        choice = json.loads(raw)['choices'][0]
        if choice.get('finish_reason') in {'content_filter', 'length', 'tool_calls'}:
            return {'error': 'provider_output_' + choice['finish_reason']}
        answer = choice['message']['content']
        if not isinstance(answer, str) or not answer.strip():
            return {'error': 'invalid_provider_response'}
        return {'text': answer[:8000], 'provider': provider, 'model': config['model']}
    except urllib.error.HTTPError as exc:
        return {'error': 'provider_http_' + str(exc.code)}
    except Exception:
        return {'error': 'provider_unavailable'}


def main():
    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
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
                from router import route_request, State
                result = route_request(packet, config,
                    lambda route, timeout: infer(packet, route, timeout=timeout),
                    State(config_path.with_name('router-state.sqlite')))
            else:
                result = infer(packet, config)
    except Exception:
        result = {'error': 'invalid_request_or_configuration'}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
