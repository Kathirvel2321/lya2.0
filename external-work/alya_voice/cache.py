"""Optional hash-keyed render cache. Disabled by default.

Keys are hashes of the plan and voice, never the source text, and stored files
contain audio only. Enable it in config/policy.json only if the owner accepts
speech audio being written to disk.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np


class AudioCache:
    def __init__(self, directory, enabled=False, max_bytes=32 * 1024 * 1024):
        self.directory = Path(directory)
        self.enabled = bool(enabled)
        self.max_bytes = int(max_bytes)
        if self.enabled:
            self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(*parts):
        payload = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]

    def _path(self, key):
        return self.directory / ('%s.npz' % key)

    def get(self, key):
        if not self.enabled:
            return None
        target = self._path(key)
        if not target.exists():
            return None
        try:
            with np.load(target) as data:
                return data['samples'].astype(np.float32), int(data['sr'][0])
        except (OSError, ValueError, KeyError):
            try:
                target.unlink()
            except OSError:
                pass
            return None

    def put(self, key, samples, sr):
        if not self.enabled:
            return None
        target = self._path(key)
        temporary = target.with_suffix('.npz.tmp')
        try:
            with open(temporary, 'wb') as handle:
                np.savez_compressed(handle, samples=np.asarray(samples, dtype=np.float32),
                                    sr=np.asarray([int(sr)], dtype=np.int64))
            os.replace(temporary, target)  # atomic: no half-written cache entry is ever read
        except OSError:
            if temporary.exists():
                temporary.unlink()
            return None
        self.trim()
        return str(target)

    def total_bytes(self):
        if not self.directory.exists():
            return 0
        return sum(p.stat().st_size for p in self.directory.glob('*.npz'))

    def trim(self):
        if not self.directory.exists():
            return 0
        entries = sorted(self.directory.glob('*.npz'), key=lambda p: p.stat().st_mtime)
        removed = 0
        total = self.total_bytes()
        for entry in entries:
            if total <= self.max_bytes:
                break
            size = entry.stat().st_size
            try:
                entry.unlink()
            except OSError:
                continue
            total -= size
            removed += 1
        return removed

    def clear(self):
        if not self.directory.exists():
            return 0
        removed = 0
        for entry in self.directory.glob('*.npz'):
            try:
                entry.unlink()
                removed += 1
            except OSError:
                pass
        return removed
