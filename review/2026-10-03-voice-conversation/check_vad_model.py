"""Installed VAD with generated public audio only; no microphone or playback."""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from audio.voice import SpeechActivity


def check(samples):
    detector = SpeechActivity()
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes()
    states = [detector.feed(pcm[i:i + 640].ljust(640, b'\0'))
              for i in range(0, len(pcm), 640)]
    return states


def main():
    here = Path(__file__).resolve().parent
    with wave.open(str(here / 'amy-public-preview.wav')) as wav:
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), np.int16).astype(np.float32) / 32768
    from math import gcd
    divisor = gcd(16000, rate)
    speech = resample_poly(samples, 16000 // divisor, rate // divisor)
    silence = check(np.zeros(32000))
    noise = check(np.random.default_rng(7).normal(0, .015, 32000))
    turn = check(np.concatenate([np.zeros(16000), speech, np.zeros(32000)]))
    results = dict(silence_rejected=not any(silence), generated_noise_rejected=not any(noise),
                   public_speech_detected=any(turn), quiet_tail_released=not any(turn[-50:]))
    (here / 'vad-model-check.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results))
    assert all(results.values())


if __name__ == '__main__':
    main()
