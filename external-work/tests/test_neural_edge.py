"""Tests for the neural (Edge) engine and its safety gates.

No network and no real MP3: `edge_tts` is replaced by a fake module, and every
policy comes from a temporary config file.
"""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import privacy
from alya_voice.director import Director
from alya_voice.emotions import EmotionTable
from alya_voice.engines.base import EngineError, hz_string, pct_string
from alya_voice.engines.neural_edge import NeuralEdgeEngine
from alya_voice.persona import load_persona

CALLS = []


class FakeCommunicate:
    def __init__(self, text, voice, **kwargs):
        self.text, self.voice, self.kwargs = text, voice, kwargs
        CALLS.append({'text': text, 'voice': voice, 'kwargs': kwargs})

    async def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b'ID3' + b'\x00' * 6000)   # 48 kbps CBR stand-in


def fake_edge_module():
    module = types.ModuleType('edge_tts')
    module.Communicate = FakeCommunicate
    module.__version__ = 'fake'
    return module


def opt_in_policy(folder):
    payload = json.loads(Path(privacy.Policy().source).read_text(encoding='utf-8'))
    payload['remote'] = 'opt_in'
    path = Path(folder) / 'policy.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    return privacy.Policy(path)


class NeuralEdgeTests(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        self.folder = Path(tempfile.mkdtemp(prefix='alya-neural-'))
        self.persona = load_persona()
        self.policy = opt_in_policy(self.folder)
        self.plan = Director(self.persona, EmotionTable()).build(
            'The backup finished. Everything is safe.', emotion='serious',
            seed=5, allow_interjections=False)
        self._saved = sys.modules.get('edge_tts')
        sys.modules['edge_tts'] = fake_edge_module()

    def tearDown(self):
        if self._saved is None:
            sys.modules.pop('edge_tts', None)
        else:
            sys.modules['edge_tts'] = self._saved

    def make(self, **kwargs):
        kwargs.setdefault('policy', self.policy)
        kwargs.setdefault('work_dir', self.folder / 'work')
        return NeuralEdgeEngine(self.persona, **kwargs)

    def test_one_request_per_span_with_emotion_prosody(self):
        engine = self.make(cache_bytes=0, keep_files=True)
        chunks = list(engine.render(self.plan, allow_remote=True))
        self.assertEqual(len(chunks), len(self.plan.spans))
        self.assertEqual(len(CALLS), len(self.plan.spans))
        for span, call in zip(self.plan.spans, CALLS):
            self.assertEqual(call['text'], span.text)
            self.assertEqual(call['kwargs']['rate'], pct_string(span.rate_pct, -40, 40))
            self.assertEqual(call['kwargs']['pitch'], hz_string(span.pitch_hz, -35, 35))
        self.assertTrue(all(chunk.path.endswith('.mp3') for chunk in chunks))
        self.assertFalse(any(chunk.cached for chunk in chunks))
        self.assertGreater(chunks[0].seconds, 0.0)

    def test_one_voice_for_both_languages(self):
        engine = self.make(cache_bytes=0)
        tamil = Director(self.persona, EmotionTable()).build('வணக்கம். நலம்.', seed=5)
        list(engine.render(tamil, allow_remote=True))
        voices = {call['voice'] for call in CALLS}
        self.assertEqual(len(voices), 1)
        self.assertIn('Multilingual', voices.pop())

    def test_second_render_comes_from_cache_without_a_request(self):
        engine = self.make(cache_bytes=10_000_000)
        first = list(engine.render(self.plan, allow_remote=True))
        self.assertEqual(len(CALLS), len(self.plan.spans))
        CALLS.clear()
        second = list(engine.render(self.plan, allow_remote=True))
        self.assertEqual(CALLS, [])
        self.assertTrue(all(chunk.cached for chunk in second))
        self.assertEqual([c.path for c in first], [c.path for c in second])

    def test_cache_larger_than_its_cap_is_trimmed(self):
        engine = self.make(cache_bytes=8000)
        list(engine.render(self.plan, allow_remote=True))
        total = sum(p.stat().st_size for p in engine.cache_dir.glob('*.mp3'))
        self.assertLessEqual(total, 8000 + 6100)

    def test_temporary_files_are_deleted_when_not_kept(self):
        engine = self.make(cache_bytes=0, keep_files=False)
        list(engine.render(self.plan, allow_remote=True))
        engine.cleanup_temp()
        self.assertEqual(list((self.folder / 'work').glob('*.mp3')), [])

    def test_kept_files_are_not_deleted(self):
        engine = self.make(cache_bytes=0, keep_files=True)
        list(engine.render(self.plan, allow_remote=True))
        engine.cleanup_temp()
        self.assertEqual(len(list((self.folder / 'work').glob('*.mp3'))), len(self.plan.spans))

    def test_policy_disabled_means_engine_error_not_a_request(self):
        engine = self.make(policy=privacy.Policy(), cache_bytes=0)
        with self.assertRaises(EngineError):
            list(engine.render(self.plan, allow_remote=True))
        self.assertEqual(CALLS, [])

    def test_private_text_is_refused_even_when_opted_in(self):
        engine = self.make(cache_bytes=0)
        with self.assertRaises(EngineError):
            list(engine.render(self.plan, allow_remote=True, sensitivity='private'))
        self.assertEqual(CALLS, [])

    def test_availability_reports_the_policy_reason(self):
        blocked, reason = self.make(policy=privacy.Policy(), cache_bytes=0).available()
        self.assertFalse(blocked)
        self.assertIn('disabled by policy', reason)
        allowed, reason = self.make(cache_bytes=0).available(allow_remote=True)
        self.assertTrue(allowed)
        self.assertIn('leaves this device', reason)


if __name__ == '__main__':
    unittest.main()
