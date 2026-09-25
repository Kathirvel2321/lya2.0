"""Optional remote engine: Microsoft Edge neural voices through edge-tts.

Free, no API key, no account, and it runs the model on their servers, so the
laptop cost is a few MB of RAM. It is also the only free way found to keep one
female timbre across English and Tamil (en-US-AvaMultilingualNeural).

This engine is OFF by default (config/policy.json: "remote": "disabled") because
speech text leaves the device. It refuses anything above 'public' sensitivity.
The service escapes text as XML, so no SSML can be injected. The reply arrives
as MP3, which this stack does not decode, so remote spans are played as files
and skip the DSP stage. Temporary MP3s are deleted by cleanup_temp().
"""
from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

from .. import audiofile
from ..privacy import Policy
from .base import Chunk, Engine, EngineError


def _pct(value, low, high):
    return '%+d%%' % max(low, min(high, int(value)))


def _hz(value, low, high):
    return '%+dHz' % max(low, min(high, int(value)))


class EdgeEngine(Engine):
    name = 'cloud_edge'
    kind = 'remote'
    supports_dsp = False          # MP3 stream is not decoded locally

    def __init__(self, persona, policy=None, mode='unified', temp_dir=None,
                 connect_timeout=10, receive_timeout=60):
        self.persona = persona
        self.policy = policy or Policy()
        self.mode = mode
        self.temp_dir = Path(temp_dir) if temp_dir else Path(__file__).resolve().parents[2] / 'out' / 'remote'
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
        except Exception as error:                        # pragma: no cover - env dependent
            return False, 'edge-tts is not importable (%s)' % error
        decision = self.policy.decide(self.name, sensitivity, allow_remote)
        if not decision.allowed:
            return False, decision.reason
        return True, 'remote voice %s (text leaves the device)' % self._voice(self.persona.languages[0])

    def _render_span(self, span):
        import edge_tts
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        voice = self._voice(span.language)
        target = self.temp_dir / ('span-%03d-%d.mp3' % (span.index, time.time_ns() % 100000))
        communicate = edge_tts.Communicate(span.text, voice,
                                           rate=_pct(span.rate_pct, -40, 40),
                                           pitch=_hz(span.pitch_hz, -35, 35),
                                           volume=_pct(span.volume_pct, -30, 15),
                                           connect_timeout=self.connect_timeout,
                                           receive_timeout=self.receive_timeout)
        asyncio.run(communicate.save(str(target)))
        if not target.exists() or target.stat().st_size == 0:
            raise EngineError('remote service returned no audio')
        self._files.append(target)
        return target

    def render(self, plan, seed=0, allow_remote=False, sensitivity='public'):
        self._stop.clear()
        decision = self.policy.decide(self.name, sensitivity, allow_remote)
        if not decision.allowed:
            raise EngineError('remote engine refused: %s' % decision.reason)
        started = time.perf_counter()
        first = None
        for span in plan.spans:
            if self._stop.is_set():
                return
            span_started = time.perf_counter()
            path = self._render_span(span)
            if first is None:
                first = (time.perf_counter() - started) * 1000.0
            yield Chunk(index=span.index, engine=self.name, text=span.text, path=str(path),
                        sample_rate=0, seconds=audiofile.mp3_duration_estimate(path),
                        paused_after_ms=span.pause_after_ms, breath_before=False,
                        first_audio_ms=first, synth_ms=(time.perf_counter() - span_started) * 1000.0,
                        language=span.language, emotion=span.emotion)

    def probe(self, text='Vanakkam, this is a voice test.', language='ta'):
        """Opt-in live check used by tools/probe_edge.py. Never called implicitly."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        voice = self._voice(language)
        target = self.temp_dir / ('probe-%s.mp3' % language)
        import edge_tts
        started = time.perf_counter()
        asyncio.run(edge_tts.Communicate(text, voice,
                                         connect_timeout=self.connect_timeout,
                                         receive_timeout=self.receive_timeout).save(str(target)))
        return {'language': language, 'voice': voice, 'file': str(target),
                'bytes': target.stat().st_size,
                'seconds_estimate': audiofile.mp3_duration_estimate(target),
                'elapsed_ms': (time.perf_counter() - started) * 1000.0}

    def cleanup_temp(self):
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
