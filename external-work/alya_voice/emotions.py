"""Emotion table, explicit tags, cue-based inference and delivery maths.

The table in ../config/emotions.json is the source of truth. Inference is
deliberately simple (cue words + punctuation bias + persistence in the
director); it is a delivery heuristic, not sentiment analysis, and it never
changes what she says.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config'

SINGLE_TAG_RE = re.compile(r'\[\s*(?:emotion\s*:\s*)?([a-z_]+)\s*\]|<([a-z_]+)>')


@dataclass(frozen=True)
class Emotion:
    name: str
    rate_pct: int
    pitch_hz: int
    pitch_range: float
    volume_pct: int
    pause_scale: float
    breath: float
    humanize_cents: float
    contour: str
    description: str = ''
    cues: dict = None


@dataclass(frozen=True)
class Delivery:
    """Exactly what one engine is asked to do for one span of speech."""

    rate_pct: int
    pitch_hz: int
    volume_pct: int
    pause_scale: float
    breath: float
    humanize_cents: float
    contour: str
    pitch_range: float
    emotion: str = 'neutral'


def _clamp(value, low, high):
    return max(low, min(high, value))


def _cue_present(haystack, cue):
    cue = cue.strip().lower()
    if not cue:
        return False
    if ' ' in cue:
        return cue in haystack
    return re.search(r'(?<!\w)' + re.escape(cue) + r'(?!\w)', haystack) is not None


class EmotionTable:
    def __init__(self, path=None):
        source = Path(path) if path else CONFIG_DIR / 'emotions.json'
        data = json.loads(Path(source).read_text(encoding='utf-8'))
        self.source = str(source)
        self._by_name = {}
        for name, row in data['emotions'].items():
            fields = dict(row)
            cues = fields.pop('cues', {'en': [], 'ta': []})
            self._by_name[name] = Emotion(name=name, cues=cues, **fields)
        self.aliases = {str(k).lower(): str(v) for k, v in data.get('aliases', {}).items()}
        self.punctuation_bias = data.get('punctuation_bias', {})
        self.default = data.get('default', 'neutral')
        self.get(self.default)

    @property
    def names(self):
        return tuple(self._by_name)

    def get(self, name):
        key = str(name or '').strip().lower()
        key = self.aliases.get(key, key)
        if key not in self._by_name:
            raise KeyError('unknown emotion %r; known: %s' % (name, ', '.join(self.names)))
        return self._by_name[key]

    def strip_tags(self, text):
        """Return (explicit_emotion_or_None, cleaned_text). Unknown words stay put."""
        explicit = [None]

        def repl(match):
            word = (match.group(1) or match.group(2) or '').lower()
            candidate = self.aliases.get(word, word)
            if candidate in self._by_name and explicit[0] is None:
                explicit[0] = candidate
                return ' '
            return match.group(0)

        # Strip first, then read the captured tag: building the tuple the other way
        # round reads explicit[0] before sub() has mutated it, which silently drops
        # every explicit [emotion:...] / <...> tag.
        cleaned = SINGLE_TAG_RE.sub(repl, text)
        return explicit[0], cleaned

    def score(self, text, name):
        emotion = self.get(name)
        low = str(text).lower()
        total = 0.0
        for cue in list(emotion.cues.get('en', [])) + list(emotion.cues.get('ta', [])):
            if _cue_present(low, cue):
                total += 1.0
        for mark, weights in self.punctuation_bias.items():
            if mark in text:
                total += float(weights.get(emotion.name, 0))
        return total

    def infer(self, text):
        """(best_emotion, score). Falls back to the table default at score 0."""
        best, best_score = None, 0.0
        for name in self.names:
            value = self.score(text, name)
            if value > best_score:
                best, best_score = name, value
        return (best or self.default), best_score


def deliver(emotion, style, limits):
    """Combine an emotion with a style vector and clamp to the engine-safe range."""
    rate = int(round(getattr(style, 'rate_offset_pct', 0.0) +
                     emotion.rate_pct * getattr(style, 'rate_scale', 1.0)))
    pitch = int(round(emotion.pitch_hz * getattr(style, 'pitch_scale', 1.0)))
    volume = int(round(emotion.volume_pct * getattr(style, 'volume_scale', 1.0)))
    rate_limits = limits.get('rate_pct', (-40, 40))
    pitch_limits = limits.get('pitch_hz', (-35, 35))
    volume_limits = limits.get('volume_pct', (-30, 15))
    return Delivery(
        rate_pct=_clamp(rate, *rate_limits),
        pitch_hz=_clamp(pitch, *pitch_limits),
        volume_pct=_clamp(volume, *volume_limits),
        pause_scale=float(getattr(style, 'pause_scale', 1.0)) * emotion.pause_scale,
        breath=_clamp(emotion.breath * getattr(style, 'breath_scale', 1.0), 0.0, 1.0),
        humanize_cents=emotion.humanize_cents * getattr(style, 'humanize_scale', 1.0),
        contour=emotion.contour,
        pitch_range=emotion.pitch_range,
        emotion=emotion.name,
    )


def hz_to_semitones(hz, base_f0_hz):
    """Convert an absolute Hz offset into semitones for the DSP pitch shifter."""
    if hz == 0:
        return 0.0
    target = max(40.0, float(base_f0_hz) + float(hz))
    return 12.0 * math.log2(target / float(base_f0_hz))


# The owner's `lya-voice` engine (lya-external-work/lya-voice) exposed ten "moods".
# They were kept as a compatibility vocabulary: one name here always resolves to
# the same emotion plus the same delivery style in this engine, so scripts and
# habits from that engine keep working without a second code path.
MOOD_PRESETS = {
    'warm': ('warm', 'everyday'),
    'happy': ('cheerful', 'joyful'),
    'excited': ('excited', 'hype'),
    'caring': ('sympathetic', 'storyteller'),
    'calm': ('calm', 'night'),
    'shy': ('shy', 'whisper'),
    'teasing': ('playful', 'joyful'),
    'serious': ('serious', 'hacker'),
    'sad': ('sad', 'storyteller'),
    'whisper': ('gentle', 'whisper'),
}


def resolve_mood(name):
    """(emotion, style) for a mood name. Raises KeyError with the valid list."""
    key = str(name or '').strip().lower()
    if key not in MOOD_PRESETS:
        raise KeyError('unknown mood %r; known: %s' % (name, ', '.join(sorted(MOOD_PRESETS))))
    return MOOD_PRESETS[key]
