"""Normalisation: turn written text into what a person would actually say.

Handles markdown, code, URLs, emoji, numbers, decimals, percentages, currency,
times, ISO dates, ordinals and common units in English and Tamil.

Known limitation (owner listening QA required): Tamil number words are built
from a rule table and are not reviewed by a native speaker. Long compound
Tamil numerals may sound slightly formal or stilted.
"""
import re

TAMIL_RANGE = (0x0B80, 0x0BFF)

_EN_ONES = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
            'seventeen', 'eighteen', 'nineteen')
_EN_TENS = ('', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety')
_EN_SCALE = ((10 ** 12, 'trillion'), (10 ** 9, 'billion'), (10 ** 6, 'million'), (1000, 'thousand'))
_EN_ORD = {'one': 'first', 'two': 'second', 'three': 'third', 'four': 'fourth', 'five': 'fifth',
           'six': 'sixth', 'seven': 'seventh', 'eight': 'eighth', 'nine': 'ninth', 'ten': 'tenth',
           'eleven': 'eleventh', 'twelve': 'twelfth'}

_TA_0_9 = ('பூஜ்யம்', 'ஒன்று', 'இரண்டு', 'மூன்று', 'நான்கு', 'ஐந்து', 'ஆறு', 'ஏழு', 'எட்டு', 'ஒன்பது')
_TA_10_19 = ('பத்து', 'பதினொன்று', 'பன்னிரண்டு', 'பதின்மூன்று', 'பதினான்கு', 'பதினைந்து',
             'பதினாறு', 'பதினேழு', 'பதினெட்டு', 'பத்தொன்பது')
_TA_TENS = ('', '', 'இருபது', 'முப்பது', 'நாற்பது', 'ஐம்பது', 'அறுபது', 'எழுபது', 'எண்பது', 'தொண்ணூறு')
_TA_TENS_JOIN = ('', '', 'இருபத்து', 'முப்பத்து', 'நாற்பத்து', 'ஐம்பத்து', 'அறுபத்து', 'எழுபத்து',
                 'எண்பத்து', 'தொண்ணூற்று')
_TA_HUNDREDS = ('', 'நூறு', 'இருநூறு', 'முந்நூறு', 'நானூறு', 'ஐந்நூறு', 'அறுநூறு', 'எழுநூறு',
                'எண்ணூறு', 'தொள்ளாயிரம்')
_TA_MONTHS = ('ஜனவரி', 'பிப்ரவரி', 'மார்ச்', 'ஏப்ரல்', 'மே', 'ஜூன்', 'ஜூலை', 'ஆகஸ்ட்',
              'செப்டம்பர்', 'அக்டோபர்', 'நவம்பர்', 'டிசம்பர்')
_EN_MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
              'september', 'october', 'november', 'december')

_PERCENT = {'en': 'percent', 'ta': 'சதவீதம்'}
_ORDINAL_SUFFIX = {'en': '', 'ta': 'வது'}
_UNITS = {
    'km': {'en': 'kilometres', 'ta': 'கிலோமீட்டர்'}, 'kg': {'en': 'kilograms', 'ta': 'கிலோ'},
    'cm': {'en': 'centimetres', 'ta': 'சென்டிமீட்டர்'}, 'mm': {'en': 'millimetres', 'ta': 'மில்லிமீட்டர்'},
    'ms': {'en': 'milliseconds', 'ta': 'மில்லி விநாடி'}, 'gb': {'en': 'gigabytes', 'ta': 'ஜிகாபைட்'},
    'mb': {'en': 'megabytes', 'ta': 'மெகாபைட்'}, 'kb': {'en': 'kilobytes', 'ta': 'கிலோபைட்'},
    'hz': {'en': 'hertz', 'ta': 'ஹெர்ட்ஸ்'}, '°c': {'en': 'degrees celsius', 'ta': 'டிகிரி'},
    'rs': {'en': 'rupees', 'ta': 'ரூபாய்'},
}
_CURRENCY = {'₹': {'en': 'rupees', 'ta': 'ரூபாய்'}, '$': {'en': 'dollars', 'ta': 'டாலர்'},
             '€': {'en': 'euros', 'ta': 'யூரோ'}, '£': {'en': 'pounds', 'ta': 'பவுண்ட்'}}
