"""Append-only audit log that never stores what she said.

Only a per-run salted hash, character count and engine metadata are written. The
salt is random per process, so fingerprints cannot be linked across runs. Raw
text is written only if a caller explicitly passes store_text=True.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

from . import privacy


class Auditor:
    def __init__(self, directory, enabled=True, store_text=False, salt=None, max_bytes=2_000_000):
        self.directory = Path(directory)
        self.enabled = bool(enabled)
        self.store_text = bool(store_text)
        self.salt = salt or secrets.token_hex(8)
        self.max_bytes = int(max_bytes)
        if self.enabled:
            self.directory.mkdir(parents=True, exist_ok=True)

    @property
    def path(self):
        return self.directory / 'voice-audit.jsonl'

    def record(self, kind, text=None, **fields):
        if not self.enabled:
            return None
        row = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'kind': str(kind)}
        row.update(fields)
        if text is not None:
            row['text'] = privacy.fingerprint(text, self.salt)
            row['chars'] = len(str(text))
            row['sensitivity'] = privacy.classify(text)[0]
            if self.store_text:
                row['raw'] = str(text)
        target = self.path
        try:
            if target.exists() and target.stat().st_size > self.max_bytes:
                os.replace(target, target.with_suffix('.jsonl.1'))
            with target.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')
        except OSError:
            # An audit failure must never break speech, but it is reported.
            row['audit_error'] = 'write failed'
        return row

    def tail(self, limit=20):
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding='utf-8').splitlines()[-int(limit):]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out
