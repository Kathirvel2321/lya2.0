"""Read-only account catalog probe. Prints provider/model IDs, never credentials.

Reads only known provider entries from the project's .env or process environment.
Does not send prompts, enable routes, follow redirects or contact custom gateways.
"""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def load_values(path=None):
    """Read only provider settings; no expansion, evaluation or secret logging."""
    values = {}
    path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / '.env'
    names = {'GROQ_API_KEY', 'NVIDIA_API_KEY', 'NVAPI_KEY', 'HF_TOKEN', 'HUGGINGFACE_API_KEY',
             'LYA_GROQ_MODEL', 'LYA_NVIDIA_MODEL', 'OMNIROUTE_URL', 'OMNIROUTE_KEY'}
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line.startswith('export '):
                line = line[7:]
            key, sep, value = line.partition('=')
            if sep and key.strip() in names:
                value = value.strip()
                if value.startswith(('"', "'")):
                    end = value.find(value[0], 1)
                    if end < 0 or (value[end+1:].strip() and not value[end+1:].strip().startswith('#')):
                        raise ValueError('Malformed provider setting')
                    value = value[1:end]
                else:
                    value = re.split(r'\s+#', value, maxsplit=1)[0].strip()
                values[key.strip()] = value
    values.update({k: os.environ[k] for k in names if os.environ.get(k)})
    return values


def main():
    values = load_values()
    opener = urllib.request.build_opener(NoRedirect)
    for provider, keys, url in [
        ('groq', ['GROQ_API_KEY'], 'https://api.groq.com/openai/v1/models'),
        ('nvidia', ['NVIDIA_API_KEY', 'NVAPI_KEY'], 'https://integrate.api.nvidia.com/v1/models'),
        ('huggingface', ['HF_TOKEN', 'HUGGINGFACE_API_KEY'], 'https://router.huggingface.co/v1/models')]:
        token = next((values[k] for k in keys if values.get(k)), '')
        if not token or token.lower().startswith(('your_', 'replace_', 'changeme', '<')):
            print(json.dumps({'provider': provider, 'status': 'credential_not_configured'}))
            continue
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token, 'User-Agent': 'LYA/1.0'})
        try:
            with opener.open(req, timeout=12) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('oversize')
            models = [r['id'] for r in json.loads(raw)['data'] if isinstance(r.get('id'), str)]
            print(json.dumps({'provider': provider, 'status': 'catalog_accessible', 'models': models[:100]}))
        except urllib.error.HTTPError as exc:
            print(json.dumps({'provider': provider, 'status': 'http_' + str(exc.code)}))
        except Exception:
            print(json.dumps({'provider': provider, 'status': 'probe_failed'}))


if __name__ == '__main__':
    main()