_ABBREV = {'mr.': 'mister', 'mrs.': 'missus', 'dr.': 'doctor', 'prof.': 'professor',
           'vs.': 'versus', 'approx.': 'approximately', 'e.g.': 'for example',
           'i.e.': 'that is', 'etc.': 'et cetera', 'no.': 'number', 'fig.': 'figure'}


def is_tamil(text):
    return any(TAMIL_RANGE[0] <= ord(c) <= TAMIL_RANGE[1] for c in text)


def detect_language(text, default='en'):
    """Tamil if any Tamil codepoint is present, otherwise the caller's default."""
    return 'ta' if is_tamil(text) else default


def number_to_words_en(value):
    n = int(value)
    if n < 0:
        return 'minus ' + number_to_words_en(-n)
    if n < 20:
        return _EN_ONES[n]
    if n < 100:
        return _EN_TENS[n // 10] + (' ' + _EN_ONES[n % 10] if n % 10 else '')
    if n < 1000:
        return _EN_ONES[n // 100] + ' hundred' + (' ' + number_to_words_en(n % 100) if n % 100 else '')
    for size, name in _EN_SCALE:
        if n >= size:
            head, tail = divmod(n, size)
            return number_to_words_en(head) + ' ' + name + (' ' + number_to_words_en(tail) if tail else '')
    return _EN_ONES[0]


def number_to_words_ta(value):
    n = int(value)
    if n < 0:
        return 'மைனஸ் ' + number_to_words_ta(-n)
    if n < 10:
        return _TA_0_9[n]
    if n < 20:
        return _TA_10_19[n - 10]
    if n < 100:
        tens, rest = divmod(n, 10)
        return _TA_TENS_JOIN[tens] if not rest else _TA_TENS_JOIN[tens] + ' ' + _TA_0_9[rest]
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        head = _TA_HUNDREDS[hundreds]
        return head if not rest else head + ' ' + number_to_words_ta(rest)
    if n < 100000:
        thousands, rest = divmod(n, 1000)
        head = _TA_0_9[thousands] + ' ஆயிரம்' if thousands < 10 else number_to_words_ta(thousands) + ' ஆயிரம்'
        return head if not rest else head + ' ' + number_to_words_ta(rest)
    if n < 10000000:
        lakhs, rest = divmod(n, 100000)
        head = number_to_words_ta(lakhs) + ' இலட்சம்'
        return head if not rest else head + ' ' + number_to_words_ta(rest)
    crores, rest = divmod(n, 10000000)
    head = number_to_words_ta(crores) + ' கோடி'
    return head if not rest else head + ' ' + number_to_words_ta(rest)


def number_to_words(value, lang='en'):
    return number_to_words_ta(value) if lang == 'ta' else number_to_words_en(value)


def ordinal_to_words(value, lang='en'):
    words = number_to_words(value, lang)
    if lang == 'ta':
        return words + _ORDINAL_SUFFIX['ta']
    tail = words.rsplit(' ', 1)[-1]
    return words[:-len(tail)] + _EN_ORD.get(tail, tail + 'th')



_CODE_RE = re.compile(r'```.*?(?:```|$)|`[^`]*`', re.S)
_URL_RE = re.compile(r'\b(?:https?://|www\.)\S+|\b[\w.+-]+@[\w-]+\.[\w.]+')
_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_MD_MARK_RE = re.compile(r'(^|\n)\s{0,3}(?:#{1,6}|[-*+]|\d+\.|>)\s+')
_EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]+')
_CURRENCY_RE = re.compile(r'([\u20b9$\u20ac\u00a3])\s?(\d[\d,]*(?:\.\d+)?)')
_UNIT_RE = re.compile(r'(\d[\d,]*(?:\.\d+)?)\s?(km|kg|cm|mm|ms|gb|mb|kb|hz|\u00b0c|rs)\b', re.I)
_PERCENT_RE = re.compile(r'(\d[\d,]*(?:\.\d+)?)\s?%')
_TIME_RE = re.compile(r'\b(\d{1,2}):(\d{2})(?:\s?([ap])\.?m\.?)?\b', re.I)
_ISO_DATE_RE = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b')
_SLASH_DATE_RE = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b')
_ORDINAL_RE = re.compile(r'\b(\d+)(st|nd|rd|th)\b', re.I)
_GROUPED_DIGITS_RE = re.compile(r'\b(?:\d{3,4}[ -]){2,}\d{3,4}\b')
_ABBREV_RE = re.compile(r'\b(' + '|'.join(re.escape(k) for k in _ABBREV) + ')', re.I)
_NUMBER_RE = re.compile(r'\b(\d[\d,]*)(?:\.(\d+))?\b')


def _digit_by_digit(run, lang):
    return ' '.join(number_to_words(int(d), lang) for d in run)


def _say_number(run, lang):
    clean = run.replace(',', '')
    if len(clean) > 6:
        return _digit_by_digit(clean, lang)
    return number_to_words(int(clean), lang)


def _replace_numbers(text, lang):
    def repl(match):
        whole, decimals = match.group(1), match.group(2)
        head = _say_number(whole, lang)
        if decimals is None:
            return head
        sep = ' \u0baa\u0bc1\u0bb3\u0bcd\u0bb3\u0bbf ' if lang == 'ta' else ' point '
        return head + sep + _digit_by_digit(decimals, lang)

    return _NUMBER_RE.sub(repl, text)


def strip_markdown(text):
    """Remove structure that must not be read aloud."""
    text = _MD_LINK_RE.sub(r'\1', text)
    text = _MD_MARK_RE.sub(r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*|__(.+?)__', lambda m: m.group(1) or m.group(2), text, flags=re.S)
    text = text.replace('|', ', ')
    return text


def _month(index, lang):
    months = _TA_MONTHS if lang == 'ta' else _EN_MONTHS
    return months[max(0, min(11, index - 1))]


def spoken_form(text, lang='en'):
    """Rewrite `text` into speakable form. Word order survives; nothing is invented."""
    text = str(text)
    code_note = ' \u0b95\u0bc1\u0bb1\u0bbf\u0baf\u0bc0\u0b9f\u0bc1 \u0ba4\u0bbf\u0bb0\u0bc8\u0baf\u0bbf\u0bb2\u0bcd ' if lang == 'ta' else ' code is on screen '
    link_note = ' \u0b87\u0ba3\u0bc8\u0baa\u0bcd\u0baa\u0bc1 \u0ba4\u0bbf\u0bb0\u0bc8\u0baf\u0bbf\u0bb2\u0bcd ' if lang == 'ta' else ' link on screen '
    text = _CODE_RE.sub(code_note, text)
    text = _URL_RE.sub(link_note, text)
    text = strip_markdown(text)
    text = _EMOJI_RE.sub(' ', text)
    text = _ISO_DATE_RE.sub(lambda m: f'{int(m.group(3))} {_month(int(m.group(2)), lang)} {m.group(1)}', text)
    text = _SLASH_DATE_RE.sub(lambda m: f'{int(m.group(1))} {_month(int(m.group(2)), lang)} {m.group(3)}', text)
    text = _TIME_RE.sub(lambda m: f'{m.group(1)} {m.group(2)}' + (f' {m.group(3)} m' if m.group(3) else ''), text)
    text = _CURRENCY_RE.sub(lambda m: f'{m.group(2)} {_CURRENCY[m.group(1)][lang]}', text)
    text = _UNIT_RE.sub(lambda m: f'{m.group(1)} {_UNITS[m.group(2).lower()][lang]}', text)
    text = _PERCENT_RE.sub(lambda m: f'{m.group(1)} {_PERCENT[lang]}', text)
    text = _ORDINAL_RE.sub(lambda m: ordinal_to_words(int(m.group(1)), lang), text)
    text = _GROUPED_DIGITS_RE.sub(lambda m: ' '.join(number_to_words(int(d), lang)
                                                    for d in re.findall(r'\d', m.group(0))), text)
    text = _replace_numbers(text, lang)
    text = _ABBREV_RE.sub(lambda m: _ABBREV[m.group(1).lower()], text)
    text = re.sub(r'\.{2,}|\u2026', ', ', text)
    text = re.sub(r'\s*[\u2014\u2013]\s*', ', ', text)
    return re.sub(r'\s+', ' ', text).strip()
