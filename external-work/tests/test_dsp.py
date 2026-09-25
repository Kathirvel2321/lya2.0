import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import audiofile, dsp

SR = 22050


def tone(f0=200.0, seconds=0.6, sr=SR, harmonics=6):
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    signal = np.zeros_like(t)
    for index in range(1, harmonics + 1):
        signal += (1.0 / index) * np.sin(2 * np.pi * f0 * index * t)
    return (0.3 * signal / np.abs(signal).max()).astype(np.float32)


def dominant_hz(samples, sr=SR):
    spectrum = np.abs(np.fft.rfft(np.asarray(samples, dtype=np.float64)))
    return float(np.fft.rfftfreq(len(samples), 1.0 / sr)[int(np.argmax(spectrum))])


def envelope_in_band(samples, sr=SR, low=300.0, high=3500.0):
    magnitude, freqs = dsp.spectral_envelope(samples, sr)
    mask = (freqs >= low) & (freqs <= high)
    return 20.0 * np.log10(np.maximum(magnitude[mask], 1e-9))


class BasicSignalTests(unittest.TestCase):
    def test_as_float_and_helpers(self):
        self.assertEqual(dsp.as_float([0.1, 0.2]).dtype, np.float32)
        self.assertEqual(dsp.silence(100, SR).size, 2205)
        self.assertEqual(dsp.peak(np.zeros(10)), 0.0)
        self.assertAlmostEqual(dsp.rms(np.ones(10)), 1.0, places=6)

    def test_concat_and_fade(self):
        joined = dsp.concat([np.ones(100, dtype=np.float32), np.ones(50, dtype=np.float32)])
        self.assertEqual(joined.size, 150)
        faded = dsp.fade_edges(np.ones(1000, dtype=np.float32), SR, ms=5)
        self.assertLess(abs(float(faded[0])), 0.2)
        self.assertLess(abs(float(faded[-1])), 0.2)
        self.assertAlmostEqual(float(faded[500]), 1.0, places=5)

    def test_empty_inputs_are_safe(self):
        empty = np.zeros(0, dtype=np.float32)
        for function in (lambda x: dsp.pitch_shift(x, SR, 2.0),
                         lambda x: dsp.humanize(x, SR, 20.0),
                         lambda x: dsp.normalize_loudness(x),
                         lambda x: dsp.limiter(x),
                         lambda x: dsp.time_stretch(x, 1.3, SR),
                         lambda x: dsp.resample_linear(x, 1.2)):
            self.assertEqual(function(empty).size, 0)

    def test_limiter_cannot_exceed_ceiling(self):
        loud = np.full(500, 3.0, dtype=np.float32)
        self.assertLessEqual(dsp.peak(dsp.limiter(loud, ceiling=0.9)), 0.9001)

    def test_loudness_normalisation_hits_the_target(self):
        for amplitude in (0.02, 0.5):
            signal = (tone() * (amplitude / 0.3)).astype(np.float32)
            result = dsp.normalize_loudness(signal, target_dbfs=-16.0)
            measured = 20.0 * np.log10(max(dsp.rms(result), 1e-9))
            self.assertTrue(-18.5 < measured < -13.5, measured)


