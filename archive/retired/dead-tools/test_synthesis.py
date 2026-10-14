"""Synthetic policy checks: no playback, microphone, network or real storage."""
import unittest
from unittest.mock import Mock, patch
from audio.synthesis import prepare, segments, speak, KokoroSession

class SynthesisTests(unittest.TestCase):
    def test_mixed_tamil_english_routes_without_translation(self):
        parts=list(segments('வணக்கம் buddy. உங்கள் task முடிந்தது.'))
        self.assertEqual([p[0] for p in parts], ['ta','en','ta','en','ta'])

    def test_explicit_latin_language_and_unknown_scripts(self):
        self.assertEqual(list(segments('Bonjour à vous', 'fr'))[0][0], 'fr')
        with self.assertRaises(ValueError): list(segments('안녕하세요'))

    def test_bounded_spoken_text_and_code(self):
        self.assertNotIn('secret_code',prepare('Hi ```secret_code``` there'))
        self.assertNotIn('example.com',prepare('See https://example.com'))
        self.assertLessEqual(len(prepare('word '*1000)), 900)

    def test_economy_never_mispronounces_tamil(self):
        with patch('audio.synthesis.sapi') as sapi:
            with self.assertRaises(RuntimeError): speak('வணக்கம்',engine='economy')
            sapi.assert_not_called()

    def test_missing_english_model_uses_local_female_fallback(self):
        with patch('audio.synthesis.Renderer') as renderer, patch('audio.synthesis.sapi') as sapi:
            renderer.return_value.audio.side_effect=FileNotFoundError()
            speak('Hello')
            sapi.assert_called_once_with('Hello','warm')

    def test_partial_failure_never_repeats_audio(self):
        def broken(*args):
            yield [0.0]*30,24000
            raise RuntimeError('failure')
        with patch('audio.synthesis.Renderer') as renderer, patch('sounddevice.play'), patch('audio.synthesis.sapi') as sapi:
            renderer.return_value.audio.side_effect=broken
            with self.assertRaises(RuntimeError): speak('Hello')
            sapi.assert_not_called()

    def test_export_speed_adapter_preserves_fraction(self):
        import numpy as np
        runtime=Mock(); wrapped=KokoroSession(runtime); wrapped.speed=.96
        wrapped.run(None,{'speed':np.array([0],dtype=np.int32)})
        value=runtime.run.call_args.args[1]['speed']
        self.assertAlmostEqual(float(value[0]),.96,places=5)
        self.assertEqual(value.dtype,np.float32)

if __name__=='__main__': unittest.main()
