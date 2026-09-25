"""Tests for the optional ffmpeg realism pass (ported from the owner's work)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import audiofile, realism

HAVE_FFMPEG = bool(realism.ffmpeg_path())


def tone(seconds=0.5, sr=24000):
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return (0.25 * np.sin(2 * np.pi * 190.0 * t)).astype(np.float32)


class ChainTests(unittest.TestCase):
    def test_phone_band_is_a_real_telephone_band(self):
        chain = realism.chain('phone')
        self.assertIn('highpass=f=250', chain)
        self.assertIn('lowpass=f=3400', chain)
        self.assertIn('loudnorm=I=-16', chain)
        self.assertIn('acompressor', chain)

    def test_studio_keeps_the_full_band(self):
        chain = realism.chain('studio')
        self.assertIn('highpass=f=70', chain)
        self.assertNotIn('lowpass=f=3400', chain)

    def test_raw_only_normalises_loudness(self):
        self.assertEqual(realism.chain('raw'), 'loudnorm=I=-16:TP=-1.5:LRA=9')

    def test_none_is_empty(self):
        self.assertEqual(realism.chain('none'), '')

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            realism.chain('teleport')

    def test_personality_shift_moves_pitch_and_restores_tempo(self):
        chain = realism.chain('studio', personality='deep', sample_rate=24000)
        self.assertIn('asetrate=%d' % int(24000 * 0.965), chain)
        self.assertIn('atempo=%.6f' % (1.0 / 0.965), chain)

    def test_default_personality_does_not_resample(self):
        chain = realism.chain('studio', personality='lya')
        self.assertNotIn('asetrate', chain)
        self.assertIn('highpass=f=70', chain)

    def test_deeper_setting_adds_a_treble_touch(self):
        self.assertIn('treble=g=1', realism.chain('studio', depth=0.9))
        self.assertNotIn('treble=g=1', realism.chain('studio', depth=0.3))

    def test_ambience_is_seeded_and_low(self):
        first = realism.ambience_chain('phone', seed=7)
        self.assertEqual(first, realism.ambience_chain('phone', seed=7))
        self.assertIn('seed=7', first)
        self.assertIn('volume=-42dB', first)
        self.assertIn('volume=-48dB', realism.ambience_chain('studio', seed=7))


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix='alya-realism-'))
        self.raw = self.folder / 'raw.wav'
        audiofile.write_wav(self.raw, tone(), 24000)

    def test_missing_ffmpeg_is_a_clear_error(self):
        with mock.patch('alya_voice.realism.ffmpeg_path', return_value=None):
            available, reason = realism.available()
            self.assertFalse(available)
            self.assertIn('ffmpeg', reason)
            with self.assertRaises(realism.RealismError):
                realism.apply(self.raw, self.folder / 'out.mp3', mode='studio')

    def test_none_mode_refuses_to_write_anything(self):
        with self.assertRaises(ValueError):
            realism.apply(self.raw, self.folder / 'out.mp3', mode='none')

    @unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg is not installed')
    def test_phone_pass_produces_a_smaller_band_file(self):
        out = realism.apply(self.raw, self.folder / 'phone.mp3', mode='phone', seed=3)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 1000)
        samples, rate = audiofile.read_wav(
            realism.apply(self.raw, self.folder / 'phone.wav', mode='phone', seed=3))
        self.assertEqual(rate, 24000)
        spectrum = np.abs(np.fft.rfft(samples.astype(np.float64)))
        freqs = np.fft.rfftfreq(len(samples), 1.0 / rate)
        high = float(np.sum(spectrum[freqs > 4000]))

        unprocessed, _ = audiofile.read_wav(self.raw)
        base = np.abs(np.fft.rfft(unprocessed.astype(np.float64)))
        base_high = float(np.sum(base[freqs > 4000]))
        self.assertLess(high, base_high * 0.6)


if __name__ == '__main__':
    unittest.main()
