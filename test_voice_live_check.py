"""Diagnostic stage checks with fake audio/model/playback; no hardware access."""
import unittest
from unittest.mock import Mock, patch
import numpy as np
from tools.check_voice_live import check


class LiveCheckTests(unittest.TestCase):
    def test_stage_results_and_no_command_transcription(self):
        from audio import voice
        for mode in ('name', 'clap', 'silence', 'sound_only'):
            with self.subTest(mode=mode):
                stream = Mock()
                stream.__enter__ = Mock(return_value=stream)
                stream.__exit__ = Mock(return_value=False)
                samples = np.zeros(320, np.int16)
                if mode != 'silence':
                    samples[:32] = np.random.default_rng(7).choice([-12000, 12000], 32)
                stream.read.return_value = (samples.tobytes(), False)

                def loop(callback, **kwargs):
                    import sounddevice as sd
                    with sd.RawInputStream() as mic:
                        kwargs['on_ready']()
                        pcm, _ = mic.read(320)
                    if mode == 'clap':
                        detector = voice.DoubleClap()
                        detector.feed(pcm)
                        for _ in range(15):
                            detector.feed(bytes(640))
                        detector.feed(pcm)
                        self.assertTrue(detector.feed(bytes(640)))
                    if mode in ('clap', 'name'):
                        callback('wake up lya', False)
                        self.assertTrue(kwargs['stop_event'].is_set())
                    self.assertTrue(kwargs['offline_required'])

                with patch('sounddevice.RawInputStream', return_value=stream), \
                     patch.object(voice, 'wake_loop', side_effect=loop), \
                     patch('winsound.PlaySound') as play, \
                     patch.object(voice, 'transcribe', side_effect=AssertionError('transcription forbidden')):
                    result = check(output=Mock())
                self.assertTrue(result['microphone_opened'])
                self.assertEqual(result['sound_received'], mode != 'silence')
                self.assertEqual(result['name_detected'], mode == 'name')
                self.assertEqual(result['double_clap_detected'], mode == 'clap')
                self.assertEqual(result['greeting_playback_started'], mode in ('clap', 'name'))
                self.assertEqual(play.call_count, int(mode in ('clap', 'name')))

    def test_failure_is_not_reported_as_success(self):
        with patch('audio.voice.wake_loop', side_effect=RuntimeError('fake failure')):
            result = check(output=Mock())
        self.assertFalse(result['microphone_opened'])
        self.assertFalse(result['greeting_playback_started'])
        self.assertEqual(result['error'], 'RuntimeError')


if __name__ == '__main__':
    unittest.main()
