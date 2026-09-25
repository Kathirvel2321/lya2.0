import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alya_voice import normalize


class NumberWordsTests(unittest.TestCase):
    def test_english_numbers(self):
        cases = {0: 'zero', 15: 'fifteen', 42: 'forty two', 100: 'one hundred',
                 101: 'one hundred one', 1234: 'one thousand two hundred thirty four',
                 1000000: 'one million'}
        for value, expected in cases.items():
            self.assertEqual(normalize.number_to_words_en(value), expected)

    def test_tamil_numbers(self):
        self.assertEqual(normalize.number_to_words_ta(5), 'ஐந்து')
        self.assertEqual(normalize.number_to_words_ta(15), 'பதினைந்து')
        self.assertEqual(normalize.number_to_words_ta(21), 'இருபத்து ஒன்று')
        self.assertEqual(normalize.number_to_words_ta(105), 'நூறு ஐந்து')
        self.assertIn('ஆயிரம்', normalize.number_to_words_ta(2000))
        self.assertIn('இலட்சம்', normalize.number_to_words_ta(250000))
        self.assertIn('கோடி', normalize.number_to_words_ta(10000000))

    def test_ordinals(self):
        self.assertEqual(normalize.ordinal_to_words(21, 'en'), 'twenty first')
        self.assertEqual(normalize.ordinal_to_words(3, 'en'), 'third')
        self.assertEqual(normalize.ordinal_to_words(5, 'ta'), 'ஐந்துவது')

    def test_language_detection(self):
        self.assertEqual(normalize.detect_language('hello there'), 'en')
        self.assertEqual(normalize.detect_language('வணக்கம்'), 'ta')
        self.assertEqual(normalize.detect_language('hello', 'ta'), 'ta')


class SpokenFormTests(unittest.TestCase):
    def test_percent_currency_and_units(self):
        self.assertIn('twenty five percent', normalize.spoken_form('25% done'))
        self.assertIn('nine hundred fifty rupees', normalize.spoken_form('₹950'))
        self.assertIn('five kilometres', normalize.spoken_form('5km left'))
        self.assertIn('சதவீதம்', normalize.spoken_form('25%', 'ta'))

    def test_time_and_iso_date(self):
        self.assertIn('nine thirty', normalize.spoken_form('meeting at 9:30'))
        self.assertIn('twenty two september two thousand twenty six',
                      normalize.spoken_form('on 2026-09-22'))
        self.assertIn('செப்டம்பர்', normalize.spoken_form('2026-09-22', 'ta'))

    def test_grouped_digits_read_digit_by_digit(self):
        spoken = normalize.spoken_form('card 4111 1111 1111 1111')
        self.assertIn('four one one one', spoken)
        self.assertNotIn('four thousand one hundred eleven', spoken)

    def test_very_long_numbers_are_spelled_out(self):
        self.assertIn('one two three four five six seven', normalize.spoken_form('1234567'))

    def test_markdown_code_urls_and_emoji(self):
        spoken = normalize.spoken_form('**Bold** and `x=1` see https://example.com/a?b=1 🚀')
        self.assertIn('Bold', spoken)
        self.assertIn('code is on screen', spoken)
        self.assertIn('link on screen', spoken)
        self.assertNotIn('http', spoken)
        self.assertNotIn('🚀', spoken)

    def test_abbreviations_and_pauses(self):
        self.assertIn('et cetera', normalize.spoken_form('files, etc.'))
        self.assertIn('doctor', normalize.spoken_form('Dr. Rao called'))
        self.assertNotIn('...', normalize.spoken_form('well... maybe'))

    def test_tamil_keeps_word_order(self):
        original = 'வணக்கம், உங்கள் கோப்புகள் தயாராக உள்ளன.'
        spoken = normalize.spoken_form(original, 'ta')
        self.assertTrue(spoken.startswith('வணக்கம்'))
        self.assertIn('கோப்புகள்', spoken)

    def test_empty_and_whitespace(self):
        self.assertEqual(normalize.spoken_form('   '), '')
        self.assertEqual(normalize.spoken_form(''), '')


if __name__ == '__main__':
    unittest.main()
