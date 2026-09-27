"""Comprehensive unit tests for LYA offline voice wake and audio pipeline.

Checks:
1. Speech rate bounds & fallback behavior (set_rate).
2. Audio stream WAV framing & header fidelity (_wav).
3. R04 Voice Wake interruption ("stop" & "cancel" break through speaking loops & expired windows).
4. Wake word regex matching, command extraction, and conversation timeout gating (45s window).
5. Voice liveness replay and duration detection (voice_liveness).
6. Quiet mode suppression.
"""
import io
import math
import os
import time
import unittest
import wave
import numpy as np

from audio import voice
from security.liveness import voice_liveness


class VoicePipelineTests(unittest.TestCase):
    def setUp(self):
        voice.set_quiet(False)
        voice._SPEAKING.clear()
        # Listener telemetry lives in module state; clear it so one test's device
        # name or counted window can never leak into another test's assertions.
        voice._reset_listener_stats()
        voice._STATS['device'] = None
        voice._STATS['window'] = None

    def tearDown(self):
        voice.set_quiet(False)
        voice._SPEAKING.clear()
        voice._reset_listener_stats()
        voice._STATS['device'] = None
        voice._STATS['window'] = None

    def test_set_rate_bounds_and_fallback(self):
        # Valid rate
        self.assertTrue(voice.set_rate(200))
        # Non-numeric rate falls back to 175 without crashing
        self.assertTrue(voice.set_rate("invalid_rate"))
        # Out-of-bounds rates (<60 or >400) fall back to 175
        self.assertTrue(voice.set_rate(10))
        self.assertTrue(voice.set_rate(999))

    def test_wav_framing(self):
        # 16000 Hz, 16-bit mono = 32000 bytes per second
        raw_pcm = b"\x00\x08" * 8000  # 0.5s of 16-bit audio
        wav_buf = voice._wav(raw_pcm)
        self.assertIsInstance(wav_buf, io.BytesIO)

        with wave.open(wav_buf, "rb") as w:
            self.assertEqual(w.getnchannels(), 1)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getframerate(), 16000)
            self.assertEqual(w.getnframes(), 8000)
            frames = w.readframes(w.getnframes())
            self.assertEqual(frames, raw_pcm)

    def test_r04_interruption_during_speaking(self):
        calls = []
        def handler(text, quiet):
            calls.append((text, quiet))

        # Simulate engine is actively speaking
        voice._SPEAKING.set()

        # Normal command while speaking must be ignored to prevent self-triggering
        handled, _ = voice.process_utterance("what time is it", last_wake_time=time.monotonic(), on_wake=handler)
        self.assertFalse(handled)
        self.assertEqual(len(calls), 0)

        # R04: "stop" and "cancel" MUST pass through immediately even while speaking
        handled, last = voice.process_utterance("stop", last_wake_time=time.monotonic(), on_wake=handler)
        self.assertTrue(handled)
        self.assertEqual(last, 0.0)
        self.assertEqual(calls, [("stop", False)])

        calls.clear()
        handled, last = voice.process_utterance("cancel", last_wake_time=0.0, on_wake=handler)
        self.assertTrue(handled)
        self.assertEqual(last, 0.0)
        self.assertEqual(calls, [("cancel", False)])

    def test_wake_words_and_extraction(self):
        received = []
        def handler(text, quiet):
            received.append(text)

        test_cases = [
            ("hey lya what time is it", "what time is it"),
            ("wake up leya show files", "show files"),
            ("liya status", "status"),
            ("lya", "wake up lya"),
            ("hey liya", "wake up lya"),
            ("wake up lya", "wake up lya"),
            ("laya", "wake up lya"),
            ("leya", "wake up lya"),
            ("elya", "wake up lya"),
            ("please laya help me", "help me"),
            ("hey lya wake up", "wake up lya"),
        ]

        for utterance, expected in test_cases:
            received.clear()
            handled, last = voice.process_utterance(utterance, last_wake_time=0.0, on_wake=handler)
            self.assertTrue(handled, f"Failed for utterance: {utterance}")
            self.assertGreater(last, 0.0)
            self.assertEqual(received, [expected])

    def test_conversation_window_and_expiration(self):
        received = []
        def handler(text, quiet):
            received.append(text)

        # Utterance without wake word when window is 0 (expired) -> ignored
        handled, _ = voice.process_utterance("show files", last_wake_time=0.0, on_wake=handler)
        self.assertFalse(handled)
        self.assertEqual(len(received), 0)

        # Now wake up LYA
        handled, wake_time = voice.process_utterance("hey lya", last_wake_time=0.0, on_wake=handler)
        self.assertTrue(handled)
        self.assertEqual(received, ["wake up lya"])

        # Subsequent command within active window (simulating 5s later) -> accepted without wake word
        received.clear()
        handled, wake_time2 = voice.process_utterance("what time is it", last_wake_time=wake_time, on_wake=handler)
        self.assertTrue(handled)
        self.assertEqual(received, ["what time is it"])
        self.assertGreaterEqual(wake_time2, wake_time)

        # After conversation timeout (simulating 50s later) -> ignored
        received.clear()
        expired_time = time.monotonic() - 50.0
        handled, _ = voice.process_utterance("show files", last_wake_time=expired_time, on_wake=handler)
        self.assertFalse(handled)
        self.assertEqual(len(received), 0)

    def test_voice_liveness_detection(self):
        # 1. Short audio (<1.0s) must fail
        short_pcm = b"\x00\x10" * 3200  # 0.2s
        short_wav = voice._wav(short_pcm).getvalue()
        live, detail = voice_liveness(short_wav)
        self.assertFalse(live)
        self.assertIn("too short", detail)

        # 2. Constant sine tone (flat energy device replay artifact) must fail
        tone_frames = bytearray()
        for i in range(16000 * 2):  # 2.0s constant tone
            tone_frames += int(3000 * math.sin(2 * math.pi * 440 * i / 16000)).to_bytes(2, "little", signed=True)
        tone_wav = voice._wav(bytes(tone_frames)).getvalue()
        live, detail = voice_liveness(tone_wav)
        self.assertFalse(live)
        self.assertIn("replay suspected", detail)

        # 3. Dynamic audio with varying speech energy must pass
        varying_frames = bytearray()
        for i in range(16000 * 2):  # 2.0s
            amplitude = 500 if (i // 2000) % 2 == 0 else 4000
            sample = int(amplitude * math.sin(2 * math.pi * 220 * i / 16000))
            varying_frames += sample.to_bytes(2, "little", signed=True)
        varying_wav = voice._wav(bytes(varying_frames)).getvalue()
        live, detail = voice_liveness(varying_wav)
        self.assertTrue(live, f"Expected live audio to pass, got detail: {detail}")

    def test_quiet_mode(self):
        voice.set_quiet(True)
        self.assertTrue(voice.QUIET["on"])
        voice.speak("test speech")
        self.assertFalse(voice._SPEAKING.is_set())
        voice.set_quiet(False)
        self.assertFalse(voice.QUIET["on"])

    def test_offline_mode_refuses_missing_model_before_recording(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'LYA_VOSK_MODEL': ''}):
                with patch('storage.store.get_data_dir', return_value=Path(tmp)):
                    with patch.object(voice, '_record_stream', side_effect=AssertionError('microphone opened')):
                        with self.assertRaises(RuntimeError):
                            voice.wake_loop(lambda *a: None, offline_required=True)

    def test_wake_loop_transcribes_only_after_local_wake(self):
        import tempfile
        import threading
        from unittest.mock import patch
        events = []
        lengths = []
        stopped = threading.Event()
        sample = voice._wav(b'\x00\x08' * 8000)
        clock = [100.0]

        def on_wake(text, quiet):
            events.append(text)
            if len(events) == 1:
                voice._SPEAKING.set()
                clock[0] += 60  # A long spoken reply must not expire the user's next turn.
            else:
                stopped.set()

        class Recognizer:
            def AcceptWaveform(self, _pcm): return True
            def FinalResult(self): return '{"text":"wake up lya"}'

        def record(max_seconds, silence, stop_event, clap_enabled):
            lengths.append(max_seconds)
            self.assertEqual(silence, 0.8)
            return sample

        with tempfile.TemporaryDirectory() as model:
            with patch.dict(os.environ, {'LYA_VOSK_MODEL': model}):
                with patch.object(voice, '_local', object()):
                    with patch.object(voice, '_wait_for_wake', return_value=True) as wake:
                        with patch.object(voice, '_record_stream', side_effect=record):
                            with patch.object(voice, 'transcribe', return_value='show files') as remote:
                                with patch.object(voice.time, 'monotonic', side_effect=lambda: clock[0]), \
                                     patch.object(voice.time, 'sleep', side_effect=lambda _: voice._SPEAKING.clear()):
                                    voice.wake_loop(on_wake, stop_event=stopped, offline_required=False)
        self.assertEqual(lengths, [25])
        wake.assert_called_once()
        self.assertEqual(events, ['wake up lya', 'show files'])
        remote.assert_called_once()

    def test_double_clap_requires_two_short_separated_impulses(self):
        silence = np.zeros(320, np.int16).tobytes()
        pulse = np.zeros(320, np.int16)
        pulse[:32] = np.random.default_rng(7).choice([-12000, 12000], 32)
        pulse = pulse.tobytes()
        def detect(blocks):
            detector = voice.DoubleClap()
            return [i for i, block in enumerate(blocks) if detector.feed(block)]
        self.assertEqual(detect([silence] * 100), [])
        self.assertEqual(detect([pulse] + [silence] * 50), [])
        self.assertEqual(detect([pulse] + [silence] * 15 + [pulse, silence]), [17])
        quiet_pulse = (np.frombuffer(pulse, np.int16) // 10).astype(np.int16).tobytes()
        self.assertEqual(detect([quiet_pulse] + [silence] * 15 + [quiet_pulse, silence]), [17])
        background = np.random.default_rng(9).normal(0, 40, 320).astype(np.int16).tobytes()
        self.assertEqual(detect([background] * 100), [])
        self.assertEqual(detect([pulse] + [silence] * 3 + [pulse, silence]), [])
        self.assertEqual(detect([pulse] + [silence] * 45 + [pulse, silence]), [])
        self.assertEqual(detect([pulse] * 10 + [silence] * 15 + [pulse, silence]), [])
        tone = (5000 * np.sin(np.arange(320) * 0.1)).astype(np.int16).tobytes()
        self.assertEqual(detect([tone] + [silence] * 15 + [tone, silence]), [])
        with self.assertRaises(ValueError):
            voice.DoubleClap(0)

    def test_streaming_wake_and_claps_stay_local_and_close_stream(self):
        import threading
        from unittest.mock import Mock, patch
        for claps in (False, True):
            with self.subTest(claps=claps):
                stream = Mock()
                stream.__enter__ = Mock(return_value=stream)
                stream.__exit__ = Mock(return_value=False)
                recognizer = Mock()
                recognizer.AcceptWaveform.return_value = not claps
                recognizer.Result.return_value = '{"text":"please leah"}'
                quiet = np.zeros(320, np.int16)
                pulse = quiet.copy()
                pulse[:32] = np.random.default_rng(7).choice([-12000, 12000], 32)
                blocks = [quiet] if not claps else [pulse] + [quiet] * 15 + [pulse, quiet]
                stream.read.side_effect = [(b.tobytes(), False) for b in blocks]
                ready = Mock()
                with patch('sounddevice.RawInputStream', return_value=stream), \
                     patch('vosk.KaldiRecognizer', return_value=recognizer), \
                     patch.object(voice, 'transcribe', side_effect=AssertionError('ambient upload')):
                    self.assertTrue(voice._wait_for_wake(object(), claps, threading.Event(), ready))
                ready.assert_called_once()
                stream.__exit__.assert_called_once()

    def test_failed_microphone_is_not_reported_ready(self):
        from unittest.mock import Mock, patch
        ready = Mock()
        with patch('vosk.KaldiRecognizer'), \
             patch('sounddevice.RawInputStream', side_effect=RuntimeError('fake device failure')):
            with self.assertRaises(RuntimeError):
                voice._wait_for_wake(object(), False, None, ready)
        ready.assert_not_called()

    def test_provisional_name_that_disappears_cannot_wake(self):
        import threading
        from unittest.mock import Mock, patch
        stopped = threading.Event()
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        reads = []
        def read(_):
            reads.append(True)
            if len(reads) == 3:
                stopped.set()
            return bytes(640), False
        stream.read.side_effect = read
        recognizer = Mock()
        recognizer.AcceptWaveform.side_effect = [False, True]
        recognizer.PartialResult.return_value = '{"partial":"lia"}'
        recognizer.Result.return_value = '{"text":"[unk]"}'
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch('vosk.KaldiRecognizer', return_value=recognizer):
            self.assertFalse(voice._wait_for_wake(object(), False, stopped, None))

    def test_command_recorder_detects_claps_without_transcription(self):
        from unittest.mock import Mock, patch
        quiet = np.zeros(320, np.int16)
        pulse = quiet.copy()
        pulse[:32] = np.random.default_rng(7).choice([-12000, 12000], 32)
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.read.side_effect = [(b.tobytes(), False) for b in
                                   [pulse] + [quiet] * 15 + [pulse, quiet]]
        with patch('sounddevice.RawInputStream', return_value=stream):
            self.assertIs(voice._record_stream(clap_enabled=True), voice._CLAP_WAKE)

    def test_stopping_stream_cannot_emit_late_wake(self):
        import threading
        from unittest.mock import Mock, patch
        stopped = threading.Event()
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        def read(_):
            stopped.set()
            return bytes(640), False
        stream.read.side_effect = read
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch('vosk.KaldiRecognizer') as recognizer:
            self.assertFalse(voice._wait_for_wake(object(), False, stopped, None))
        recognizer.return_value.AcceptWaveform.assert_not_called()
        stream.__exit__.assert_called_once()

    def test_listener_errors_are_reported_and_bounded(self):
        import tempfile
        from unittest.mock import Mock, patch
        report = Mock()
        with tempfile.TemporaryDirectory() as model, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': model}), \
             patch.object(voice, '_local', object()), \
             patch.object(voice, '_wait_for_wake', side_effect=RuntimeError('fake microphone failure')), \
             patch.object(voice.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'three times'):
                voice.wake_loop(lambda *a: None, on_error=report)
        self.assertEqual(report.call_count, 3)

    def test_wake_recorder_does_not_open_mic_while_lya_speaks(self):
        from unittest.mock import patch
        voice._SPEAKING.set()
        with patch('sounddevice.RawInputStream', side_effect=AssertionError('microphone opened')):
            self.assertIsNone(voice._record_stream(max_seconds=1))

    def test_microphone_telemetry_counts_loudness_without_opening_a_stream(self):
        from unittest.mock import patch
        with patch('sounddevice.RawInputStream', side_effect=AssertionError('microphone opened')), \
             patch.object(voice, '_input_device_name', return_value=None):
            voice.mic_test_start(seconds=99)
            voice._note_audio(np.zeros(320, np.int16).tobytes())
            voice._note_audio((np.ones(320, np.int16) * 5000).tobytes())
            voice._note_clap()
            report = voice.mic_test_report()
        self.assertEqual(report['seconds'], voice._MIC_TEST_MAX_SECONDS)  # window is bounded
        self.assertEqual(report['samples'], 640)
        self.assertEqual(report['peak'], 5000)
        self.assertEqual(report['loud_blocks'], 1)
        self.assertEqual(report['claps'], 1)
        self.assertIsNone(report['device'])
        self.assertEqual(report['verdict'], 'no-listener')
        health = voice.listener_health()
        self.assertEqual(health['state'], 'stopped')
        self.assertFalse(health['listening'])

    def test_microphone_self_test_verdicts_for_silence_quiet_and_speech(self):
        from unittest.mock import patch
        for peak, verdict in ((0, 'silent'), (200, 'too-quiet'), (5000, 'hearing')):
            with self.subTest(verdict=verdict):
                voice._reset_listener_stats()
                voice._STATS['device'] = None
                voice._note_state('listening')
                with patch.object(voice, '_input_device_name', return_value='Synthetic microphone'):
                    voice.mic_test_start(seconds=5)
                voice._note_audio((np.ones(320, np.int16) * peak).tobytes())
                report = voice.mic_test_report()
                self.assertEqual(report['verdict'], verdict)
                self.assertEqual(report['device'], 'Synthetic microphone')
                self.assertTrue(report['detail'])
        voice._reset_listener_stats()
        voice._note_state('listening')
        with patch.object(voice, '_input_device_name', return_value='Synthetic microphone'):
            voice.mic_test_start()
        self.assertEqual(voice.mic_test_report()['verdict'], 'no-audio')
        voice._note_state('stopped')
        voice._STATS['window'] = None
        self.assertIsNone(voice.mic_test_report())

    def test_wake_telemetry_counts_during_speech_suppression(self):
        import threading
        from unittest.mock import Mock, patch
        voice._SPEAKING.set()
        stopped = threading.Event()
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        reads = []
        def read(_):
            reads.append(True)
            if len(reads) == 3:
                stopped.set()
            return (np.ones(320, np.int16) * 4000).tobytes(), False
        stream.read.side_effect = read
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
             patch('vosk.KaldiRecognizer') as recognizer:
            self.assertFalse(voice._wait_for_wake(object(), True, stopped, None))
        recognizer.return_value.AcceptWaveform.assert_not_called()
        health = voice.listener_health()
        self.assertEqual(health['device'], 'Synthetic microphone')
        self.assertEqual(health['samples'], 960)
        self.assertEqual(health['speaking_blocks'], 3)
        self.assertEqual(health['loud_blocks'], 3)  # loudness still counted while suppressed
        self.assertEqual(health['claps'], 0)        # clap detection stays suppressed
        self.assertFalse(health['listening'])

    def test_command_recorder_counts_blocks_and_releases_listener_state(self):
        from unittest.mock import Mock, patch
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.read.side_effect = [((np.ones(320, np.int16) * 3000).tobytes(), False),
                                   (np.zeros(320, np.int16).tobytes(), False)]
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'):
            self.assertIsNotNone(voice._record_stream(max_seconds=1, silence=0.02))
        health = voice.listener_health()
        self.assertEqual(health['samples'], 640)
        self.assertEqual(health['peak'], 3000)
        self.assertEqual(health['loud_blocks'], 1)
        self.assertFalse(health['listening'])

    @unittest.skipUnless(os.environ.get("LYA_RUN_ONLINE_TESTS") == "1", "Explicit online integration test; excluded from offline checks")
    def test_edge_tts_ava_voice_synthesis(self):
        import asyncio
        import edge_tts
        import tempfile
        import os
        # Test synthesis with default 21yo Ava voice and playful tone
        async def _synth():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            try:
                comm = edge_tts.Communicate("Hey there, I am Lya!", "en-US-AvaNeural", rate="+10%", pitch="+2Hz")
                await comm.save(tmp)
                self.assertTrue(os.path.exists(tmp))
                self.assertGreater(os.path.getsize(tmp), 1000)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        asyncio.run(_synth())

    def test_stop_speaking_playback_interruption(self):
        voice._SPEAKING.set()
        voice._STOP_PLAYBACK.clear()
        voice.stop_speaking()
        self.assertTrue(voice._STOP_PLAYBACK.is_set())
        self.assertFalse(voice._SPEAKING.is_set())

    def test_groq_whisper_transcription(self):
        from unittest.mock import patch
        raw_pcm = b"\x00\x08" * 8000
        wav_bytes = voice._wav(raw_pcm).getvalue()

        # When GROQ_API_KEY is configured, transcribe routes through _transcribe_groq
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_fake_key"}):
            with patch.object(voice, "_transcribe_groq", return_value="hello lya vanakkam") as mock_groq:
                result = voice.transcribe(wav_bytes, offline_required=False)
                self.assertEqual(result, "hello lya vanakkam")
                mock_groq.assert_called_once_with(wav_bytes, "gsk_test_fake_key")


if __name__ == "__main__":
    unittest.main()

