"""F0 (pitch) probe - measures how young / bright a rendered voice actually is.

Ported from the owner's `lya-external-work/lya-voice/tests/f0_probe.py`, which was
the first honest acceptance instrument in either voice effort: it turned "does
she sound like a 21-year-old?" into a number that can be compared between engines
instead of argued about.

Method: get mono 16 kHz PCM (stdlib WAV reader, or ffmpeg for MP3), then
autocorrelation over 40 ms voiced frames. Pure Python, no numpy required.

Reference: adult female ~165-255 Hz, adult male ~85-155 Hz, young child 250-400 Hz.
Pitch is only half of perceived age - formants (vocal-tract size) are not measured
here, so a bright adult voice still reads as an adult.

Usage:
    python tools/f0_probe.py out/reel-01-warm.wav out/neural/span-000.mp3 --json out/f0.json
"""
from __future__ import annotations

import json
import shutil
import statistics
import struct
import subprocess
import sys
import wave
from pathlib import Path

SR = 16000
FRAME = int(SR * 0.04)
HOP = int(SR * 0.02)
EVERY = 3
F0_MIN, F0_MAX = 90, 400
MIN_CORR = 0.30
MAX_SECONDS = 14.0


def decode(path):
    """Mono float samples at 16 kHz, from WAV directly or MP3 through ffmpeg."""
    path = Path(path)
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        raw = subprocess.run(
            [ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(path),
             '-t', str(MAX_SECONDS), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
            capture_output=True).stdout
    elif path.suffix.lower() == '.wav':
        with wave.open(str(path), 'rb') as handle:
            raw = handle.readframes(int(handle.getframerate() * MAX_SECONDS))
    else:
        raise RuntimeError('ffmpeg is needed to read %s' % path.suffix)
    count = len(raw) // 2
    values = struct.unpack('<%dh' % count, raw[:count * 2])
    return [v / 32768.0 for v in values]


def frame_f0(frame):
    """Fundamental frequency of one frame, or None when unvoiced."""
    n = len(frame)
    mean = sum(frame) / n
    x = [v - mean for v in frame]
    energy = sum(v * v for v in x)
    if energy <= 1e-5:
        return None
    best_lag, best = 0, 0.0
    for lag in range(SR // F0_MAX, SR // F0_MIN):
        corr = 0.0
        for i in range(0, n - lag, 2):
            corr += x[i] * x[i + lag]
        if corr > best:
            best, best_lag = corr, lag
    if not best_lag:
        return None
    if best / (energy / 2) < MIN_CORR:
        return None
    return SR / best_lag


def measure(path):
    """{'file', 'median_hz', 'p10_hz', 'p90_hz', 'voiced_pct', 'frames'} or errors."""
    samples = decode(path)
    if len(samples) < FRAME * 2:
        return {'file': str(path), 'error': 'too short or silent'}
    values = []
    for start in range(0, len(samples) - FRAME, HOP * EVERY):
        found = frame_f0(samples[start:start + FRAME])
        if found:
            values.append(found)
    if not values:
        return {'file': str(path), 'error': 'no voiced frames detected'}
    values.sort()
    return {
        'file': str(path),
        'median_hz': round(statistics.median(values), 1),
        'p10_hz': round(values[int(len(values) * 0.10)], 1),
        'p90_hz': round(values[min(len(values) - 1, int(len(values) * 0.90))], 1),
        'voiced_pct': round(100.0 * len(values) / max(1, len(samples) // (HOP * EVERY)), 1),
        'frames': len(values),
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    json_out = None
    if '--json' in args:
        index = args.index('--json')
        json_out = args[index + 1]
        del args[index:index + 2]
    if not args:
        print(__doc__)
        return 2
    results = []
    print('F0 (pitch) estimate - higher = brighter / younger-sounding')
    print('-' * 74)
    for name in args:
        if not Path(name).exists():
            print('%-34s missing' % Path(name).name)
            results.append({'file': name, 'error': 'missing'})
            continue
        row = measure(name)
        results.append(row)
        if 'error' in row:
            print('%-34s %s' % (Path(name).name, row['error']))
        else:
            print('%-34s median %6.1f Hz   p10-p90 %6.1f-%6.1f Hz   voiced %4.1f%%'
                  % (Path(name).name, row['median_hz'], row['p10_hz'], row['p90_hz'],
                     row['voiced_pct']))
    print('-' * 74)
    print('Adult female 165-255 Hz | adult male 85-155 Hz | young child 250-400 Hz')
    if json_out:
        Path(json_out).write_text(json.dumps(results, indent=2), encoding='utf-8')
        print('wrote %s' % json_out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
