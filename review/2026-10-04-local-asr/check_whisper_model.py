"""Real installed model with generated public speech and silence; no live I/O."""
import io
import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from audio import local_whisper, voice


def main():
    here = Path(__file__).resolve().parent
    public = ROOT / 'review/2026-10-03-voice-conversation/amy-public-preview.wav'
    text = local_whisper.transcribe(public.read_bytes()).lower()
    checks = {'generated_public_speech_accepted': 'here' in text and 'time' in text,
              'silence_rejected': False}
    with io.BytesIO() as buffer:
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(np.zeros(48000, np.int16).tobytes())
        try:
            local_whisper.transcribe(buffer.getvalue())
        except voice.RecognitionUncertain:
            checks['silence_rejected'] = True
    (here / 'synthetic-whisper-check.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    print(json.dumps(checks))
    assert all(checks.values())


if __name__ == '__main__':
    main()
