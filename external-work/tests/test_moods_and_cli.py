"""Owner mood vocabulary, delivery resolution and CLI wiring."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import cli
from alya_voice.emotions import MOOD_PRESETS, EmotionTable, resolve_mood
from alya_voice.persona import load_persona


class MoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.persona = load_persona()
        cls.table = EmotionTable()

    def test_every_mood_resolves_to_a_real_emotion_and_style(self):
        for name in MOOD_PRESETS:
            emotion, style = resolve_mood(name)
            self.assertEqual(self.table.get(emotion).name, emotion, name)
            self.persona.style(style)

    def test_owner_vocabulary_is_fully_covered(self):
        for name in ('warm', 'happy', 'excited', 'caring', 'calm', 'shy',
                     'teasing', 'serious', 'sad', 'whisper'):
            self.assertIn(name, MOOD_PRESETS)

    def test_case_insensitive_and_unknown(self):
        self.assertEqual(resolve_mood('WARM'), resolve_mood('warm'))
        with self.assertRaises(KeyError) as caught:
            resolve_mood('grumpy')
        self.assertIn('grumpy', str(caught.exception))


class DeliveryResolutionTests(unittest.TestCase):
    def test_mood_fills_in_for_emotion_and_style(self):
        emotion, style = cli.resolve_delivery(SimpleNamespace(mood='happy'))
        self.assertEqual((emotion, style), ('cheerful', 'joyful'))

    def test_explicit_emotion_wins_over_mood(self):
        emotion, style = cli.resolve_delivery(
            SimpleNamespace(mood='happy', emotion='serious'))
        self.assertEqual(emotion, 'serious')
        self.assertEqual(style, 'joyful')

    def test_no_mood_means_no_change(self):
        self.assertEqual(cli.resolve_delivery(SimpleNamespace(emotion='warm', style='night')),
                         ('warm', 'night'))


class CliTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows process counter')
    def test_peak_memory_counter_is_not_zero(self):
        self.assertGreater(cli.peak_working_set_mb(), 1.0)

    def test_parser_accepts_mood_and_realism(self):
        args = cli.build_parser().parse_args(['say', 'hello', '--mood', 'warm',
                                              '--realism', 'phone', '--personality', 'soft'])
        self.assertEqual(args.mood, 'warm')
        self.assertEqual(args.realism, 'phone')
        self.assertEqual(args.personality, 'soft')

    def test_default_realism_is_off_for_realtime_speech(self):
        args = cli.build_parser().parse_args(['say', 'hello'])
        self.assertEqual(args.realism, 'none')

    def test_bad_realism_mode_is_rejected(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(['say', 'hello', '--realism', 'teleport'])

    def test_plan_command_runs_with_a_mood(self):
        self.assertEqual(cli.main(['plan', 'The backup finished.', '--mood', 'serious']), 0)

    def test_unknown_mood_is_a_clear_error(self):
        with self.assertRaises(KeyError):
            cli.main(['plan', 'hello', '--mood', 'grumpy'])

    def test_doctor_reports_every_engine(self):
        self.assertEqual(cli.main(['doctor']), 0)


if __name__ == '__main__':
    unittest.main()
