"""Minimal WAV I/O and duration helpers. No extra dependencies."""
from __future__ import annotations

import wave

import numpy as np


def float_to_int16(samples, dither=False):
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    np.clip(samples, -1.0, 1.0, out=samples)
    scaled = samples * 32767.0
    if dither:
        rng = np.random.default_rng(0)
        scaled = scaled + rng.normal(scale=0.5, size=scaled.size)
    return np.clip(np.rint(scaled), -32768, 32767).astype('<i2')


def int16_to_float(data):
    return (np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768.0)


def write_wav(path, samples, sr):
    """Mono 16-bit PCM. Returns the path as a string."""
    payload = float_to_int16(samples)
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(round(sr)))
        handle.writeframes(payload.tobytes())
    return str(path)


def read_wav(path):
    with wave.open(str(path), 'rb') as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        sr = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if width != 2:
        raise ValueError('only 16-bit PCM WAV is supported')
    samples = int16_to_float(frames)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1).astype(np.float32)
    return samples, sr


def duration_seconds(samples, sr):
    return float(len(np.asarray(samples).reshape(-1))) / float(sr) if sr else 0.0


def mp3_duration_estimate(path, bitrate_bps=48000):
    """Edge TTS streams 24 kHz mono CBR MP3 at 48 kbps, so bytes imply duration."""
    import os
    return os.path.getsize(str(path)) * 8.0 / float(bitrate_bps)
