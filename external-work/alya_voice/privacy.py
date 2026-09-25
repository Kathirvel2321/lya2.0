"""Sensitivity classification, redaction and the fail-closed routing policy.

Design rule: masking does NOT make remote speech safe, because masking changes
what she says. Anything above 'public' is therefore routed to a local engine or
refused - never sanitised and sent. Findings keep only a masked preview, so logs
and reports never carry the original secret.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

PUBLIC, PERSONAL, PRIVATE = 'public', 'personal', 'private'
_ORDER = {PUBLIC: 0, PERSONAL: 1, PRIVATE: 2}

_DETECTORS = (
    ('private_key', PRIVATE, re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('api_key', PRIVATE, re.compile(r'\b(?:sk-[A-Za-z0-9_\-]{12,}|ghp_[A-Za-z0-9]{20,}'
                                    r'|AIza[0-9A-Za-z_\-]{20,}|xox[bpoas]-[A-Za-z0-9\-]{10,}'
                                    r'|AKIA[0-9A-Z]{12,})\b')),
    ('bearer', PRIVATE, re.compile(r'(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{16,}')),
    ('password_phrase', PRIVATE, re.compile(r'(?i)\b(?:my\s+)?(?:password|passcode|otp|pin'
                                            r'|seed phrase|recovery code|api key|access token)\b')),
    ('credit_card', PRIVATE, re.compile(r'\b(?:\d[ -]?){13,19}\b')),
    ('id_number', PRIVATE, re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')),
    ('id_code', PRIVATE, re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b')),
    ('private_marker', PRIVATE, re.compile(r"(?i)\b(?:confidential|do not tell|don't tell"
                                           r'|keep (?:this|it) secret|private fact|biometric'
                                           r'|face data|voiceprint)\b')),
    ('url_credentials', PRIVATE, re.compile(r'\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@\S+', re.I)),
    ('email', PERSONAL, re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b')),
    ('phone', PERSONAL, re.compile(r'(?<![\d.])(?:\+\d{1,3}[ -]?)?\d(?:[ -]?\d){8,10}(?![\d.]\d)')),
    ('ipv4', PERSONAL, re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')),
    ('path', PERSONAL, re.compile(r'(?:[A-Za-z]:\\[^\r\n:*?"<>|]*?\\[^\r\n:*?"<>|]+'
                                  r'|/(?:home|Users|mnt|var|etc)/[^\s\'"]+)')),
)

_MASK = {
    'private_key': '<private-key>', 'api_key': '<api-key>', 'bearer': '<token>',
    'password_phrase': '<credential-phrase>', 'credit_card': '<card>',
    'id_number': '<id-number>', 'id_code': '<id-code>', 'private_marker': '<private>',
    'url_credentials': '<url-with-credentials>', 'email': '<email>', 'phone': '<number>',
    'ipv4': '<address>', 'path': '<path>',
}


@dataclass(frozen=True)
class Finding:
    kind: str
    sensitivity: str
    start: int
    end: int
    preview: str


@dataclass(frozen=True)
class Decision:
    engine: str
    allowed: bool
    reason: str
    sensitivity: str = PUBLIC
    findings: tuple = ()


def _luhn(digits):
    total, parity = 0, len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _accepted(kind, raw):
    digits = re.sub(r'\D', '', raw)
    if kind == 'credit_card':
        return 13 <= len(digits) <= 19 and _luhn(digits)
    if kind == 'id_number':
        return len(digits) == 12 and digits[0] in '23456789'
    if kind == 'ipv4':
        return all(0 <= int(part) <= 255 for part in raw.split('.'))
    if kind == 'phone':
        return len(digits) >= 10
    return True


def classify(text):
    """(sensitivity, findings). Findings carry only a masked preview."""
    text = str(text)
    level = PUBLIC
    findings = []
    for kind, sensitivity, pattern in _DETECTORS:
        for match in pattern.finditer(text):
            if not _accepted(kind, match.group(0)):
                continue
            if _ORDER[sensitivity] > _ORDER[level]:
                level = sensitivity
            findings.append(Finding(kind=kind, sensitivity=sensitivity, start=match.start(),
                                    end=match.end(), preview=_MASK.get(kind, '<hidden>')))
    findings.sort(key=lambda f: f.start)
    return level, tuple(findings)


def redact(text):
    """Return (redacted_text, findings). Safe for logs, reports and screenshots."""
    text = str(text)
    _, findings = classify(text)
    out, cursor = [], 0
    for finding in findings:
        if finding.start < cursor:
            continue
        out.append(text[cursor:finding.start])
        out.append(finding.preview)
        cursor = finding.end
    out.append(text[cursor:])
    return ''.join(out), findings


def fingerprint(text, salt=''):
    """Stable short hash: identifies a phrase in a log without storing it."""
    return hashlib.sha256((str(salt) + '\x1f' + str(text)).encode('utf-8')).hexdigest()[:16]


def highest_sensitivity(levels):
    level = PUBLIC
    for value in levels:
        if _ORDER.get(value, 0) > _ORDER[level]:
            level = value
    return level


class Policy:
    """Fail-closed engine routing. Default config keeps every remote path off."""

    def __init__(self, path=None):
        import json
        from pathlib import Path
        source = Path(path) if path else Path(__file__).resolve().parents[1] / 'config' / 'policy.json'
        data = json.loads(Path(source).read_text(encoding='utf-8'))
        self.source = str(source)
        self.remote = str(data.get('remote', 'disabled')).lower()
        if self.remote not in ('disabled', 'opt_in', 'enabled'):
            raise ValueError('unknown remote policy %r' % self.remote)
        self.remote_allow_sensitivity = tuple(data.get('remote_allow_sensitivity', [PUBLIC]))
        self.engines = dict(data.get('engines', {}))
        self.fallback_order = tuple(data.get('fallback_order', []))
        self.audit = dict(data.get('audit', {}))
        self.cache = dict(data.get('cache', {}))

    def decide(self, engine, sensitivity=PUBLIC, allow_remote=None):
        row = self.engines.get(engine)
        if row is None:
            return Decision(engine, False, 'unknown engine', sensitivity)
        if not row.get('allowed', False):
            return Decision(engine, False, 'engine is disabled in policy', sensitivity)
        if row.get('kind') == 'local':
            return Decision(engine, True, 'local engine', sensitivity)
        if self.remote == 'disabled':
            return Decision(engine, False, 'remote speech is disabled by policy', sensitivity)
        if sensitivity not in self.remote_allow_sensitivity:
            return Decision(engine, False,
                            'text sensitivity %r never leaves the device' % sensitivity, sensitivity)
        if self.remote == 'opt_in' and allow_remote is not True:
            return Decision(engine, False, 'remote needs an explicit per-run opt-in', sensitivity)
        return Decision(engine, True, 'remote allowed by policy', sensitivity)

    def ladder(self, preferred, sensitivity=PUBLIC, allow_remote=None):
        """Preferred engine first, then the configured local fallbacks."""
        order = [preferred] + [name for name in self.fallback_order if name != preferred]
        allowed = []
        for name in order:
            if name in allowed:
                continue
            if self.decide(name, sensitivity, allow_remote).allowed:
                allowed.append(name)
        return allowed
