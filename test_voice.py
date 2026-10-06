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
        from unittest.mock import patch
        engine = patch.dict(os.environ, {'LYA_COMMAND_ASR': 'vosk', 'LYA_MICROPHONE': ''})
        engine.start()
        self.addCleanup(engine.stop)
        voice.set_quiet(False)
        voice._SPEAKING.clear()
        voice._THINKING.clear()
        # Listener telemetry lives in module state; clear it so one test's device
        # name or counted window can never leak into another test's assertions.
        voice._reset_listener_stats()
        voice._STATS['device'] = None
        voice._STATS['window'] = None

    def tearDown(self):
        voice.set_quiet(False)
        voice._SPEAKING.clear()
        voice._THINKING.clear()
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

    def test_native_input_and_all_finalized_transcript_segments(self):
        import tempfile
        from unittest.mock import Mock, patch
        sound = Mock()
        sound.query_hostapis.return_value = [
            {'name': 'MME', 'default_input_device': 1},
            {'name': 'Windows WASAPI', 'default_input_device': 14}]
        self.assertEqual(voice._input_device(sound), 14)
        sound.query_hostapis.return_value = [{'name': 'MME', 'default_input_device': 1}]
        self.assertIsNone(voice._input_device(sound))
        recognizer = Mock()
        recognizer.AcceptWaveform.side_effect = [True, False]
        recognizer.Result.return_value = '{"text":"current Mumbai"}'
        recognizer.FinalResult.return_value = '{"text":"weather"}'
        with tempfile.TemporaryDirectory() as model, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': model}), \
             patch.object(voice, '_local', object()), \
             patch('vosk.KaldiRecognizer', return_value=recognizer):
            wav = voice._wav(bytes(3000)).getvalue()
            self.assertEqual(voice.transcribe(wav), 'current Mumbai weather')

    def test_selected_microphone_prefers_native_and_missing_input_fails(self):
        from unittest.mock import Mock, patch
        sound = Mock()
        sound.query_devices.return_value = [
            {'name': 'Synthetic mic', 'max_input_channels': 1, 'hostapi': 0},
            {'name': 'Synthetic mic', 'max_input_channels': 1, 'hostapi': 1},
            {'name': 'Output only', 'max_input_channels': 0, 'hostapi': 1}]
        sound.query_hostapis.side_effect = lambda index: {'name': ('MME', 'Windows WASAPI')[index]}
        with patch.dict(os.environ, {'LYA_MICROPHONE': 'Synthetic mic'}):
            self.assertEqual(voice._input_device(sound), 1)
        with patch.dict(os.environ, {'LYA_MICROPHONE': 'Disconnected mic'}):
            with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                voice._input_device(sound)

    def test_disabling_voice_during_decode_never_dispatches_late_question(self):
        import tempfile
        import threading
        from unittest.mock import Mock, patch
        stopped = threading.Event()
        callback = Mock()
        def decode(*args, **kwargs):
            stopped.set()
            return 'stale question'
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': folder}), \
             patch.object(voice, '_local', object()), \
             patch.object(voice, '_wait_for_wake', return_value=True), \
             patch.object(voice, '_record_stream', return_value=voice._wav(bytes(640))), \
             patch.object(voice, 'transcribe', side_effect=decode):
            voice.wake_loop(callback, stop_event=stopped)
        self.assertEqual(callback.call_count, 1)  # Wake only; no decoded question.
        self.assertNotEqual(callback.call_args.args[0], 'stale question')

    def test_long_active_turn_keeps_context_after_capture_and_decoder_delay(self):
        import tempfile
        import threading
        from unittest.mock import patch
        stopped = threading.Event()
        clock = [100.0]
        text = 'I have class tomorrow, Lya, help me plan my morning.'
        calls = []

        def callback(words, quiet):
            calls.append(words)
            if len(calls) == 2:
                stopped.set()

        def decode(*args, **kwargs):
            clock[0] += 75  # Longer than the idle conversation window.
            return text

        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': folder}), \
             patch.object(voice, '_local', object()), \
             patch.object(voice, '_wait_for_wake', return_value=True), \
             patch.object(voice, '_record_stream', return_value=voice._wav(bytes(640))), \
             patch.object(voice, 'transcribe', side_effect=decode), \
             patch.object(voice.time, 'monotonic', side_effect=lambda: clock[0]):
            voice.wake_loop(callback, stop_event=stopped)
        self.assertEqual(calls, ['wake up lya', text])

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

    def test_active_conversation_keeps_name_and_all_context_without_regreeting(self):
        from unittest.mock import Mock
        callback = Mock()
        current = time.monotonic()
        text = 'I have class tomorrow, Lya, can you help me plan my morning?'
        handled, last = voice.process_utterance(text, current, callback)
        self.assertTrue(handled)
        callback.assert_called_once_with(text, False)
        for standalone in ('lya', 'hey lya', 'wake up lya', 'hey lya wake up',
                           'Hey, Lya.', ' Lya, wake up! ', 'Wake up, Lya!'):
            callback.reset_mock()
            handled, last = voice.process_utterance(standalone, last, callback)
            self.assertTrue(handled)
            callback.assert_not_called()

    def test_active_name_at_start_or_end_does_not_drop_question(self):
        from unittest.mock import Mock
        callback = Mock()
        for text in ('Can you explain this to me, Lya?', 'Lya, can you explain this to me?'):
            callback.reset_mock()
            voice.process_utterance(text, time.monotonic(), callback)
            callback.assert_called_once_with(text, False)

    def test_punctuated_stop_interrupts_speaking_without_a_wake(self):
        from unittest.mock import Mock
        callback = Mock()
        voice._SPEAKING.set()
        handled, last = voice.process_utterance('Stop.', 0.0, callback)
        self.assertTrue(handled)
        self.assertEqual(last, 0.0)
        callback.assert_called_once_with('stop', False)

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

        def record(max_seconds, silence, stop_event, clap_enabled, endpoint_model, on_state, use_vad):
            lengths.append(max_seconds)
            self.assertEqual(silence, 2.5)
            self.assertIs(endpoint_model, voice._local)
            self.assertTrue(use_vad)
            return sample

        with tempfile.TemporaryDirectory() as model:
            with patch.dict(os.environ, {'LYA_VOSK_MODEL': model}):
                with patch.object(voice, '_local', object()):
                    with patch.object(voice, '_wait_for_wake', return_value=True) as wake:
                        with patch.object(voice, '_record_stream', side_effect=record):
                            with patch.object(voice, 'transcribe', return_value='show files') as remote:
                                with patch.object(voice.time, 'monotonic', side_effect=lambda: clock[0]), \
                                     patch.object(voice, '_wait_for_interrupt', side_effect=lambda *a: voice._SPEAKING.clear()):
                                    voice.wake_loop(on_wake, stop_event=stopped, offline_required=False)
            self.assertEqual(lengths, [120])
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

    def test_command_endpoint_allows_continuation_above_noise_gate_and_ignores_empty_results(self):
        from unittest.mock import Mock, patch
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        pcm = (np.ones(320, np.int16) * 3000).tobytes()
        stream.read.side_effect = [(pcm, False)] * 69
        recognizer = Mock()
        count = [0]
        def accept(_):
            count[0] += 1
            return count[0] in (1, 4, 10)
        recognizer.AcceptWaveform.side_effect = accept
        recognizer.Result.side_effect = ['{"text":""}', '{"text":"what time"}', '{"text":"is it"}']
        recognizer.PartialResult.side_effect = lambda: ('{"partial":"is it"}'
                                                       if 6 <= count[0] < 10 else '{"partial":""}')
        model = object()
        states = []
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
             patch('vosk.KaldiRecognizer', return_value=recognizer) as build, \
             patch.object(voice, 'transcribe', side_effect=AssertionError('capture must stay local')):
            captured = voice._record_stream(silence=1.2, endpoint_model=model, on_state=states.append)
        build.assert_called_once_with(model, 16000)
        self.assertEqual(stream.read.call_count, 69)
        self.assertEqual(states, ['listening', 'hearing'])
        with wave.open(captured, 'rb') as wav:
            self.assertEqual(wav.readframes(wav.getnframes()), pcm * 69)
        stream.__exit__.assert_called_once()
        self.assertFalse(voice.listener_health()['listening'])

    def test_command_endpoint_keeps_silence_fallback_when_words_are_unrecognized(self):
        from unittest.mock import Mock, patch
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.read.side_effect = [((np.ones(320, np.int16) * 3000).tobytes(), False),
                                  (bytes(640), False)]
        recognizer = Mock()
        recognizer.AcceptWaveform.return_value = False
        recognizer.PartialResult.return_value = '{"partial":"synthetic"}'
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
             patch('vosk.KaldiRecognizer', return_value=recognizer):
            self.assertIsNotNone(voice._record_stream(silence=0.02, endpoint_model=object()))
        self.assertEqual(stream.read.call_count, 2)

    def test_slow_question_survives_internal_pause_and_ends_after_final_pause(self):
        from unittest.mock import Mock, patch
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        first = np.full(320, 900, np.int16).tobytes()
        second = np.full(320, 1300, np.int16).tobytes()
        blocks = [first] * 5 + [bytes(640)] * 90 + [second] * 5 + [bytes(640)] * 125
        stream.read.side_effect = [(block, False) for block in blocks]
        activity = Mock()
        activity.feed.side_effect = [True] * 5 + [False] * 90 + [True] * 5 + [False] * 125
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic mic'), \
             patch.object(voice, 'SpeechActivity', return_value=activity):
            capture = voice._record_stream(max_seconds=120, silence=2.5, use_vad=True)
        with wave.open(capture, 'rb') as wav:
            self.assertEqual(wav.readframes(wav.getnframes()), b''.join(blocks))
        self.assertEqual(stream.read.call_count, len(blocks))

    def test_adaptive_endpoint_keeps_short_turns_fast_and_slow_turns_complete(self):
        from unittest.mock import Mock, patch
        # 20ms blocks: short speech, 8s speech, and a resumed 1.8s pause.
        cases = ([True] * 25 + [False] * 100,
                 [True] * 400 + [False] * 150,
                 [True] * 25 + [False] * 90 + [True] * 25 + [False] * 140
                 + [True] * 25 + [False] * 150)
        for activity_blocks in cases:
            with self.subTest(blocks=len(activity_blocks)):
                stream = Mock()
                stream.__enter__ = Mock(return_value=stream)
                stream.__exit__ = Mock(return_value=False)
                blocks = [np.full(320, 900 if active else 0, np.int16).tobytes()
                          for active in activity_blocks]
                stream.read.side_effect = [(block, False) for block in blocks]
                activity = Mock()
                activity.feed.side_effect = activity_blocks
                with patch('sounddevice.RawInputStream', return_value=stream), patch.object(
                        voice, '_input_device_name', return_value='Synthetic mic'), patch.object(
                        voice, 'SpeechActivity', return_value=activity):
                    capture = voice._record_stream(max_seconds=120, silence=2.0,
                                                   continuation_silence=3.0, use_vad=True)
                with wave.open(capture, 'rb') as wav:
                    self.assertEqual(wav.readframes(wav.getnframes()), b''.join(blocks))
                self.assertEqual(stream.read.call_count, len(blocks))

    def test_noise_alone_does_not_start_a_model_gated_question(self):
        import threading
        from unittest.mock import Mock, patch
        stopped = threading.Event()
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        reads = [0]
        def read(_):
            reads[0] += 1
            if reads[0] == 4:
                stopped.set()
            return np.full(320, 3000, np.int16).tobytes(), False
        stream.read.side_effect = read
        recognizer = Mock()
        recognizer.AcceptWaveform.return_value = False
        recognizer.PartialResult.return_value = '{"partial":""}'
        states = []
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
             patch('vosk.KaldiRecognizer', return_value=recognizer):
            self.assertIsNone(voice._record_stream(endpoint_model=object(), stop_event=stopped,
                                                   on_state=states.append))
        self.assertEqual(states, ['listening'])

    def test_vad_delimits_question_despite_continuous_loud_room_noise(self):
        from unittest.mock import Mock, patch
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        pcm = np.full(320, 3000, np.int16).tobytes()
        stream.read.side_effect = [(pcm, False)] * 6
        activity = Mock()
        activity.feed.side_effect = [False, False, True, True, False, False]
        states = []
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
             patch.object(voice, 'SpeechActivity', return_value=activity), \
             patch('vosk.KaldiRecognizer', side_effect=AssertionError('no duplicate endpoint model')):
            captured = voice._record_stream(silence=0.04, use_vad=True, endpoint_model=object(),
                                            on_state=states.append)
        self.assertEqual(states, ['listening', 'hearing'])
        with wave.open(captured, 'rb') as wav:
            self.assertEqual(wav.readframes(wav.getnframes()), pcm * 6)

    def test_capture_limit_rejects_truncated_question(self):
        from unittest.mock import Mock, patch
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.read.return_value = (np.full(320, 3000, np.int16).tobytes(), False)
        with patch('sounddevice.RawInputStream', return_value=stream), \
             patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
             patch.object(voice, '_note_audio'), patch.object(voice, '_note_state'), \
             patch.object(voice.time, 'monotonic', side_effect=[0, 0, 2]):
            with self.assertRaises(voice.RecognitionUncertain):
                voice._record_stream(max_seconds=1)

    def test_uncertain_transcript_is_not_returned_as_a_question(self):
        import tempfile
        from unittest.mock import Mock, patch
        recognizer = Mock()
        recognizer.AcceptWaveform.return_value = False
        recognizer.FinalResult.return_value = '{"text":"Mumbai testnet", "result":[{"conf":0.3},{"conf":0.9}]}'
        with tempfile.TemporaryDirectory() as model, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': model}), \
             patch.object(voice, '_local', object()), \
             patch('vosk.KaldiRecognizer', return_value=recognizer):
            with self.assertRaises(voice.RecognitionUncertain):
                voice.transcribe(voice._wav(bytes(640)).getvalue())
        recognizer.SetWords.assert_called_once_with(True)

    def test_uncertain_capture_requests_repeat_without_forwarding_or_counting_device_failure(self):
        import tempfile
        import threading
        from unittest.mock import Mock, patch
        stopped = threading.Event()
        wake = Mock()
        error = Mock()
        retry = Mock(side_effect=lambda candidate, paused: stopped.set())
        with tempfile.TemporaryDirectory() as model, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': model}), \
             patch.object(voice, '_local', object()), \
             patch.object(voice, '_wait_for_wake', return_value=True), \
             patch.object(voice, '_record_stream', side_effect=voice.RecognitionUncertain('synthetic')):
            voice.wake_loop(wake, stop_event=stopped, on_error=error, on_retry=retry)
        wake.assert_called_once_with('wake up lya', False)
        error.assert_not_called()
        retry.assert_called_once_with('', False)

    def test_uncertain_turns_pause_after_two_and_reset_after_a_good_question(self):
        import tempfile
        import threading
        from unittest.mock import Mock, call, patch
        for with_good_question in (False, True):
            with self.subTest(with_good_question=with_good_question):
                wake, retry, error = Mock(), Mock(), Mock()
                uncertain = voice.RecognitionUncertain('synthetic', 'lower the volume')
                turns = [uncertain, uncertain]
                expected = [call('lower the volume', False), call('lower the volume', True)]
                if with_good_question:
                    turns.insert(1, voice._wav(bytes(640)))
                    expected.insert(1, call('lower the volume', False))
                    turns.insert(2, uncertain)
                with tempfile.TemporaryDirectory() as model, \
                     patch.dict(os.environ, {'LYA_VOSK_MODEL': model}), \
                     patch.object(voice, '_local', object()), \
                     patch.object(voice.time, 'monotonic', return_value=100), \
                     patch.object(voice, '_wait_for_wake', side_effect=[True, False]) as waiting, \
                     patch.object(voice, '_record_stream', side_effect=turns) as recording, \
                     patch.object(voice, 'transcribe', return_value='what time is it'):
                    voice.wake_loop(wake, stop_event=threading.Event(), on_error=error, on_retry=retry)
                self.assertEqual(retry.call_args_list, expected)
                self.assertEqual(waiting.call_count, 2)
                self.assertEqual(recording.call_count, len(turns))
                self.assertEqual(wake.call_args_list, [call('wake up lya', False)] +
                                 ([call('what time is it', False)] if with_good_question else []))
                error.assert_not_called()

    def test_stopped_uncertain_decoder_cannot_emit_a_late_retry(self):
        import tempfile
        import threading
        from unittest.mock import Mock, patch
        stopped = threading.Event()
        wake, retry = Mock(), Mock()
        def decode(*args, **kwargs):
            stopped.set()
            raise voice.RecognitionUncertain('synthetic', 'volume down')
        with tempfile.TemporaryDirectory() as model, \
             patch.dict(os.environ, {'LYA_VOSK_MODEL': model}), \
             patch.object(voice, '_local', object()), \
             patch.object(voice, '_wait_for_wake', return_value=True), \
             patch.object(voice, '_record_stream', return_value=voice._wav(bytes(640))), \
             patch.object(voice, 'transcribe', side_effect=decode):
            voice.wake_loop(wake, stop_event=stopped, on_retry=retry)
        wake.assert_called_once_with('wake up lya', False)
        retry.assert_not_called()

    def test_spoken_stop_works_during_reply_and_thinking_without_forwarding_other_words(self):
        import threading
        from unittest.mock import Mock, patch
        for busy in (voice._SPEAKING, voice._THINKING):
            with self.subTest(busy=busy):
                busy.set()
                stream = Mock()
                stream.__enter__ = Mock(return_value=stream)
                stream.__exit__ = Mock(return_value=False)
                stream.read.return_value = (bytes(640), False)
                recognizer = Mock()
                recognizer.AcceptWaveform.return_value = False
                recognizer.PartialResult.side_effect = ['{"partial":"what weather"}',
                                                        '{"partial":"stop"}', '{"partial":"stop"}']
                callback = Mock()
                with patch('sounddevice.RawInputStream', return_value=stream), \
                     patch.object(voice, '_input_device_name', return_value='Synthetic microphone'), \
                     patch('vosk.KaldiRecognizer', return_value=recognizer), \
                     patch.object(voice, 'transcribe', side_effect=AssertionError('no upload')):
                    voice._wait_for_interrupt(object(), threading.Event(), callback)
                callback.assert_called_once_with('stop', True)
                self.assertEqual(stream.read.call_count, 3)
                stream.__exit__.assert_called_once()
                busy.clear()

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

    def test_cloud_failure_never_substitutes_local_guess_or_another_provider(self):
        from unittest.mock import patch
        from audio import local_whisper
        with patch.dict(os.environ, {'GROQ_API_KEY': 'fake-test-key'}), \
             patch.object(voice, '_transcribe_groq', side_effect=TimeoutError()), \
             patch.object(local_whisper, 'transcribe') as local, \
             patch('vosk.KaldiRecognizer') as legacy:
            with self.assertRaisesRegex(RuntimeError, 'No other audio provider'):
                voice.transcribe(b'fake wav', offline_required=False)
            local.assert_not_called()
            legacy.assert_not_called()

    def test_empty_cloud_result_is_rejected(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {'GROQ_API_KEY': 'fake-test-key'}), \
             patch.object(voice, '_transcribe_groq', return_value=''):
            with self.assertRaises(voice.RecognitionUncertain):
                voice.transcribe(b'fake wav', offline_required=False)


if __name__ == "__main__":
    unittest.main()

