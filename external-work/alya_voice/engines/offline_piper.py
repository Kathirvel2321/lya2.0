"""Local Piper synthesis: native or unified speakers, bounded CPU, no network.

Reuses the model files already pinned in the LYA project (`models/voice`) so
nothing is downloaded. Model sessions are created on demand, limited to two CPU
threads with idle spinning off, and released by close().
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import numpy as np

from .. import dsp
from .base import Chunk, Engine, EngineError

_THREADS = 2


def default_models_dir():
    override = os.environ.get('ALYA_VOICE_MODELS')
    if override:
        return Path(override)
    workspace = Path(__file__).resolve().parents[3] / 'models' / 'voice'
    if workspace.exists():
        return workspace
    return Path(__file__).resolve().parents[2] / 'models' / 'voice'


def _session(model_path):
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = _THREADS
    options.inter_op_num_threads = 1
    options.add_session_config_entry('session.intra_op.allow_spinning', '0')
    options.add_session_config_entry('session.inter_op.allow_spinning', '0')
    return ort.InferenceSession(str(model_path), sess_options=options,
                                providers=['CPUExecutionProvider'])


class PiperEngine(Engine):
    name = 'offline_piper'
    kind = 'local'

    def __init__(self, persona, models_dir=None, mode='unified', strict_phonemes=False):
        if mode not in ('unified', 'native'):
            raise ValueError("mode must be 'unified' or 'native'")
        self.persona = persona
        self.models_dir = Path(models_dir or default_models_dir())
        self.mode = mode
        self.strict_phonemes = bool(strict_phonemes)
        self._sessions = {}
        self._voices = {}
        self._stop = threading.Event()

    def _model_for(self, language):
        mode = 'unified' if self.mode == 'unified' else 'per_language'
        return self.persona.voice('piper', language, mode)

    def models(self):
        return sorted({self._model_for(lang) for lang in self.persona.languages})

    def available(self):
        try:
            import piper  # noqa: F401
        except Exception as error:                       # pragma: no cover - env dependent
            return False, 'piper-tts is not importable (%s)' % error
        missing = [name for name in self.models()
                   if not (self.models_dir / (name + '.onnx')).exists()]
        if missing:
            return False, 'missing model file(s) in %s: %s' % (self.models_dir, ', '.join(missing))
        timbre = 'one timbre for both languages' if self.mode == 'unified' else 'one model per language'
        return True, '%d model(s) in %s (%s)' % (len(self.models()), self.models_dir, timbre)

    def _voice(self, language):
        from piper import PiperVoice
        from piper.config import PiperConfig
        model = self._model_for(language)
        espeak = 'ta' if language == 'ta' else 'en-us'
        key = (model, espeak)
        if key not in self._voices:
            config = PiperConfig.from_dict(
                json.loads((self.models_dir / (model + '.onnx.json')).read_text(encoding='utf-8')))
            config.espeak_voice = espeak
            if model not in self._sessions:
                self._sessions[model] = _session(self.models_dir / (model + '.onnx'))
            self._voices[key] = PiperVoice(self._sessions[model], config)
        return self._voices[key]

    def _synthesize(self, voice, span):
        from piper.config import SynthesisConfig
        speed = max(0.55, 1.0 + float(span.rate_pct) / 100.0)
        # Lower variance keeps consonants cleaner after the bounded prosody pass,
        # especially when one unified model speaks both English and Tamil.
        config = SynthesisConfig(length_scale=1.0 / speed, noise_scale=0.55, noise_w_scale=0.7)
        if self.strict_phonemes:
            try:
                unsupported = [p for row in voice.phonemize(span.text) for p in row
                               if p not in voice.config.phoneme_id_map]
            except AttributeError:
                unsupported = []
            if unsupported:
                raise EngineError('unsupported pronunciation in span %d' % span.index)
        chunks = list(voice.synthesize(span.text, config))
        if not chunks:
            raise EngineError('piper produced no audio for span %d' % span.index)
        return (np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32),
                int(chunks[0].sample_rate))

    def render(self, plan, seed=0):
        self._stop.clear()
        started = time.perf_counter()
        first = None
        for span in plan.spans:
            if self._stop.is_set():
                return
            span_started = time.perf_counter()
            samples, sr = self._synthesize(self._voice(span.language), span)
            synth_ms = (time.perf_counter() - span_started) * 1000.0
            span_seed = int(seed or 0) * 1000 + span.index
            clean_delivery = plan.style in ('everyday', 'joyful')
            if span.breath_before and not clean_delivery:
                intake = dsp.breath(sr, 110, level=0.05 * max(span.breath_amount, 0.3), seed=span_seed)
                samples = np.concatenate([intake, np.zeros(int(sr * 0.03), dtype=np.float32), samples])
            if not clean_delivery:
                samples = dsp.pitch_shift(samples, sr, self.persona.semitones(span.pitch_hz), formant=True)
                samples = dsp.humanize(samples, sr, cents=span.humanize_cents, seed=span_seed)
            samples = dsp.apply_volume(samples, span.volume_pct)
            samples = dsp.normalize_loudness(samples, target_dbfs=-16.0)
            samples = dsp.fade_edges(samples, sr)
            if first is None:
                first = (time.perf_counter() - started) * 1000.0
            yield Chunk(index=span.index, engine=self.name, text=span.text, samples=samples,
                        sample_rate=int(sr), seconds=float(dsp.as_float(samples).size) / float(sr),
                        paused_after_ms=span.pause_after_ms, breath_before=span.breath_before,
                        first_audio_ms=first, synth_ms=synth_ms,
                        language=span.language, emotion=span.emotion)

    def stop(self):
        self._stop.set()

    def close(self):
        self._voices.clear()
        self._sessions.clear()
