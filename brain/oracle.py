"""Opt-in SSH inference bridge. Private memory authorization stays in Brain."""
import ipaddress
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'desktop' / 'oracle.local.json'


class OracleModel:
    description = 'Oracle SSH bridge (cloud inference; configured, not a live health check)'

    def __init__(self, config=None, runner=subprocess.run):
        self.config = config
        self.runner = runner

    def __call__(self, messages):
        return self.invoke(messages)

    def invoke(self, messages, *, task='general', sensitivity='private'):
        from brain.workflow import ModelUnavailable
        try:
            config = self.config if self.config is not None else json.loads(CONFIG.read_text())
            host = str(ipaddress.ip_address(config['host']))
            key = (ROOT / config['key_file']).resolve()
            key.relative_to(ROOT)
            if not key.is_file():
                raise ValueError('Missing key')
            body = json.dumps({'messages': messages, 'task': task, 'sensitivity': sensitivity}, ensure_ascii=True)
            if len(body.encode()) > 65536:
                raise ValueError('Request too large')
            command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                       '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
                       '-o', 'UserKnownHostsFile=' + str(ROOT / 'oracle_known_hosts.local'),
                       '-i', str(key), 'ubuntu@' + host,
                       '/usr/bin/python3 /home/ubuntu/lya/inference.py']
            run = self.runner(command, input=body, capture_output=True, text=True,
                              encoding='utf-8', timeout=30,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if run.returncode:
                raise ModelUnavailable('Oracle connection failed. Check SSH access; no provider fallback was attempted.')
            if len(run.stdout) > 65536:
                raise ValueError('Oversize response')
            response = json.loads(run.stdout)
            if response.get('error'):
                allowed = {'provider_not_configured', 'provider_http_401', 'provider_http_403',
                           'provider_http_429', 'provider_unavailable', 'no_eligible_route',
                           'daily_budget_exhausted', 'cooldown', 'provider_output_length'}
                reason = response['error'] if response['error'] in allowed else 'backend_error'
                raise ModelUnavailable('Oracle inference unavailable: ' + reason + '. Approved routes could not complete this request.')
            answer = response.get('text')
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('Invalid response')
            attempts = response.get('attempts', [])
            if attempts:
                # Backend config IDs are data; do not expose arbitrary response fields.
                import re
                rid = str(response.get('route', ''))
                if re.fullmatch(r'[a-z0-9_-]{1,40}', rid):
                    answer = answer[:7600] + f'\n\nModel route: {rid}; {min(len(attempts), 2)} provider attempt(s).'
            return answer[:8000]
        except ModelUnavailable:
            raise
        except Exception:
            raise ModelUnavailable('Oracle inference could not complete. Check configuration or connection; no fallback was attempted.') from None
