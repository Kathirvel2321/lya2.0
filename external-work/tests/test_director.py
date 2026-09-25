import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import emotions, normalize
from alya_voice.director import Director, pause_after, split_sentences
from alya_voice.persona import load_persona

WORDS = re.compile(r'[\w\u0b80-\u0bff]+')


def words(text):
    return [w.lower() for w in WORDS.findall(text)]


class DirectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.persona = load_persona()
        cls.table = emotions.EmotionTable()
        cls.director = Director(cls.persona, cls.table)

    def build(self, text, **kwargs):
        kwargs.setdefault('allow_interjections', False)
        kwargs.setdefault('seed', 7)
        return self.director.build(text, **kwargs)

    def test_same_seed_same_plan(self):
        text = 'The backup finished, and all files are safe. Do you want the report? '
        self.assertEqual(self.build(text).to_dict(), self.build(text).to_dict())

    def test_no_words_are_lost_or_invented(self):
        text = ('Good evening. Your backup finished 4 minutes ago, '
                'so nothing needs your attention right now.')
        plan = self.build(text)
        self.assertEqual(words(' '.join(s.text for s in plan.spans)), words(plan.text))

    def test_number_commas_survive_clause_splitting(self):
        plan = self.build('We saved 1,204 files, and 3 folders were skipped.')
        joined = ' '.join(s.text for s in plan.spans)
        self.assertIn('one thousand two hundred four', joined)
        self.assertNotIn('one, two', joined)

    def test_short_sentence_keeps_commas_in_one_audio_span(self):
        text = 'Hey, I am here, and your work is ready.'
        plan = self.build(text)
        self.assertEqual(len(plan.spans), 1)
        self.assertEqual(plan.spans[0].source, text)

    def test_explicit_emotion_applies_to_every_span(self):
        plan = self.build('First part. Second part. Third part.', emotion='serious')
        self.assertTrue(all(span.emotion == 'serious' for span in plan.spans))

    def test_emotion_tag_in_text_wins(self):
        plan = self.build('[playful] Wow, that is unexpected! Really. I see.')
        self.assertEqual(plan.emotion, 'playful')
        self.assertEqual(plan.spans[0].emotion, 'playful')

    def test_emotion_persists_to_the_next_sentence(self):
        plan = self.build('That is amazing! I cannot believe it. It works.')
        self.assertEqual(plan.spans[0].emotion, 'excited')
        self.assertEqual(plan.spans[-1].emotion, 'excited')

    def test_question_lifts_the_last_clause(self):
        base = emotions.deliver(self.table.get('curious'), self.persona.style('everyday'),
                                self.persona.limits)
        plan = self.build('Is the backup finished?', emotion='curious')
        self.assertEqual(plan.spans[-1].pitch_hz, base.pitch_hz + 4)

    def test_statement_gets_a_final_cadence(self):
        base = emotions.deliver(self.table.get('warm'), self.persona.style('everyday'),
                                self.persona.limits)
        plan = self.build('The backup is finished.', emotion='warm')
        self.assertEqual(plan.spans[-1].rate_pct, base.rate_pct - 2)

    def test_style_changes_beat_length(self):
        text = 'First, the backup finished. Then, I checked the logs. Everything is fine.'
        brisk = self.build(text, style='hacker')
        slow = self.build(text, style='storyteller')
        self.assertLess(sum(s.pause_after_ms for s in brisk.spans),
                        sum(s.pause_after_ms for s in slow.spans))

    def test_pauses_stay_inside_limits(self):
        for span in self.build('A. B, C; D: E? F!').spans:
            self.assertTrue(40 <= span.pause_after_ms <= 900, span.pause_after_ms)

    def test_interjections_only_when_allowed(self):
        text = 'The backup finished a few minutes ago, so nothing needs your attention right now.'
        quiet = self.build(text, allow_interjections=False)
        chattier = self.director.build(text, seed=1, allow_interjections=True)
        palette = set(self.persona.interjections['en'])
        self.assertFalse(any(s.text.split(',')[0] in palette for s in quiet.spans))
        self.assertTrue(any(s.text.split(',')[0] in palette for s in chattier.spans))

    def test_language_routing(self):
        self.assertTrue(all(s.language == 'ta' for s in self.build('வணக்கம், நலம்.').spans))
        self.assertTrue(all(s.language == 'en' for s in self.build('Hello there.').spans))
        mixed = self.build('Hello. வணக்கம்.')
        self.assertEqual([s.language for s in mixed.spans], ['en', 'ta'])

    def test_long_sentence_is_split_into_bounded_spans(self):
        plan = self.build('word ' * 120)
        self.assertTrue(plan.spans)
        self.assertTrue(all(len(s.text) <= self.persona.max_span_chars for s in plan.spans))

    def test_empty_text_makes_an_empty_plan(self):
        plan = self.build('   ')
        self.assertEqual(plan.spans, ())
        self.assertEqual(plan.text, '')

    def test_unsupported_language_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build('hello', language='fr')

    def test_lines_and_dict_are_serialisable(self):
        import json
        plan = self.build('Hello there, friend.')
        self.assertEqual(len(plan.lines()), len(plan.spans))
        json.dumps(plan.to_dict())

    def test_blank_sentences_do_not_crash(self):
        self.assertEqual(split_sentences('...'), [])
        self.assertEqual(pause_after('x', True, 1.0, False), 320)


if __name__ == '__main__':
    unittest.main()
