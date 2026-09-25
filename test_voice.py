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

    def tearDown(self):
        voice.set_quiet(False)
        voice._SPEAKING.clear()

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
            ("lya", "help"),
            ("hey liya", "help"),
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
        self.assertEqual(received, ["help"])

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

