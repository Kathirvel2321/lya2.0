"""Light DSP so one synthetic speaker stops sounding like a synth.

Nothing here needs a GPU or a neural model: WSOLA time-stretch, linear resampling,
cepstral spectral-envelope correction (formant preservation), micro-vibrato,
random micro-drift, breath noise, loudness normalisation and a soft limiter.

Cost note: pitch shifting is the only non-trivial stage. It is bounded to short
spans by the director, and the benchmark in ../out measures it.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-8


def as_float(samples):
    return np.asarray(samples, dtype=np.float32).reshape(-1)


def silence(ms, sr):
    return np.zeros(max(0, int(round(sr * ms / 1000.0))), dtype=np.float32)


def concat(chunks):
    pieces = [as_float(c) for c in chunks if c is not None and len(c)]
    if not pieces:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(pieces).astype(np.float32)


def peak(samples):
    samples = as_float(samples)
    return float(np.max(np.abs(samples))) if samples.size else 0.0


def rms(samples):
    samples = as_float(samples)
    return float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0


def fade_edges(samples, sr, ms=8.0):
    samples = as_float(samples).copy()
    n = len(samples)
    ramp = min(int(sr * ms / 1000.0), n // 2)
    if ramp <= 1:
        return samples
    shape = np.linspace(0.0, 1.0, ramp, dtype=np.float32)
    samples[:ramp] *= shape
    samples[-ramp:] *= shape[::-1]
    return samples


def limiter(samples, ceiling=0.97, knee=0.8):
    samples = as_float(samples)
    scaled = samples / float(ceiling)
    magnitude = np.abs(scaled)
    soft = knee + (1.0 - knee) * np.tanh((magnitude - knee) / (1.0 - knee))
    out = np.where(magnitude <= knee, scaled, np.sign(scaled) * soft) * float(ceiling)
    return np.clip(out, -ceiling, ceiling).astype(np.float32)


def normalize_loudness(samples, target_dbfs=-16.0, ceiling=0.97):
    samples = as_float(samples)
    if samples.size == 0:
        return samples
    current = 20.0 * np.log10(max(rms(samples), EPS))
    gain = 10.0 ** ((float(target_dbfs) - current) / 20.0)
    headroom = ceiling / max(peak(samples), EPS)
    gain = min(gain, headroom)
    return limiter(samples * gain, ceiling=ceiling)


def apply_volume(samples, volume_pct):
    return limiter(as_float(samples) * (1.0 + float(volume_pct) / 100.0))


def resample_linear(samples, ratio):
    """y[i] = x[i * ratio]: duration / ratio, pitch * ratio."""
    samples = as_float(samples)
    ratio = float(ratio)
    if samples.size == 0 or abs(ratio - 1.0) < 1e-9:
        return samples.copy()
    out_len = max(1, int(round(samples.size / ratio)))
    positions = np.arange(out_len, dtype=np.float64) * ratio
    return np.interp(positions, np.arange(samples.size), samples).astype(np.float32)


def time_stretch(samples, factor, sr, frame_ms=40.0, search_ms=12.0):
    """WSOLA: change duration without changing pitch.

    Analysis frames are taken from the input and laid down at synthesis hop
    `hop_s`. Before copying, the frame is nudged by +/- `search` samples to the
    position whose overlap region best matches the *input* tail of the previous
    frame. Matching against the raw input (not the windowed output) is what keeps
    the pitch intact: this is the step that a window-normalised overlap-add gets
    wrong, because it smears periodic content into a different fundamental.
    """
    samples = as_float(samples)
    factor = float(factor)
    if samples.size < 256 or abs(factor - 1.0) < 1e-3:
        return samples.copy()
    frame = max(128, int(sr * frame_ms / 1000.0) // 2 * 2)
    hop_a = frame // 2
    hop_s = max(1, int(round(hop_a * factor)))
    search = max(2, int(sr * search_ms / 1000.0))
    window = np.hanning(frame).astype(np.float32)
    out_len = int(samples.size * factor) + 2 * frame
    out = np.zeros(out_len, dtype=np.float32)
    norm = np.zeros(out_len, dtype=np.float32)
    pos_a, pos_s = 0, 0
    previous = None                       # raw input tail of the last frame
    while pos_a + frame + search < samples.size:
        offset = search // 2
        if previous is not None:
            best = -np.inf
            for candidate in range(0, search + 1):
                block = samples[pos_a + candidate:pos_a + candidate + hop_a]
                if block.size < hop_a:
                    break
                score = float(np.dot(previous, block))
                if score > best:
                    best, offset = score, candidate
        start = pos_a + offset
        block = samples[start:start + frame]
        if block.size < frame:
            break
        out[pos_s:pos_s + frame] += block * window
        norm[pos_s:pos_s + frame] += window
        previous = samples[start + hop_s:start + hop_s + hop_a].copy()
        pos_a += hop_a
        pos_s += hop_s
    end = min(pos_s + frame, out_len)
    out, norm = out[:end], norm[:end]
    np.maximum(norm, 1e-3, out=norm)
    # Overlap-add normalisation: divide by the window sum so amplitude is flat.
    return (out / norm).astype(np.float32)


def spectral_envelope(samples, sr, frame=1024, hop=512, order=32):
    """Smoothed log-amplitude envelope: (magnitude, freqs) on the frame grid."""
    samples = as_float(samples)
    freqs = np.fft.rfftfreq(frame, 1.0 / sr)
    if samples.size == 0:
        return np.ones(frame // 2 + 1, dtype=np.float32), freqs
    window = np.hanning(frame).astype(np.float32)
    acc = np.zeros(frame // 2 + 1, dtype=np.float64)
    if samples.size < frame:
        padded = np.zeros(frame, dtype=np.float32)
        padded[:samples.size] = samples
        acc += np.abs(np.fft.rfft(padded * window))
        count = 1
    else:
        count = 0
        for start in range(0, samples.size - frame + 1, hop):
            acc += np.abs(np.fft.rfft(samples[start:start + frame] * window))
            count += 1
        count = max(count, 1)
    acc = np.maximum(acc / count, 1e-7)
    cepstrum = np.fft.irfft(np.log(acc), frame)
    lifter = np.zeros(frame, dtype=np.float64)
    lifter[:order + 1] = 1.0
    lifter[frame - order:] = 1.0
    return np.exp(np.fft.rfft(cepstrum * lifter, frame).real).astype(np.float32), freqs


def apply_gain_curve(samples, sr, grid_freqs, gains, pad=512):
    """Zero-phase filtering by an amplitude curve sampled on a coarse grid."""
    samples = as_float(samples)
    if samples.size < 64:
        return samples.copy()
    pad = int(min(pad, max(16, samples.size // 4)))
    padded = np.concatenate([samples[:pad][::-1], samples, samples[-pad:][::-1]]).astype(np.float64)
    n_fft = 1 << int(np.ceil(np.log2(padded.size)))
    spectrum = np.fft.rfft(padded, n_fft)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    curve = np.interp(freqs, grid_freqs, gains, left=gains[0], right=gains[-1])
    filtered = np.fft.irfft(spectrum * curve, n_fft)[:padded.size]
    return filtered[pad:pad + samples.size].astype(np.float32)


def _fit_length(samples, length):
    samples = as_float(samples)
    if samples.size == length:
        return samples
    if samples.size > length:
        return samples[:length].copy()
    return np.concatenate([samples, np.zeros(length - samples.size, dtype=np.float32)])


def pitch_shift(samples, sr, semitones, formant=True, alpha=0.8, max_gain_db=12.0):
    """Shift pitch by `semitones`, preserving duration and (optionally) formants."""
    samples = as_float(samples)
    semitones = float(semitones)
    if samples.size < 256 or abs(semitones) < 0.02:
        return samples.copy()
    ratio = 2.0 ** (semitones / 12.0)
    source_env = spectral_envelope(samples, sr) if formant else None
    shifted = resample_linear(time_stretch(samples, ratio, sr), ratio)
    shifted = _fit_length(shifted, samples.size)
    if not formant or source_env is None:
        return shifted
    out_env = spectral_envelope(shifted, sr)
    gain = np.power(source_env[0] / np.maximum(out_env[0], EPS), float(alpha))
    limit = 10.0 ** (max_gain_db / 20.0)
    gain = np.clip(gain, 1.0 / limit, limit).astype(np.float32)
    return _fit_length(apply_gain_curve(shifted, sr, out_env[1], gain), samples.size)


def vibrato(samples, sr, cents=0.0, rate_hz=5.0):
    """Bounded, length-preserving micro pitch movement."""
    samples = as_float(samples)
    cents = float(cents)
    if samples.size < 256 or cents <= 0.01:
        return samples.copy()
    depth = 2.0 ** (cents / 1200.0) - 1.0
    amplitude = depth * sr / (2.0 * np.pi * float(rate_hz))
    n = np.arange(samples.size, dtype=np.float64)
    delay = amplitude * (1.0 - np.cos(2.0 * np.pi * float(rate_hz) * n / sr))
    return np.interp(n - delay, n, samples, left=float(samples[0]),
                     right=float(samples[-1])).astype(np.float32)


def humanize(samples, sr, cents=10.0, seed=0):
    """Two-stage micro-pitch movement so no syllable is clinically flat."""
    if float(cents) <= 0.01:
        return as_float(samples)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    fast = vibrato(samples, sr, cents=float(cents) * 0.45, rate_hz=rng.uniform(4.2, 6.0))
    return vibrato(fast, sr, cents=float(cents) * 0.55, rate_hz=rng.uniform(0.6, 1.4))


def breath(sr, ms, level=0.05, seed=0, shape='inhale'):
    """Soft band-shaped noise. Used as an audible intake before long phrases."""
    n = max(1, int(round(sr * float(ms) / 1000.0)))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    noise = rng.normal(size=n).astype(np.float32)
    noise = np.diff(noise, prepend=noise[:1]).astype(np.float32)
    noise = np.convolve(noise, np.ones(3, dtype=np.float32) / 3.0, mode='same')
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)
    # Clip first: np.sin can return a tiny negative value at the endpoints, and a
    # fractional power of a negative number is NaN, which would silence the puff.
    envelope = np.clip(np.sin(np.pi * t), 0.0, None) ** 1.5
    edge = np.clip(t if shape == 'inhale' else (1.0 - t), 0.0, None)
    envelope = envelope * np.sqrt(edge)
    loudest = float(max(np.abs(noise).max(), EPS))
    return (noise / loudest * envelope * float(level)).astype(np.float32)
