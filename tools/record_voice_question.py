"""Owner-authorized native-input recording, retained only in a private temp folder."""
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import winsound

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio import voice


def main():
    device = voice._input_device(sd)
    info = sd.query_devices(device, 'input')
    rate = int(info['default_samplerate'])
    print('Selected Windows input:', info['name'], flush=True)
    frames = []
    with sd.RawInputStream(device=device, samplerate=rate, channels=1, dtype='int16') as stream:
        print('Five low beeps, then high beep. Speak naturally for 25 seconds after the high beep.', flush=True)
        for _ in range(5):
            winsound.Beep(450, 120)
            _, overflow = stream.read(rate)
            if overflow:
                raise RuntimeError('Input overflow during preparation; retry needed.')
        winsound.Beep(1200, 250)
        for _ in range(1250):
            data, overflow = stream.read(rate // 50)
            if overflow:
                raise RuntimeError('Input overflow; recording invalid.')
            frames.append(bytes(data))
    winsound.Beep(650, 350)
    pcm = b''.join(frames)
    directory = Path(tempfile.mkdtemp(prefix='lya-private-question-'))
    path = directory / 'question.wav'
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)
    samples = np.frombuffer(pcm, np.int16).astype(np.float64)
    print('PRIVATE_RECORDING=' + str(path), flush=True)
    print('Audio received:', bool(np.any(samples)), 'clipped:', bool(np.any(np.abs(samples) >= 32767)), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
