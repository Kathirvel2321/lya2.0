"""Isolated speech transport checks; no speaker or network access."""
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QCoreApplication, QProcess
from desktop.setup_speech import SetupSpeech, _load_voice

app = QCoreApplication.instance() or QCoreApplication([])


class SpeechTests(unittest.TestCase):
    def test_desktop_uses_native_models_for_english_and_tamil(self):
        voice = _load_voice()
        try:
            piper = voice._engine('offline_piper')
            self.assertEqual(piper._model_for('en'), 'en_US-ljspeech-medium')
            self.assertEqual(piper._model_for('ta'), 'ta_IN-rasa_female-medium')
        finally:
            voice.close()

    def setUp(self):
        self.voice = SetupSpeech()
        self.voice.process = Mock()
        self.voice.process.state.return_value = QProcess.ProcessState.NotRunning

    def tearDown(self):
        self.voice.stop()

    def test_text_uses_stdin_and_no_shell(self):
        self.voice.say('Hello <test>')
        args = self.voice.process.start.call_args.args
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(args[1][0].endswith('setup_speech.py'))
        self.assertEqual(args[1][1], '--warm-piper')
        self.voice._started()
        written = self.voice.process.write.call_args.args[0]
        self.assertIn(b'Hello <test>', written)
        self.assertTrue(written.endswith(b'\n'))
        self.voice.process.closeWriteChannel.assert_not_called()

    def test_economy_speech_skips_piper_warmup(self):
        self.voice.say('Hello', engine='offline_sapi')
        self.assertEqual(len(self.voice.process.start.call_args.args[1]), 1)

    def test_caption_includes_audio_duration(self):
        caption = Mock()
        self.voice.caption.connect(caption)
        self.voice.busy = True
        self.voice.cancelled = False
        self.voice.request = 3
        self.voice.process.readAllStandardOutput.return_value = (
            b'{"id":3,"kind":"caption","text":"Hello there","duration_ms":720}\n')
        self.voice._read()
        caption.assert_called_once_with('Hello there', 720)

    def test_close_clears_queued_replacement(self):
        self.voice.process.state.return_value = QProcess.ProcessState.Running
        self.voice.say('Old prompt')
        self.voice.say('New prompt')
        self.voice.stop()
        self.voice._finished(1, QProcess.ExitStatus.CrashExit)
        self.voice.process.start.assert_not_called()
        self.assertIsNone(self.voice.pending)

    def test_stop_completes_active_caption(self):
        completed = Mock()
        self.voice.completed.connect(completed)
        self.voice.busy = True
        self.voice.stop()
        completed.assert_called_once()

    def test_navigation_preserves_idle_worker_but_cancels_active_speech(self):
        self.voice.process.state.return_value = QProcess.ProcessState.Running
        self.voice.stop(keep_warm=True)
        self.voice.process.kill.assert_not_called()
        self.voice.say('Next answer')
        self.voice.process.start.assert_not_called()
        self.voice.process.write.assert_called_once()
        self.voice.stop(keep_warm=True)
        self.voice.process.kill.assert_called_once()
        self.assertFalse(self.voice.busy)

    def test_navigation_preserves_prewarm_but_shutdown_stops_it(self):
        self.voice.prewarm()
        self.voice.process.state.return_value = QProcess.ProcessState.Starting
        self.voice.stop(keep_warm=True)
        self.voice.process.kill.assert_not_called()
        self.assertTrue(self.voice.warming)
        self.voice.stop()
        self.voice.process.kill.assert_called_once()

    def test_failure_and_timeout_stop_without_retry(self):
        failed = Mock()
        self.voice.unavailable.connect(failed)
        self.voice.say('Hello')
        self.voice._error(QProcess.ProcessError.FailedToStart)
        self.assertIsNone(self.voice.pending)
        self.assertFalse(self.voice.timeout.isActive())
        failed.assert_called_once()
        self.voice._timed_out()
        self.assertFalse(self.voice.timeout.isActive())


if __name__ == '__main__':
    unittest.main()
