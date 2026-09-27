"""Public synthetic speech -> real local wake model; no microphone or playback."""
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import vosk
from audio import voice
from desktop.setup_speech import _load_voice
from storage.store import get_data_dir

vosk.SetLogLevel(-1)
model = vosk.Model(str(get_data_dir() / 'models' / 'vosk-model-small-en-us-0.15'))
speaker = _load_voice(keep_warm=True)
results = []
try:
    engine = speaker._engine('offline_piper')
    for text, expected in (
        ('Wake up Lya.', True), ('Wake up Leah.', True), ('Hey Leah.', True),
        ('The weather is pleasant today.', False), ('What time is it?', False),
        ('Can you help me please?', False), ('I would like a cup of tea.', False),
    ):
        samples, rate = engine._synthesize(
            engine._voice('en'), SimpleNamespace(text=text, rate_pct=0, index=0))
        audio = np.interp(np.arange(round(len(samples) * 16000 / rate)) * rate / 16000,
                          np.arange(len(samples)), samples)
        audio = np.concatenate((audio, np.zeros(16000)))
        pcm = (audio.clip(-1, 1) * 32767).astype('<i2').tobytes()
        detector = voice.DoubleClap()
        false_claps = sum(detector.feed(pcm[i:i+640]) for i in range(0, len(pcm), 640))
        for claps in (False, True):
            stopped = threading.Event()
            stream = Mock()
            stream.__enter__ = Mock(return_value=stream)
            stream.__exit__ = Mock(return_value=False)
            offset = [0]

            def read(n):
                block = pcm[offset[0]:offset[0] + n * 2]
                offset[0] += n * 2
                if not block:
                    stopped.set()
                    block = bytes(n * 2)
                return block, False

            stream.read.side_effect = read
            with patch('sounddevice.RawInputStream', return_value=stream):
                detected = voice._wait_for_wake(model, claps, stopped, None)
            results.append(dict(public_generated_phrase=text, claps_enabled=claps,
                                detected=detected, expected=expected, false_claps=false_claps,
                                audio_seconds_consumed=round(offset[0] / 32000, 2)))
finally:
    speaker.close()
Path(__file__).with_name('model-check.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results))
assert all(row['detected'] == row['expected'] and row['false_claps'] == 0 for row in results)
