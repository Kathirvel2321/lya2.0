"""Measure PCM16 microphone levels with an optional local Rust build."""
import ctypes
from pathlib import Path
import sys


class _Metrics(ctypes.Structure):
    _fields_ = [('peak', ctypes.c_uint32), ('rms', ctypes.c_float)]


def _load_native():
    name = {'win32': 'lya_pcm.dll', 'linux': 'liblya_pcm.so', 'darwin': 'liblya_pcm.dylib'}.get(sys.platform)
    if name is None or sys.byteorder != 'little':
        return None
    library = Path(__file__).resolve().parent / 'native_pcm' / 'target' / 'release' / name
    try:
        measure = ctypes.CDLL(str(library)).lya_pcm16_metrics_v1
    except (OSError, AttributeError):
        return None
    measure.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    measure.restype = _Metrics
    return measure


_native_measure = _load_native()


def measure_pcm16(pcm):
    """Return the sample count, absolute peak and RMS of one audio block."""
    count = len(pcm) // 2
    if not count:
        return 0, 0, 0.0
    if _native_measure is not None and isinstance(pcm, bytes):
        metrics = _native_measure(pcm, len(pcm))
        return count, metrics.peak, metrics.rms

    import numpy as np
    samples = np.frombuffer(pcm[:count * 2], np.int16)
    peak = int(np.abs(samples.astype(np.int32)).max())
    rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
    return count, peak, rms
