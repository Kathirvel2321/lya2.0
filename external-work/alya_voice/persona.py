"""The single voice identity: one speaker, many delivery vectors.

English and Tamil are the same person here. The cloud engine uses one
multilingual female voice for both languages. The offline Piper path can either
run 'unified' (one Tamil-trained model speaks both languages, so the timbre
never changes, at some cost to English accent) or 'native' (best per-language
model, two timbres).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .emotions import hz_to_semitones

CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config'
DEFAULT_PERSONA_PATH = CONFIG_DIR / 'persona.json'


@dataclass(frozen=True)
class Style:
    """A delivery vector layered over per-emotion prosody."""

    name: str
    description: str
    rate_offset_pct: float = 0.0
    rate_scale: float = 1.0
    pitch_scale: float = 1.0
    volume_scale: float = 1.0
    pause_scale: float = 1.0
    humanize_scale: float = 1.0
    breath_scale: float = 1.0


@dataclass(frozen=True)
class Persona:
    name: str
    aliases: tuple
    age: int
    gender: str
    base_f0_hz: float
    languages: tuple
    default_style: str
    default_emotion: str
    interjection_probability: float
    breath_probability: float
    max_span_chars: int
    voices: dict
    interjections: dict
    styles: dict
    limits: dict
    source: str = ''

    def style(self, name=None):
        key = (name or self.default_style).strip().lower()
        if key not in self.styles:
            raise KeyError('unknown style %r; known: %s' % (name, ', '.join(sorted(self.styles))))
        return self.styles[key]

    @property
    def style_names(self):
        return tuple(sorted(self.styles))

    def voice(self, engine, language='en', mode='unified'):
        if engine not in self.voices:
            raise KeyError('no voice mapping for engine %r' % engine)
        table = self.voices[engine]
        if mode == 'unified':
            return table['unified']
        if language not in table['per_language']:
            raise KeyError('no %s voice for language %r' % (engine, language))
        return table['per_language'][language]

    def pick_interjection(self, language, rng):
        """A short discourse marker, or None. Her own interjections only."""
        if rng.random() >= self.interjection_probability:
            return None
        pool = self.interjections.get(language) or self.interjections.get('en') or []
        return rng.choice(pool) if pool else None

    def semitones(self, pitch_hz):
        return hz_to_semitones(pitch_hz, self.base_f0_hz)


def _require(mapping, key, kind):
    if key not in mapping:
        raise KeyError('persona is missing %s %r' % (kind, key))
    return mapping[key]


def load_persona(path=None):
    source = Path(path) if path else DEFAULT_PERSONA_PATH
    data = json.loads(Path(source).read_text(encoding='utf-8'))
    allowed = {'_comment', 'name', 'aliases', 'age', 'gender', 'base_f0_hz', 'languages',
               'default_style', 'default_emotion', 'interjection_probability',
               'breath_probability', 'max_span_chars', 'voices', 'interjections',
               'styles', 'delivery_limits'}
    unknown = set(data) - allowed
    if unknown:
        raise KeyError('unknown persona keys: %s' % ', '.join(sorted(unknown)))
    styles = {}
    for name, row in _require(data, 'styles', 'block').items():
        fields = dict(row)
        styles[name] = Style(name=name, **fields)
    limits = dict(_require(data, 'delivery_limits', 'block'))
    limits.pop('_comment', None)
    persona = Persona(
        name=data['name'],
        aliases=tuple(data.get('aliases', [data['name']])),
        age=int(data['age']),
        gender=data['gender'],
        base_f0_hz=float(data['base_f0_hz']),
        languages=tuple(data.get('languages', ['en'])),
        default_style=data.get('default_style', 'everyday'),
        default_emotion=data.get('default_emotion', 'warm'),
        interjection_probability=float(data.get('interjection_probability', 0.0)),
        breath_probability=float(data.get('breath_probability', 0.0)),
        max_span_chars=int(data.get('max_span_chars', 180)),
        voices=dict(_require(data, 'voices', 'block')),
        interjections={k: tuple(v) for k, v in data.get('interjections', {}).items()},
        styles=styles,
        limits=limits,
        source=str(source),
    )
    persona.style(persona.default_style)
    for engine in persona.voices:
        for mode in ('unified',):
            persona.voice(engine, persona.languages[0], mode)
        for language in persona.languages:
            persona.voice(engine, language, 'per_language')
    return persona
