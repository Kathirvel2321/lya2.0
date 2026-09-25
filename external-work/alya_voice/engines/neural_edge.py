"""Primary quality engine: Microsoft Edge neural voices (free, no key, no account).

Why this engine exists
----------------------
The local Piper voice is private and offline but plainly synthetic, and in the
project's `unified` mode a Tamil acoustic model also speaks the English words, so
the English accent is a compromise. Edge neural voices are the only free option
found that (a) sound like a real young woman and (b) can keep one timbre across
Tamil and English, because `en-US-AvaMultilingualNeural` is documented by
Microsoft as supporting `ta-IN`.

How it differs from the older `cloud_edge` engine
-------------------------------------------------
It streams: each planned span is its own file, handed to the runtime
immediately, so the first words play while the rest is still being synthesised
and a cancel takes effect between spans. Emotion still comes from the shared
director (per-sentence emotion, per-clause variation, style vector) - exactly
what the service itself refuses to do through `mstts:express-as`.

Privacy
-------
Text leaves this device. Therefore: policy refuses the engine unless the owner
opted in, anything above `public` sensitivity never reaches it, temporary audio is
deleted after playback, and the optional cache stores only hashed keys and audio
(never the source text) with a byte cap.
"""
from __future__ import annotations

import asyncio
import hashlib
import threading
import time
from pathlib import Path

from .. import audiofile
from ..privacy import Policy
from .base import Chunk, Engine, EngineError, hz_string, pct_string


class NeuralEdgeEngine(Engine):
    name = 'neural_edge'
    kind = 'remote'
    supports_dsp = False          # MP3 arrives compressed; no local decode stage

    def __init__(self, persona, policy=None, mode='unified', work_dir=None,
                 cache_bytes=0, keep_files=False, connect_timeout=10, receive_timeout=60):
        self.persona = persona
        self.policy = policy or Policy()
        self.mode = mode
        self.work_dir = Path(work_dir) if work_dir else (
            Path(__file__).resolve().parents[2] / 'out' / 'neural')
        self.cache_bytes = int(cache_bytes)
        self.keep_files = bool(keep_files)
        self.connect_timeout = int(connect_timeout)
        self.receive_timeout = int(receive_timeout)
        self._stop = threading.Event()
        self._files = []

    def _voice(self, language):
        mode = 'unified' if self.mode == 'unified' else 'per_language'
        return self.persona.voice('cloud_edge', language, mode)

    def available(self, allow_remote=None, sensitivity='public'):
        try:
            import edge_tts  # noqa: F401
        except Exception as error:                       # pragma: no cover - env dependent
            return False, 'edge-tts is not importable (%s)' % error
        decision = self.policy.decide(self.name, sensitivity, allow_remote)
        if not decision.allowed:
            return False, decision.reason
        return True, 'neural voice %s (text leaves this device)' % self._voice(self.persona.languages[0])

    @property
    def cache_dir(self):
        return self.work_dir / 'cache'

    def _cache_path(self, span):
        voice = self._voice(span.language)
        key = hashlib.sha256('\x1f'.join((
            voice, span.text, pct_string(span.rate_pct, -40, 40),
            hz_string(span.pitch_hz, -35, 35), pct_string(span.volume_pct, -30, 15),
        )).encode('utf-8')).hexdigest()[:32]
        return self.cache_dir / ('%s.mp3' % key)

    def _trim_cache(self):
        if self.cache_bytes <= 0 or not self.cache_dir.exists():
            return 0
        entries = sorted(self.cache_dir.glob('*.mp3'), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in entries)
        removed = 0
        for entry in entries:
            if total <= self.cache_bytes:
                break
            size = entry.stat().st_size
            try:
                entry.unlink()
                removed += 1
                total -= size
            except OSError:
                continue
        return removed

    def _synthesize(self, span):
        import edge_tts
        voice = self._voice(span.language)
        target = self._cache_path(span) if self.cache_bytes else None
        if target is not None and target.exists() and target.stat().st_size > 0:
            return target, True
        if target is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            target = self.work_dir / ('span-%03d-%d.mp3' % (span.index, time.time_ns() % 100000))
        communicate = edge_tts.Communicate(
            span.text, voice,
            rate=pct_string(span.rate_pct, -40, 40),
            pitch=hz_string(span.pitch_hz, -35, 35),
            volume=pct_string(span.volume_pct, -30, 15),
            connect_timeout=self.connect_timeout,
            receive_timeout=self.receive_timeout,
        )
        try:
            asyncio.run(communicate.save(str(target)))
        except Exception as error:
            raise EngineError('neural voice request failed (%s)' % error)
        if not target.exists() or target.stat().st_size == 0:
            raise EngineError('neural voice returned no audio')
        if self.cache_bytes:
            self._trim_cache()
        else:
            self._files.append(target)
        return target, False

    def render(self, plan, seed=0, allow_remote=False, sensitivity='public'):
        self._stop.clear()
        decision = self.policy.decide(self.name, sensitivity, allow_remote)
        if not decision.allowed:
            raise EngineError('neural voice refused: %s' % decision.reason)
        started = time.perf_counter()
        first = None
        for span in plan.spans:
            if self._stop.is_set():
                return
            span_started = time.perf_counter()
            path, cached = self._synthesize(span)
            if first is None and not cached:
                first = (time.perf_counter() - started) * 1000.0
            yield Chunk(index=span.index, engine=self.name, text=span.text, path=str(path),
                        seconds=audiofile.mp3_duration_estimate(path),
                        paused_after_ms=span.pause_after_ms, breath_before=False,
                        first_audio_ms=(first if first is not None else 0.0),
                        synth_ms=(time.perf_counter() - span_started) * 1000.0,
                        language=span.language, emotion=span.emotion, cached=cached)

    def cleanup_temp(self):
        """Delete synthesised audio that was not requested to be kept."""
        if self.keep_files:
            return 0
        removed = 0
        for path in list(self._files):
            try:
                Path(path).unlink()
                removed += 1
            except OSError:
                continue
        self._files.clear()
        return removed

    def stop(self):
        self._stop.set()

    def close(self):
        self.cleanup_temp()
