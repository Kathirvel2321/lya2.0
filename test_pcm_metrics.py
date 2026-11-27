"""Synthetic audio blocks only. No microphone, private data or network use."""
import unittest
from unittest.mock import patch

import numpy as np

from audio import pcm_metrics, voice


class PcmMetricsChecks(unittest.TestCase):
    def test_fallback_retains_counts_and_peak_at_pcm16_limits(self):
        pcm = b'\x00\x80\xff\x7f\xff'
        with patch.object(pcm_metrics, '_native_measure', None):
            count, peak, rms = pcm_metrics.measure_pcm16(pcm)
            self.assertEqual((count, peak), (2, 32768))
            self.assertAlmostEqual(rms, 32767.5, delta=0.005)
            self.assertEqual(pcm_metrics.measure_pcm16(b'\xff'), (0, 0, 0.0))

    def test_native_matches_fallback_at_real_microphone_block_sizes(self):
        if pcm_metrics._native_measure is None:
            self.skipTest('Build the optional Rust library to exercise its Python bridge.')
        rng = np.random.default_rng(19)
        blocks = [b'', b'\xff', bytes(640), b'\x00\x80\xff\x7f\xff']
        for count in (1, 320, 512, 2000):
            blocks.extend(rng.integers(-32768, 32768, count, dtype=np.int16).tobytes()
                          for _ in range(12))
        for block in blocks:
            count, peak, rms = pcm_metrics.measure_pcm16(block)
            with patch.object(pcm_metrics, '_native_measure', None):
                expected_count, expected_peak, expected_rms = pcm_metrics.measure_pcm16(block)
            self.assertEqual((count, peak), (expected_count, expected_peak))
            self.assertAlmostEqual(rms, expected_rms, delta=0.005)

    def test_telemetry_keeps_its_peak_threshold_and_sample_count(self):
        for backend in (pcm_metrics._native_measure, None):
            with patch.object(pcm_metrics, '_native_measure', backend), \
                 patch.object(voice, '_STATS', dict(voice._STATS, window=None)):
                voice._reset_listener_stats()
                voice._note_audio((700).to_bytes(2, 'little'), threshold=700)
                self.assertEqual(voice._STATS['loud_blocks'], 0)
                voice._note_audio((701).to_bytes(2, 'little'), threshold=700)
                self.assertEqual(voice._STATS['loud_blocks'], 1)
                self.assertEqual(voice._STATS['samples'], 2)
                self.assertEqual(voice._STATS['peak'], 701)
