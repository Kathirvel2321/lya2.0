"""No microphone, network, model download or private storage."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from audio import local_whisper, voice


def segment(text, **changes):
    return SimpleNamespace(text=text, avg_logprob=-0.2, compression_ratio=1.1,
                           no_speech_prob=0.05, **changes)


class LocalWhisperTests(unittest.TestCase):
    def test_offline_routing_uses_whisper_and_never_falls_back_after_uncertainty(self):
        with patch.dict(os.environ, {'LYA_COMMAND_ASR': 'whisper', 'GROQ_API_KEY': 'fake-never-used'}), \
             patch.object(local_whisper, 'available', return_value=True), \
             patch.object(local_whisper, 'transcribe', side_effect=voice.RecognitionUncertain('Repeat')), \
             patch.object(voice, '_transcribe_groq') as remote, \
             patch('vosk.KaldiRecognizer') as legacy:
            with self.assertRaises(voice.RecognitionUncertain):
                voice.transcribe(b'fake wav', offline_required=True)
            remote.assert_not_called()
            legacy.assert_not_called()

    def test_preserves_all_clauses_without_prompting_expected_words(self):
        model = Mock()
        model.transcribe.return_value = (iter([segment('Please tell me'), segment('the current time.')]), None)
        with patch.object(local_whisper, 'load', return_value=model):
            self.assertEqual(local_whisper.transcribe(b'fake wav'), 'Please tell me the current time.')
        options = model.transcribe.call_args.kwargs
        self.assertEqual(options['language'], 'en')
        self.assertFalse(options['condition_on_previous_text'])
        self.assertNotIn('initial_prompt', options)
        self.assertNotIn('hotwords', options)

    def test_rejects_entire_question_when_one_clause_is_uncertain(self):
        for key, value in [('avg_logprob', -1.5), ('compression_ratio', 3.0), ('no_speech_prob', 0.8)]:
            first, second = segment('Reliable clause'), segment('Uncertain clause')
            setattr(second, key, value)
            model = Mock()
            model.transcribe.return_value = (iter([first, second]), None)
            with self.subTest(key=key), patch.object(local_whisper, 'load', return_value=model):
                with self.assertRaises(voice.RecognitionUncertain):
                    local_whisper.transcribe(b'fake wav')

    def test_rejects_silence(self):
        model = Mock()
        model.transcribe.return_value = (iter([]), None)
        with patch.object(local_whisper, 'load', return_value=model):
            with self.assertRaises(voice.RecognitionUncertain):
                local_whisper.transcribe(b'fake wav')

    def test_repeated_guess_is_rejected_even_with_high_model_confidence(self):
        model = Mock()
        model.transcribe.return_value = (iter([segment('The time is now. ' + 'No. ' * 8)]), None)
        with patch.object(local_whisper, 'load', return_value=model):
            with self.assertRaises(voice.RecognitionUncertain):
                local_whisper.transcribe(b'fake wav')

    def test_incomplete_model_never_calls_download_or_loader(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ, {'LYA_WHISPER_MODEL': folder}), \
             patch('faster_whisper.WhisperModel') as constructor:
            for name in local_whisper.FILES[:-1]:
                (Path(folder) / name).touch()
            self.assertFalse(local_whisper.available())
            with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                local_whisper.load(folder)
            constructor.assert_not_called()

    def test_complete_model_loads_local_cpu_once(self):
        local_whisper.load.cache_clear()
        with tempfile.TemporaryDirectory() as folder, patch('faster_whisper.WhisperModel') as constructor:
            for name in local_whisper.FILES:
                (Path(folder) / name).touch()
            local_whisper.load(folder)
            local_whisper.load(folder)
            constructor.assert_called_once_with(folder, device='cpu', compute_type='int8',
                                                 cpu_threads=4, num_workers=1, local_files_only=True)
        local_whisper.load.cache_clear()


if __name__ == '__main__':
    unittest.main()
