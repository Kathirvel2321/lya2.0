"""Windows SAPI fallback: instant, offline, zero model files.

Rendered to a temporary WAV through SpFileStream so the rest of the stack gets
PCM like every other local engine. Emotion is expressed through SSML prosody,
which SAPI voices implement inconsistently - this is the economy path, not the
quality path, and it is English-only unless a Tamil SAPI voice is installed.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
from xml.sax.saxutils import escape

from .. import audiofile, dsp
from .base import Chunk, Engine, EngineError

_SVSF_IS_XML = 8
_SSFMCreateForWrite = 3


def _female_english_voice(engine):
    for voice in engine.GetVoices():
        try:
            if voice.GetAttribute('Gender') != 'Female':
                continue
            languages = voice.GetAttribute('Language').split(';')
            if any((int(code, 16) & 0x3ff) == 9 for code in languages):
                return voice
        except (ValueError, AttributeError):
            continue
    return None


def ssml_for(span):
    rate = max(-60, min(60, int(span.rate_pct)))
    pitch = max(-50, min(50, int(round(span.pitch_hz / 2.0))))  # SAPI pitch is a relative percent
    volume = max(-50, min(25, int(span.volume_pct)))
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        "<prosody rate='%+d%%' pitch='%+d%%' volume='%+d%%'>%s</prosody></speak>"
        % (rate, pitch, volume, escape(span.text))
    )


class SapiEngine(Engine):
    name = 'offline_sapi'
    kind = 'local'
    supports_dsp = False          # prosody is already applied by SSML

    def __init__(self, persona, voice_hint=None):
        self.persona = persona
        self.voice_hint = voice_hint
        self._stop = threading.Event()
        self._engine = None

    def _voice(self):
        import win32com.client
        if self._engine is None:
            self._engine = win32com.client.Dispatch('SAPI.SpVoice')
            chosen = None
            if self.voice_hint:
                for voice in self._engine.GetVoices():
                    if self.voice_hint.lower() in voice.GetDescription().lower():
                        chosen = voice
                        break
            chosen = chosen or _female_english_voice(self._engine)
            if chosen is None:
                raise EngineError('no installed female English SAPI voice')
            self._engine.Voice = chosen
        return self._engine

    def available(self):
        try:
            import win32com.client  # noqa: F401
        except Exception as error:                        # pragma: no cover - env dependent
            return False, 'pywin32 is not importable (%s)' % error
        try:
            if self._voice() is None:
                return False, 'no female English SAPI voice found'
        except Exception as error:
            return False, 'SAPI unavailable (%s)' % error
        return True, 'Windows SAPI female voice (prosody support varies by voice)'

    def _render_span(self, span):
        import win32com.client
        engine = self._voice()
        handle, path = tempfile.mkstemp(suffix='.wav', prefix='alya-sapi-')
        os.close(handle)
        stream = win32com.client.Dispatch('SAPI.SpFileStream')
        try:
            stream.Open(path, _SSFMCreateForWrite, False)
            engine.AudioOutputStream = stream
            engine.Speak(ssml_for(span), _SVSF_IS_XML)
            stream.Close()
            samples, sr = audiofile.read_wav(path)
        finally:
            try:
                engine.AudioOutputStream = None
            except Exception:
                pass
            try:
                os.remove(path)
            except OSError:
                pass
        return samples, sr

    def render(self, plan, seed=0):
        self._stop.clear()
        started = time.perf_counter()
        first = None
        for span in plan.spans:
            if self._stop.is_set():
                return
            if span.language != 'en':
                raise EngineError('the economy SAPI voice is English-only; it refuses to mispronounce Tamil')
            span_started = time.perf_counter()
            samples, sr = self._render_span(span)
            synth_ms = (time.perf_counter() - span_started) * 1000.0
            samples = dsp.humanize(samples, sr, cents=span.humanize_cents * 0.6,
                                   seed=int(seed or 0) * 1000 + span.index)
            samples = dsp.normalize_loudness(samples, target_dbfs=-16.0)
            samples = dsp.fade_edges(samples, sr)
            if first is None:
                first = (time.perf_counter() - started) * 1000.0
            yield Chunk(index=span.index, engine=self.name, text=span.text, samples=samples,
                        sample_rate=int(sr), seconds=float(dsp.as_float(samples).size) / float(sr),
                        paused_after_ms=span.pause_after_ms, breath_before=False,
                        first_audio_ms=first, synth_ms=synth_ms,
                        language=span.language, emotion=span.emotion)

    def stop(self):
        self._stop.set()

    def close(self):
        self._engine = None
