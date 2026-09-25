"""Live local checks against the real pinned Piper models.

Skipped automatically when piper-tts or the model files are missing, so the
suite still passes on a bare machine. Nothing here plays audio or uses network.
"""
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import audiofile
from alya_voice.audit import Auditor
from alya_voice.engines import build
from alya_voice.engines.offline_piper import default_models_dir
from alya_voice.persona import load_persona
from alya_voice.runtime import Voice


def models_ready():
    try:
        import piper  # noqa: F401
    except Exception:
        return False
    models = default_models_dir()
    persona = load_persona()
    return all((models / (name + '.onnx')).exists()
               for name in (persona.voice('piper', 'en', 'unified'),
                            persona.voice('piper', 'en', 'per_language')))


@unittest.skipUnless(models_ready(), 'pinned Piper models or piper-tts are not installed')
class LocalPiperTests(unittest.TestCase):
    def setUp(self):
        self.persona = load_persona()
        self.folder = tempfile.mkdtemp(prefix='alya-piper-')

    def speak(self, text, **kwargs):
        voice = Voice(self.persona, keep_warm=True,
                      auditor=Auditor(Path(self.folder) / 'audit', enabled=True))
        try:
            return voice.speak(text, play=False, engine='offline_piper',
                               wav=Path(self.folder) / 'out.wav', **kwargs)
        finally:
            voice.close()

    def test_english_renders_audible_audio(self):
        report = self.speak('Good evening. The backup finished four minutes ago.',
                            allow_interjections=False, seed=11)
        self.assertEqual(report.engine, 'offline_piper')
        samples, rate = audiofile.read_wav(report.wav)
        self.assertGreater(report.audio_seconds, 0.5)
        self.assertGreater(float(np.max(np.abs(samples))), 0.01)
        self.assertLess(report.total_ms / max(report.audio_seconds * 1000.0, 1.0), 8.0)

    def test_conversation_styles_do_not_apply_pitch_or_breath_effects(self):
        with patch('alya_voice.engines.offline_piper.dsp.pitch_shift') as pitch, \
                patch('alya_voice.engines.offline_piper.dsp.humanize') as wobble, \
                patch('alya_voice.engines.offline_piper.dsp.breath') as breath:
            for style in ('everyday', 'joyful'):
                report = self.speak('Hello, I am right here with you.', style=style,
                                    allow_interjections=False)
                self.assertGreater(report.audio_seconds, 0)
            pitch.assert_not_called()
            wobble.assert_not_called()
            breath.assert_not_called()

    def test_tamil_renders_audible_audio(self):
        report = self.speak('வணக்கம். உங்கள் கோப்புகள் தயாராக உள்ளன.',
                            allow_interjections=False, seed=11)
        samples, _ = audiofile.read_wav(report.wav)
        self.assertGreater(report.audio_seconds, 0.5)
        self.assertGreater(float(np.max(np.abs(samples))), 0.01)

    def test_unified_mode_uses_one_model_for_both_languages(self):
        engine = build('offline_piper', self.persona, mode='unified')
        try:
            self.assertEqual(engine._model_for('en'), engine._model_for('ta'))
        finally:
            engine.close()

    def test_native_mode_uses_a_model_per_language(self):
        engine = build('offline_piper', self.persona, mode='native')
        try:
            self.assertNotEqual(engine._model_for('en'), engine._model_for('ta'))
        finally:
            engine.close()

    def test_availability_reports_the_model_folder(self):
        usable, reason = build('offline_piper', self.persona).available()
        self.assertTrue(usable)
        self.assertIn('model', reason)

    def test_missing_models_are_reported_not_crashed(self):
        engine = build('offline_piper', self.persona, models_dir=Path(self.folder) / 'empty')
        usable, reason = engine.available()
        self.assertFalse(usable)
        self.assertIn('missing model', reason)


if __name__ == '__main__':
    unittest.main()