class PitchTests(unittest.TestCase):
    def test_duration_is_preserved(self):
        signal = tone(seconds=0.8)
        for semitones in (-4.0, -2.0, 2.0, 4.0):
            self.assertEqual(dsp.pitch_shift(signal, SR, semitones).size, signal.size, semitones)

    def test_pitch_ratio_matches_request(self):
        signal = tone(f0=200.0, seconds=0.8)
        for semitones in (-3.0, 3.0):
            measured = dominant_hz(dsp.pitch_shift(signal, SR, semitones, formant=False))
            expected = 200.0 * (2.0 ** (semitones / 12.0))
            self.assertLess(abs(measured - expected) / expected, 0.06,
                            '%s vs %s' % (measured, expected))

    def test_formant_correction_keeps_the_spectral_shape(self):
        signal = tone(f0=180.0, seconds=1.0, harmonics=10)
        plain = dsp.pitch_shift(signal, SR, 4.0, formant=False)
        corrected = dsp.pitch_shift(signal, SR, 4.0, formant=True)
        reference = envelope_in_band(signal)
        plain_error = float(np.mean(np.abs(envelope_in_band(plain) - reference)))
        corrected_error = float(np.mean(np.abs(envelope_in_band(corrected) - reference)))
        self.assertLess(corrected_error, plain_error)
        self.assertEqual(corrected.size, signal.size)

    def test_tiny_shift_is_a_passthrough(self):
        signal = tone()
        self.assertTrue(np.array_equal(dsp.pitch_shift(signal, SR, 0.0), signal))

    def test_time_stretch_approximates_the_factor(self):
        signal = tone(seconds=1.0)
        for factor in (0.8, 1.3):
            stretched = dsp.time_stretch(signal, factor, SR)
            self.assertLess(abs(stretched.size / signal.size - factor), 0.12, factor)

    def test_resample_ratio(self):
        self.assertEqual(dsp.resample_linear(np.ones(1000, dtype=np.float32), 2.0).size, 500)
        self.assertEqual(dsp.resample_linear(np.ones(1000, dtype=np.float32), 1.0).size, 1000)


class HumanisingTests(unittest.TestCase):
    def test_vibrato_keeps_length_and_stays_bounded(self):
        signal = tone()
        wobbled = dsp.vibrato(signal, SR, cents=30.0, rate_hz=5.0)
        self.assertEqual(wobbled.size, signal.size)
        self.assertLessEqual(dsp.peak(wobbled), dsp.peak(signal) * 1.05)
        self.assertTrue(np.isfinite(wobbled).all())

    def test_humanize_changes_the_signal_without_breaking_it(self):
        signal = tone(seconds=1.0)
        human = dsp.humanize(signal, SR, cents=20.0, seed=4)
        self.assertEqual(human.size, signal.size)
        self.assertFalse(np.array_equal(human, signal))
        self.assertTrue(np.isfinite(human).all())
        self.assertLessEqual(dsp.peak(human), dsp.peak(signal) * 1.05)

    def test_humanize_is_reproducible_with_a_seed(self):
        signal = tone(seconds=0.5)
        self.assertTrue(np.array_equal(dsp.humanize(signal, SR, cents=15.0, seed=11),
                                       dsp.humanize(signal, SR, cents=15.0, seed=11)))

    def test_breath_is_quiet_and_the_right_length(self):
        puff = dsp.breath(SR, ms=120, level=0.05, seed=1)
        self.assertEqual(puff.size, int(SR * 0.120))
        self.assertLessEqual(dsp.peak(puff), 0.051)
        self.assertTrue(np.isfinite(puff).all())

    def test_breath_has_no_dc_offset(self):
        self.assertLess(abs(float(np.mean(dsp.breath(SR, ms=200, level=0.08, seed=2)))), 0.01)


class AudioFileTests(unittest.TestCase):
    def test_wav_round_trip(self):
        import tempfile
        signal = tone(seconds=0.2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.wav'
            audiofile.write_wav(path, signal, SR)
            restored, rate = audiofile.read_wav(path)
        self.assertEqual(rate, SR)
        self.assertEqual(restored.size, signal.size)
        self.assertLess(float(np.max(np.abs(restored - signal))), 0.001)
        self.assertTrue(np.isfinite(restored).all())

    def test_int16_conversion_clips_safely(self):
        clipped = audiofile.float_to_int16(np.array([2.0, -2.0, 0.0], dtype=np.float32))
        self.assertEqual(clipped.tolist(), [32767, -32767, 0])

    def test_duration_helper(self):
        self.assertAlmostEqual(audiofile.duration_seconds(np.zeros(SR, dtype=np.float32), SR), 1.0)


if __name__ == '__main__':
    unittest.main()
