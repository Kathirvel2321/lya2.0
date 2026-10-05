"""Synthetic local comparison checks; no hardware, model or network calls."""
import unittest
from unittest.mock import patch

from audio import voice, local_whistle, local_whisper
from test_hearing_pilots import wav
from tools import check_local_hearing as check


class LocalComparisonTests(unittest.TestCase):
    def test_same_complete_audio_local_only_and_optional_heavy_model_not_loaded(self):
        data = wav()
        output = []
        with patch.object(voice, 'transcribe', return_value='Synthetic local text') as current, patch.object(local_whistle, 'decode', return_value={'text': 'Synthetic Whistle text'}) as tiny, patch.object(local_whisper, 'transcribe', side_effect=AssertionError('unexpected large model')):
            check.compare(data, output=output.append)
        current.assert_called_once_with(data, offline_required=True)
        tiny.assert_called_once_with(data)
        self.assertTrue(any('Synthetic local text' in text for text in output))

    def test_uncertain_words_never_accepted_and_other_local_result_visible(self):
        output = []
        with patch.object(voice, 'transcribe', side_effect=voice.RecognitionUncertain('uncertain', 'synthetic candidate')), patch.object(local_whistle, 'decode', return_value={'text': 'Local result'}):
            check.compare(wav(), output=output.append)
        self.assertTrue(any('UNCERTAIN' in text for text in output))
        self.assertTrue(any('Local result' in text for text in output))

    def test_clipped_or_long_question_not_partially_decoded(self):
        with patch.object(voice, 'transcribe') as current, patch.object(local_whistle, 'decode') as tiny:
            with self.assertRaises(voice.RecognitionUncertain):
                check.compare(wav(31))
        current.assert_not_called()
        tiny.assert_not_called()


if __name__ == '__main__':
    unittest.main()
