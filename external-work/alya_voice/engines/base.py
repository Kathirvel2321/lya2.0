"""Engine protocol shared by the offline and remote speech backends.

An engine turns a Plan into an ordered stream of Chunks. A Chunk either carries
decoded PCM (so the runtime can post-process it) or a compressed file path (for
backends whose codec we cannot decode locally, e.g. the Edge MP3 stream). The
runtime plays both, and it is explicit about which path it took.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    engine: str
    text: str = ''
    samples: object = None       # numpy float32 PCM mono, or None
    sample_rate: int = 0
    path: str = ''               # compressed audio when PCM is unavailable
    seconds: float = 0.0
    paused_after_ms: int = 0
    breath_before: bool = False
    first_audio_ms: float = 0.0
    synth_ms: float = 0.0
    language: str = 'en'
    emotion: str = 'neutral'
    cached: bool = False

    @property
    def decoded(self):
        return self.samples is not None


def pct_string(value, low, high):
    """Edge/SAPI-safe integer percent, e.g. '-8%'."""
    return '%+d%%' % max(low, min(high, int(round(float(value)))))


def hz_string(value, low, high):
    """Edge-safe integer Hz, e.g. '+15Hz'."""
    return '%+dHz' % max(low, min(high, int(round(float(value)))))


class EngineError(RuntimeError):
    """Raised when an engine cannot render, so the runtime can fall back."""


class Engine:
    name = 'engine'
    kind = 'local'
    supports_dsp = True

    def available(self):
        """(bool, reason). Must be cheap and must not open audio devices."""
        raise NotImplementedError

    def render(self, plan, seed=None):
        """Yield Chunk objects in span order. Must honour stop()."""
        raise NotImplementedError

    def stop(self):
        """Cancel current work as soon as possible."""

    def close(self):
        """Release model memory and temporary files."""
