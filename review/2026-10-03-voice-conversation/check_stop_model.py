"""Real local models, generated public speech, fake microphone. No playback/network."""
import json
import sys
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from audio import voice
from desktop.setup_speech import _load_voice


def main():
    import vosk
    vosk.SetLogLevel(-1)
    model_path = Path.home() / 'AppData/Local/LYA/models/vosk-model-small-en-us-0.15'
    model = vosk.Model(str(model_path))
    speaker = _load_voice(keep_warm=True)
    results = []
    try:
        for text, expected in (('Stop.', True), ('Cancel.', True),
                               ('What time is it?', False), ('Please continue answering.', False),
                               ('The bus stop is nearby.', False)):
            plan = speaker.plan(text, language='en', allow_interjections=False)
            audio = np.concatenate([chunk.samples for chunk in speaker._engine('offline_piper').render(plan)])
            audio = resample_poly(audio, 320, 441)
            audio = np.concatenate([np.zeros(3200), audio, np.zeros(32000)])
            pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
            blocks = iter(pcm[offset:offset + 640].ljust(640, b'\0') for offset in range(0, len(pcm), 640))
            stopped = threading.Event()
            stream = Mock()
            stream.__enter__ = Mock(return_value=stream)
            stream.__exit__ = Mock(return_value=False)
            def read(_):
                try:
                    return next(blocks), False
                except StopIteration:
                    stopped.set()
                    return bytes(640), False
            stream.read.side_effect = read
            callback = Mock()
            voice._SPEAKING.set()
            with patch('sounddevice.RawInputStream', return_value=stream), \
                 patch.object(voice, '_input_device_name', return_value='Generated fixture'):
                voice._wait_for_interrupt(model, stopped, callback)
            voice._SPEAKING.clear()
            actual = callback.called
            results.append(dict(public_phrase=text, expected=expected, actual=actual))
        target = Path(__file__).resolve().parent / 'stop-model-check.json'
        target.write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(json.dumps(results))
        assert all(row['expected'] == row['actual'] for row in results)
    finally:
        voice._SPEAKING.clear()
        speaker.close()


if __name__ == '__main__':
    main()
