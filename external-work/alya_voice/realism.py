"""Optional ffmpeg realism pass.

Ported from the owner's `lya-external-work/lya-voice` engine, which proved that
measurable polish beats guessing: a real telephone band, AGC-style compression,
loudness normalisation and a very low noise bed are what make a synthetic take
sit like a recording rather than like a synthesiser.

Two deliberate changes from that work:

* It is OFF by default. LYA's desktop path must not spawn a subprocess per
  answer (latency and battery), and masking artefacts is not the same as fixing
  them - so the owner chooses per call.
* `phone` is an explicit *call mode*, not the default. An assistant reading out a
  report has to stay intelligible; the telephone band is for call-style speech.

Requires ffmpeg on PATH. When it is missing, `available()` reports it and call
sites keep the untouched audio - never a silent switch to a different sound.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Modes: none = no processing, raw = loudness only (A/B), studio = voice-note /
# video style, phone = mobile-call style.
MODES = ('none', 'raw', 'studio', 'phone')

# Same girl, different seat. `shift` is a pitch+formant move with the tempo
# restored; `tilt` is a shallow tone control.
PERSONALITIES = {
    'lya': {'shift': 1.000, 'tilt': None, 'note': 'default, neutral-bright'},
    'soft': {'shift': 0.982, 'tilt': 'lowshelf=f=220:g=1.5', 'note': 'gentler, rounder'},
    'bright': {'shift': 1.018, 'tilt': 'treble=g=2', 'note': 'livelier, crisp'},
    'deep': {'shift': 0.965, 'tilt': 'lowshelf=f=200:g=2.5', 'note': 'lower, calmer'},
}


class RealismError(RuntimeError):
    """Raised when ffmpeg is missing or the filter chain fails."""


def ffmpeg_path():
    return shutil.which('ffmpeg')


def available():
    path = ffmpeg_path()
    if not path:
        return False, 'ffmpeg is not on PATH (realism pass unavailable)'
    return True, str(path)


def _personality(name):
    return PERSONALITIES.get(str(name or 'lya').lower(), PERSONALITIES['lya'])


def chain(mode='studio', personality='lya', sample_rate=24000, depth=0.5):
    """Pure function: the filter chain as a string, so it can be tested and printed."""
    mode = str(mode).lower()
    if mode not in MODES:
        raise ValueError('unknown realism mode %r; known: %s' % (mode, ', '.join(MODES)))
    if mode == 'none':
        return ''
    person = _personality(personality)
    filters = []
    if person['tilt']:
        filters.append(person['tilt'])
    shift = person['shift']
    if abs(shift - 1.0) > 1e-6:
        filters.append('asetrate=%d' % int(sample_rate * shift))
        filters.append('aresample=%d' % sample_rate)
        filters.append('atempo=%.6f' % (1.0 / shift))
    if mode == 'phone':
        filters += ['highpass=f=250', 'lowpass=f=3400']
        filters.append('acompressor=threshold=-20dB:ratio=4:attack=8:release=180:makeup=3')
        filters.append('afftdn=nr=8:nf=-45')
        filters.append('loudnorm=I=-16:TP=-1.5:LRA=7')
    elif mode == 'studio':
        filters.append('highpass=f=70')
        filters.append('acompressor=threshold=-18dB:ratio=2.5:attack=12:release=250:makeup=2')
        if depth > 0.5:
            filters.append('treble=g=1')
        filters.append('loudnorm=I=-16:TP=-1.5:LRA=9')
    else:  # raw
        filters.append('loudnorm=I=-16:TP=-1.5:LRA=9')
    return ','.join(filters)


def ambience_chain(mode='studio', seed=-1, sample_rate=24000):
    """Very low room/line noise bed, seeded so a take is reproducible."""
    mode = str(mode).lower()
    if mode == 'phone':
        return ('anoisesrc=r=%d:a=0.35:color=pink:seed=%d,lowpass=f=3000,volume=-42dB'
                % (sample_rate, seed))
    return ('anoisesrc=r=%d:a=0.25:color=brown:seed=%d,lowpass=f=1200,volume=-48dB'
            % (sample_rate, seed))


def apply(src, dest, mode='studio', personality='lya', ambience=True, seed=-1,
          sample_rate=24000, depth=0.5, timeout=120):
    """Run the pass. Returns dest. Raises RealismError so the caller can choose."""
    mode = str(mode).lower()
    if mode == 'none':
        raise ValueError('mode "none" means no processing; do not call apply()')
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise RealismError('ffmpeg is not on PATH')
    filters = chain(mode, personality, sample_rate, depth)
    argv = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src)]
    if ambience:
        graph = ('[0:a]%s[v];%s[n];[v][n]amix=inputs=2:duration=first:'
                 'dropout_transition=0:normalize=0,alimiter=limit=0.95[a]'
                 % (filters, ambience_chain(mode, seed, sample_rate)))
        argv += ['-filter_complex', graph, '-map', '[a]']
    else:
        argv += ['-af', filters]
    argv += ['-ar', str(sample_rate), '-ac', '1', str(dest)]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RealismError('ffmpeg failed: %s' % (result.stderr or '').strip()[:300])
    if not Path(dest).exists() or Path(dest).stat().st_size == 0:
        raise RealismError('ffmpeg produced no output')
    return Path(dest)
