"""Public synthetic voice comparison only: no playback, microphone or network."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'external-work'))
from alya_voice import audiofile
from alya_voice.engines.offline_piper import _session
from desktop.setup_speech import _load_voice
import numpy as np


class _FloatSpeedSession:
    """Compatibility for this installed float-speed model and int-speed API."""
    def __init__(self, session):
        self.session = session
        self._model_path = session._model_path

    def get_inputs(self):
        return self.session.get_inputs()

    def run(self, names, inputs):
        return self.session.run(names, dict(inputs, speed=np.asarray(inputs['speed'], dtype=np.float32)))

OUT = Path(__file__).resolve().parent
TEXT = "I'm here. Take your time, and tell me what you need."


def main():
    from kokoro_onnx import Kokoro
    model = ROOT / 'models' / 'voice'
    start = time.perf_counter()
    kokoro = Kokoro.from_session(_FloatSpeedSession(_session(model / 'kokoro-v1.0.int8.onnx')),
                                str(model / 'voices-v1.0.bin'))
    load_ms = (time.perf_counter() - start) * 1000
    results = []
    for trial in range(2):
        start = time.perf_counter()
        samples, rate = kokoro.create(TEXT, voice='af_bella', speed=1.0, lang='en-us')
        elapsed = (time.perf_counter() - start) * 1000
        path = OUT / 'bella-public-preview.wav'
        audiofile.write_wav(path, samples, rate)
        results.append(dict(engine='kokoro_bella', trial=trial, synthesis_ms=round(elapsed, 1),
                            audio_seconds=round(len(samples) / rate, 3), load_ms=round(load_ms, 1)))
    voice = _load_voice(keep_warm=True)
    try:
        report = voice.speak(TEXT, play=False, engine='offline_piper',
                             allow_interjections=False, wav=OUT / 'current-public-preview.wav')
        results.append(dict(engine='piper_current', synthesis_ms=round(report.total_ms, 1),
                            audio_seconds=round(report.audio_seconds, 3)))
    finally:
        voice.close()
    (OUT / 'voice-choice-timing.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
