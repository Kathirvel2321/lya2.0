import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import emotions, persona


class EmotionTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = emotions.EmotionTable()

    def test_table_is_loaded(self):
        self.assertGreaterEqual(len(self.table.names), 20)
        self.assertIn('cheerful', self.table.names)
        self.assertIn('warm', self.table.names)

    def test_aliases_and_unknown_names(self):
        self.assertEqual(self.table.get('happy').name, 'cheerful')
        self.assertEqual(self.table.get('SCARED').name, 'worried')
        with self.assertRaises(KeyError):
            self.table.get('no-such-emotion')

    def test_explicit_tags_are_extracted(self):
        name, cleaned = self.table.strip_tags('[emotion:cheerful] The backup finished.')
        self.assertEqual(name, 'cheerful')
        self.assertNotIn('[emotion:cheerful]', cleaned)
        name, cleaned = self.table.strip_tags('<playful> okay then')
        self.assertEqual(name, 'playful')
        name, cleaned = self.table.strip_tags('[note] this is not an emotion')
        self.assertIsNone(name)
        self.assertIn('[note]', cleaned)

    def test_cue_inference_english(self):
        emotion, score = self.table.infer("That's amazing! I can't believe it.")
        self.assertEqual(emotion, 'excited')
        self.assertGreater(score, 0)
        self.assertEqual(self.table.infer('The file is here.')[0], 'warm')

    def test_cue_inference_tamil(self):
        self.assertEqual(self.table.infer('எனக்கு ரொம்ப கவலை')[0], 'worried')
        self.assertEqual(self.table.infer('சூப்பர், வேலை முடிந்தது')[0], 'cheerful')

    def test_word_boundaries_do_not_match_inside_words(self):
        self.assertNotEqual(self.table.infer('the northern route is open')[0], 'firm')


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = emotions.EmotionTable()
        cls.persona = persona.load_persona()

    def test_style_scales_emotion(self):
        quiet = emotions.deliver(self.table.get('excited'), self.persona.style('everyday'),
                                 self.persona.limits)
        loud = emotions.deliver(self.table.get('excited'), self.persona.style('hype'),
                                self.persona.limits)
        self.assertGreater(loud.pitch_hz, quiet.pitch_hz)

    def test_style_rate_offset_really_slows_neutral_speech(self):
        delivery = emotions.deliver(self.table.get('neutral'), self.persona.style('everyday'),
                                    self.persona.limits)
        self.assertEqual(delivery.rate_pct, -8)

    def test_limits_are_never_exceeded(self):
        limits = {'rate_pct': (-5, 5), 'pitch_hz': (-3, 3), 'volume_pct': (-2, 2)}
        delivery = emotions.deliver(self.table.get('excited'), self.persona.style('hype'), limits)
        self.assertLessEqual(delivery.rate_pct, 5)
        self.assertGreaterEqual(delivery.rate_pct, -5)
        self.assertLessEqual(delivery.pitch_hz, 3)
        self.assertGreaterEqual(delivery.pitch_hz, -3)

    def test_real_table_stays_inside_engine_safe_ranges(self):
        for name in self.table.names:
            for style in self.persona.styles.values():
                delivery = emotions.deliver(self.table.get(name), style, self.persona.limits)
                self.assertTrue(-40 <= delivery.rate_pct <= 40, name)
                self.assertTrue(-35 <= delivery.pitch_hz <= 35, name)
                self.assertTrue(-30 <= delivery.volume_pct <= 15, name)
                self.assertTrue(0.0 <= delivery.breath <= 1.0, name)

    def test_hz_to_semitones(self):
        self.assertEqual(emotions.hz_to_semitones(0, 200.0), 0.0)
        value = emotions.hz_to_semitones(12, 200.0)
        self.assertTrue(0.9 < value < 1.2, value)
        self.assertTrue(emotions.hz_to_semitones(-12, 200.0) < 0)


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.persona = persona.load_persona()

    def test_identity(self):
        self.assertEqual(self.persona.name, 'Alya')
        self.assertEqual(self.persona.age, 21)
        self.assertEqual(self.persona.gender, 'female')
        self.assertEqual(self.persona.languages, ('en', 'ta'))
        self.assertIn('LYA', self.persona.aliases)

    def test_one_voice_for_both_languages(self):
        unified_en = self.persona.voice('cloud_edge', 'en', 'unified')
        self.assertEqual(unified_en, self.persona.voice('cloud_edge', 'ta', 'unified'))
        self.assertIn('Multilingual', unified_en)
        self.assertEqual(self.persona.voice('piper', 'en', 'unified'),
                         self.persona.voice('piper', 'ta', 'unified'))

    def test_per_language_voice_available_when_asked(self):
        self.assertEqual(self.persona.voice('piper', 'en', 'per_language'), 'en_US-ljspeech-medium')
        self.assertEqual(self.persona.voice('cloud_edge', 'ta', 'per_language'), 'ta-IN-PallaviNeural')

    def test_styles_and_unknown_style(self):
        self.assertIn('hacker', self.persona.style_names)
        self.assertIn('joyful', self.persona.style_names)
        self.assertEqual(self.persona.style('HACKER').rate_offset_pct, -4)
        with self.assertRaises(KeyError):
            self.persona.style('nope')

    def test_interjection_is_skipped_when_probability_not_met(self):
        class Rng:
            @staticmethod
            def random():
                return 0.99

            @staticmethod
            def choice(seq):
                return seq[0]

        self.assertIsNone(self.persona.pick_interjection('en', Rng()))

    def test_unknown_keys_are_rejected(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'persona.json'
            payload = json.loads(Path(self.persona.source).read_text(encoding='utf-8'))
            payload['surprise_key'] = True
            path.write_text(json.dumps(payload), encoding='utf-8')
            with self.assertRaises(KeyError):
                persona.load_persona(path)


if __name__ == '__main__':
    unittest.main()
