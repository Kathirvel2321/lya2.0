"""Opt-in SSH inference bridge. Private memory authorization stays in Brain."""
import ipaddress
import json
from pathlib import Path
import subprocess

from brain.diagnostics import provider_issue, safe_attempts

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'desktop' / 'oracle.local.json'


class OracleModel:
    description = 'Oracle SSH bridge (cloud inference; configured, not a live health check)'

    def __init__(self, config=None, runner=subprocess.run):
        self.config = config
        self.runner = runner
        self.last_route = None
        self.last_diagnostic = None

    def invoke_cancellable(self, messages, *, cancelled=None, **policy):
        return self.invoke(messages, cancelled=cancelled, **policy)

    def __call__(self, messages):
        return self.invoke(messages)

    def invoke(self, messages, *, task='general', sensitivity='private', cancelled=None):
        from brain.workflow import ModelUnavailable
        try:
            self.last_route = None
            self.last_diagnostic = None
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError()
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
            if self.runner is subprocess.run:
                from cloud.ssh_session import exchange
                session = config.get('session_protocol') is True
                if session:
                    command[-1] += ' --session'
                run = exchange(command, body, cancelled, close_stdin=not session)
            else:
                run = self.runner(command, input=body, capture_output=True, text=True,
                                  encoding='utf-8', timeout=30,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError()
            if run.returncode:
                self.last_diagnostic = provider_issue('oracle_connection')
                raise ModelUnavailable(self.last_diagnostic.message)
            if len(run.stdout) > 65536:
                raise ValueError('Oversize response')
            response = json.loads(run.stdout)
            statuses = safe_attempts(response.get('attempts'))
            if response.get('error'):
                reason = response['error']
                if reason == 'cancelled':
                    raise InterruptedError()
                self.last_diagnostic = provider_issue(reason if isinstance(reason, str) else '', len(statuses))
                raise ModelUnavailable(self.last_diagnostic.message)
            answer = response.get('text')
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('Invalid response')
            if statuses:
                # Backend config IDs are data; do not expose arbitrary response fields.
                import re
                rid = str(response.get('route', ''))
                if re.fullmatch(r'[a-z0-9_-]{1,40}', rid):
                    self.last_route = {'route': rid, 'attempts': len(statuses)}
                if len(statuses) == 2 and statuses[1] == 'ok' and statuses[0] != 'ok':
                    self.last_diagnostic = provider_issue(statuses[0], recovered=True)
            return answer[:8000]
        except (ModelUnavailable, InterruptedError):
            raise
        except (TimeoutError, subprocess.TimeoutExpired):
            self.last_diagnostic = provider_issue('oracle_timeout')
            raise ModelUnavailable(self.last_diagnostic.message) from None
        except Exception:
            raise ModelUnavailable('Oracle inference could not complete. Check configuration or connection; no fallback was attempted.') from None
