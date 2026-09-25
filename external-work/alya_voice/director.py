"""Prosody director: text -> a plan of emotionally shaped spans.

One speaker. Emotion is chosen per sentence, then varied inside the sentence so
consecutive clauses are never identical. Nothing is added to the meaning: the
normaliser may expand "25%" into words, but no sentence, clause or fact is ever
invented.
"""
from __future__ import annotations

import dataclasses
import random
import re

from . import normalize
from .emotions import EmotionTable, deliver

SENTENCE_RE = re.compile(r'(?<=[.!?\u2026])\s+|\n+')
CLAUSE_RE = re.compile(r'(?<=[,;:])\s+')
_NUMBER_COMMA = '\x00'
_MARKER = re.compile(r'\s+')


@dataclasses.dataclass(frozen=True)
class Span:
    text: str
    source: str
    language: str
    emotion: str
    rate_pct: int
    pitch_hz: int
    volume_pct: int
    pause_after_ms: int
    breath_before: bool
    contour: str
    index: int
    humanize_cents: float = 0.0
    breath_amount: float = 0.0


@dataclasses.dataclass(frozen=True)
class Plan:
    persona: str
    style: str
    emotion: str
    language: str
    spans: tuple
    text: str

    def to_dict(self):
        return dataclasses.asdict(self)

    def lines(self):
        out = []
        for span in self.spans:
            out.append('%2d %-3s %-12s r%+3d p%+3d v%+3d pause %4dms %s%s' % (
                span.index, span.language, span.emotion, span.rate_pct, span.pitch_hz,
                span.volume_pct, span.pause_after_ms,
                'breath ' if span.breath_before else '', span.text))
        return out


def split_sentences(text):
    protected = re.sub(r'(?<=\d),(?=\d)', _NUMBER_COMMA, text)
    parts = [p.strip() for p in SENTENCE_RE.split(protected) if p.strip()]
    parts = [p for p in parts if re.search(r'\w', p)]  # drop punctuation-only tails
    return [p.replace(_NUMBER_COMMA, ',') for p in parts]


def split_clauses(sentence, max_chars):
    # Preserve sentence prosody instead of synthesizing every comma separately.
    if len(sentence) <= max_chars:
        return [sentence] if sentence.strip() else []
    protected = re.sub(r'(?<=\d),(?=\d)', _NUMBER_COMMA, sentence)
    clauses = [c.strip() for c in CLAUSE_RE.split(protected) if c.strip()]
    clauses = [c.replace(_NUMBER_COMMA, ',') for c in clauses]
    out = []
    for clause in clauses:
        while len(clause) > max_chars:
            cut = clause.rfind(' ', 0, max_chars)
            if cut <= 0:
                cut = max_chars
            out.append(clause[:cut].strip())
            clause = clause[cut:].strip()
        if clause:
            out.append(clause)
    return out


class Director:
    """Turns text into spans. Deterministic when given a seed."""

    def __init__(self, persona, table=None):
        self.persona = persona
        self.table = table or EmotionTable()

    def build(self, text, emotion=None, style=None, language='auto', seed=None,
              allow_interjections=True):
        rng = random.Random(seed)
        style_obj = self.persona.style(style)
        tagged, cleaned = self.table.strip_tags(str(text))
        explicit = tagged
        if not explicit and isinstance(emotion, str) and emotion.strip():
            explicit = self.table.get(emotion).name
        cleaned = _MARKER.sub(' ', cleaned).strip()
        language = (language or 'auto').strip().lower()
        if language not in ('auto', 'en', 'ta'):
            raise ValueError('unsupported language %r' % language)
        limits = self.persona.limits

        spans = []
        current_emotion = explicit or self.persona.default_emotion
        sentences = split_sentences(cleaned)
        for s_index, sentence in enumerate(sentences):
            lang = language if language != 'auto' else normalize.detect_language(sentence)
            if not explicit:
                inferred, score = self.table.infer(sentence)
                held = self.table.score(sentence, current_emotion)
                if score > 0 and (score > held or s_index == 0):
                    # A new emotion takes over only when it is at least as strong as
                    # the one already in play; otherwise the previous delivery
                    # persists, which is how a real speaker carries a feeling over a
                    # run of sentences instead of resetting every clause.
                    current_emotion = inferred
                elif s_index == 0:
                    current_emotion = self.persona.default_emotion
                # otherwise the previous sentence's emotion persists, as in speech
            delivery = deliver(self.table.get(current_emotion), style_obj, limits)
            clauses = split_clauses(sentence, self.persona.max_span_chars)
            question = sentence.rstrip().endswith('?')
            exclaim = sentence.rstrip().endswith('!')
            for c_index, clause in enumerate(clauses):
                last = c_index == len(clauses) - 1
                varied = len(clauses) > 1
                pitch = delivery.pitch_hz
                rate = delivery.rate_pct
                if varied:
                    pitch += round(rng.uniform(-1.0, 1.0) * 6.0 * delivery.pitch_range)
                    rate += round(rng.uniform(-1.0, 1.0) * 3.0)
                if last:
                    if question or delivery.contour == 'rise':
                        pitch += 4
                    else:
                        rate -= 2  # sentence-final cadence
                pitch = max(limits['pitch_hz'][0], min(limits['pitch_hz'][1], pitch))
                rate = max(limits['rate_pct'][0], min(limits['rate_pct'][1], rate))
                spans.append(Span(
                    text=normalize.spoken_form(clause, lang), source=clause, language=lang,
                    emotion=current_emotion, rate_pct=rate, pitch_hz=pitch,
                    volume_pct=delivery.volume_pct,
                    pause_after_ms=pause_after(clause, last, delivery.pause_scale, exclaim),
                    breath_before=bool(last and len(clause) > 60
                                       and rng.random() < self.persona.breath_probability * delivery.breath),
                    contour=delivery.contour, index=len(spans),
                    humanize_cents=delivery.humanize_cents,
                    breath_amount=delivery.breath))
        spans = self._add_interjection(spans, random.Random(seed), allow_interjections)
        whole_lang = language if language != 'auto' else (spans[0].language if spans else 'en')
        dominant = explicit or (spans[0].emotion if spans else self.persona.default_emotion)
        return Plan(persona=self.persona.name, style=style_obj.name, emotion=dominant,
                    language=language, spans=tuple(spans),
                    text=normalize.spoken_form(' '.join(sentences), whole_lang))

    def _add_interjection(self, spans, rng, allowed):
        if not allowed or not spans:
            return spans
        first = spans[0]
        if len(first.text) < 30:
            return spans
        marker = self.persona.pick_interjection(first.language, rng)
        if not marker:
            return spans
        return [dataclasses.replace(first, text='%s, %s' % (marker, first.text))] + list(spans[1:])


def pause_after(clause, is_last, pause_scale, exclaim):
    stripped = clause.rstrip()
    if is_last:
        base = 260 if exclaim else 320
        if stripped.endswith('?'):
            base = 340
    elif stripped.endswith(','):
        base = 120
    elif stripped.endswith((';', ':')):
        base = 190
    else:
        base = 150
    return int(max(40, min(900, round(base * pause_scale))))
