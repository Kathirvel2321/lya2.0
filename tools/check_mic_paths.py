"""Compare local input paths without saving audio or sending it anywhere."""
import numpy as np
import sounddevice as sd
import winsound
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audio.voice import DoubleClap


def measure(index, seconds=4):
    info = sd.query_devices(index)
    rate = int(info['default_samplerate'])
    channels = min(2, info['max_input_channels'])
    levels = []
    peaks = []
    print(f'Input {index}: {info["name"]} ({rate} Hz). Speak and clap twice after the beep.', flush=True)
    try:
        with sd.RawInputStream(device=index, samplerate=rate, channels=channels,
                               dtype='int16') as stream:
            winsound.Beep(900, 120)
            for _ in range(int(seconds * rate / 1024)):
                data, overflow = stream.read(1024)
                samples = np.frombuffer(data, np.int16).astype(np.float32)
                if channels > 1:
                    samples = samples.reshape(-1, channels)
                    samples = samples[:, np.argmax(np.mean(samples * samples, axis=0))]
                levels.append(float(np.sqrt(np.mean(samples * samples))))
                peaks.append(float(np.abs(samples).max()))
        print(f'  RMS p95={np.percentile(levels, 95):.0f}, max={max(levels):.0f}; peak={max(peaks):.0f}', flush=True)
    except Exception as error:
        print(f'  unavailable: {type(error).__name__}: {error}', flush=True)


if __name__ == '__main__':
    if '--lya-only' not in sys.argv:
        for device in (1, 9, 16, 17, 10):
            measure(device)
    print('LYA input: say LYA after first beep; clap twice after second beep.', flush=True)
    with sd.RawInputStream(samplerate=16000, channels=1, dtype='int16') as stream:
        for label in ('voice', 'claps'):
            detector = DoubleClap() if label == 'claps' else None
            levels, peaks, accepted = [], [], False
            winsound.Beep(900, 120)
            for _ in range(250):
                data, overflow = stream.read(320)
                samples = np.frombuffer(data, np.int16).astype(np.float32)
                levels.append(float(np.sqrt(np.mean(samples * samples))))
                peaks.append(float(np.abs(samples).max()))
                if detector:
                    accepted = detector.feed(bytes(data)) or accepted
            print(f'  {label}: RMS p95={np.percentile(levels, 95):.0f}, max={max(levels):.0f}; peak={max(peaks):.0f}; double-clap accepted={accepted}', flush=True)
