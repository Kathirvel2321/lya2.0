"""Content-free descriptions of failures reported by trusted adapters."""
from dataclasses import dataclass
import errno
from pathlib import Path
import platform
import re


_CAUSES = {
    'provider_http_401': ('The provider rejected its API credential (HTTP 401).',
                          'Check the configured credential and its expiry with that provider. The response does not identify why it was rejected.'),
    'provider_http_403': ('The provider refused access (HTTP 403).',
                          'Check whether the configured account is allowed to use that model.'),
    'provider_http_429': ('The provider limited requests (HTTP 429).',
                          'Wait for the provider limit to reset or check the account quota.'),
    'provider_timeout': ('The provider took too long to reply.',
                         'Check provider availability and retry when it is responsive.'),
    'provider_http_408': ('The provider reported a request timeout (HTTP 408).',
                          'Check provider availability before retrying.'),
    'provider_http_504': ('The provider’s gateway timed out waiting for its upstream service (HTTP 504).',
                          'Check provider availability before retrying.'),
    'deadline_exceeded': ('The inference request reached LYA’s time limit.',
                          'Check the latest provider status before retrying.'),
    'provider_unavailable': ('The provider could not be reached or did not complete its request.',
                             'Check the connection and provider status.'),
    'provider_not_configured': ('An eligible provider has no usable configuration.',
                                'Check the connection settings without sharing credentials.'),
    'no_eligible_route': ('No configured provider met the request’s routing requirements.',
                          'Check which providers are enabled for this type of request.'),
    'daily_budget_exhausted': ('LYA reached its daily provider request budget.', 'Wait for the daily budget to reset.'),
    'daily_token_budget_exhausted': ('LYA reached its daily provider token budget.', 'Wait for the daily budget to reset.'),
    'cooldown': ('The available provider is temporarily on cooldown.', 'Wait briefly and retry.'),
    'invalid_provider_response': ('The provider returned an unusable response.', 'Check provider availability before retrying.'),
    'oracle_connection': ('LYA could not reach its Oracle inference process.',
                          'Check whether the Oracle instance is online and its configured SSH connection works.'),
    'oracle_timeout': ('LYA timed out waiting for the Oracle connection.',
                       'Check the Oracle host and network before retrying.'),
    'local_timeout': ('The local model did not answer before its time limit.',
                      'Check whether the local model is running and ready to answer.'),
    'local_connection': ('LYA could not connect to the local model.',
                         'Check that the local model service has started.'),
}


@dataclass(frozen=True)
class Diagnosis:
    message: str
    public_evidence: str = ''

    def research_request(self):
        if not self.public_evidence:
            return None
        return f'Research troubleshooting for {self.public_evidence.rstrip(".")}'


def safe_status(code):
    if isinstance(code, str) and (code in _CAUSES or re.fullmatch(r'provider_http_[45][0-9]{2}', code)):
        return code
    return ''


def provider_issue(code, attempts=None, *, recovered=False):
    code = safe_status(code)
    if code in _CAUSES:
        explanation, next_step = _CAUSES[code]
    elif code:
        explanation = f'The provider returned HTTP {code[-3:]}.'
        next_step = 'Check the provider’s documentation and recent status to determine the cause.'
    else:
        explanation = 'The inference service could not complete the request.'
        next_step = 'Check the configured service’s status before making any changes.'
    public_evidence = explanation if code else ''
    if recovered:
        return Diagnosis(explanation + ' An approved fallback answered the request.', public_evidence)
    activity = ('No provider fallback was attempted.' if attempts == 1 else
                'Two approved routes were tried.' if attempts == 2 else '')
    return Diagnosis(' '.join(part for part in (explanation, activity, next_step) if part), public_evidence)


def safe_attempts(attempts):
    if not isinstance(attempts, list) or len(attempts) not in (1, 2):
        return []
    if any(not isinstance(item, dict) or type(item.get('status')) is not str for item in attempts):
        return []
    return ['ok' if item['status']=='ok' else safe_status(item['status']) for item in attempts]


def source_location(exc):
    root = Path(__file__).resolve().parents[1]
    tb, last = exc.__traceback__, None
    while tb:
        path = Path(tb.tb_frame.f_code.co_filename)
        if path.is_absolute() and path.is_relative_to(root):
            relative = path.relative_to(root)
            if relative.parts[0] in ('brain', 'cloud', 'skills', 'security', 'storage'):
                last = f'{relative.as_posix()}:{tb.tb_lineno}'
        tb = tb.tb_next
    return last


def runtime_issue(exc):
    location = source_location(exc)
    kind = type(exc)
    exception_name = kind.__name__ if kind.__module__ == 'builtins' else ''
    os_code = errno.errorcode.get(exc.errno) if isinstance(exc, OSError) and type(exc.errno) is int else None
    facts = ' '.join(part for part in (exception_name, os_code) if part)
    message = 'LYA stopped while processing the request.'
    if facts:
        message += f' Python reported {facts}.'
    if location:
        message += f' The failure surfaced at {location}.'
    return Diagnosis(message + ' The underlying cause is still unconfirmed.',
                     f'Python on {platform.system()} reported {facts}' if facts else '')


_SITE_TASK = re.compile(
    r"^\s*(?:lya[, ]+)?(?:please\s+)?(?:open|go to|visit|use)\s+(?P<site>.+?)"
    r"\s+(?:and(?:\s+then)?|then|to)\s+(?P<task>.+)$", re.I)
_SITE = re.compile(r'(?:https?://[^\s<>]+|\b(?:[a-z0-9-]+\.)+[a-z]{2,63}\b)', re.I)
_BROWSER = re.compile(r'\b(?:website|site|browser|chrome|safari|edge|firefox|google)\b', re.I)


def website_task(text):
    """Build a public research description without copying private task details."""
    match = _SITE_TASK.fullmatch(text)
    if not match:
        return None
    first, task = match.group('site', 'task')
    candidate = _SITE.search(first) or (_SITE.search(task) if _BROWSER.search(first) else None)
    if not candidate:
        return ('', '') if _BROWSER.search(first) else None
    from urllib.parse import urlsplit
    from cloud.web_reader import public_url
    address = candidate.group()
    try:
        parsed = urlsplit(public_url(address if '://' in address else 'https://' + address))
        host = parsed.hostname or ''
    except ValueError:
        return ('', '')
    if host.endswith('.ts.net') or not re.fullmatch(r'(?:[a-z0-9-]{1,63}\.)+[a-z]{2,63}', host):
        return ('', '')
    categories = (
        (r'\b(?:submit|fill|send)\b', 'submit a form'),
        (r'\b(?:download|export)\b', 'download or export information'),
        (r'\b(?:sign\s*in|log\s*in)\b', 'sign in'),
        (r'\b(?:search|find|read|check|look up)\b', 'find and read information'),
        (r'\b(?:update|change|edit)\b', 'update information'),
    )
    operation = next((label for pattern, label in categories if re.search(pattern, task, re.I)),
                     'carry out a browser task')
    return host, operation
