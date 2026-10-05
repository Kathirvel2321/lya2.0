"""One local command-capture check; no recording, transcript or network retained."""
import sys
from pathlib import Path
import winsound
import sounddevice as sd
import wave
import numpy as np
import time
from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audio import voice

snapshot_root = Path(__file__).resolve().parents[1] / 'models' / 'speech' / 'models--Systran--faster-whisper-base.en' / 'snapshots'
model = WhisperModel(str(next(snapshot_root.iterdir())), device='cpu', compute_type='int8', cpu_threads=4)

original_stream = sd.RawInputStream
peaks = []


class CuedStream:
    def __init__(self, *args, **kwargs):
        self.stream = original_stream(*args, **kwargs)

    def __enter__(self):
        self.stream.__enter__()
        print('Microphone ready: five low beeps, then a high beep. Speak after the high beep.', flush=True)
        for _ in range(5):
            winsound.Beep(500, 120)
            self.stream.read(16000)
        winsound.Beep(900, 200)
        self.stream.read(320)  # Drop the cue from the headset input.
        original_read = self.stream.read

        def metered_read(frames):
            data, overflow = original_read(frames)
            samples = np.frombuffer(data, np.int16).astype(np.int32)
            peaks.append(int(np.abs(samples).max()))
            return data, overflow

        self.stream.read = metered_read
        return self.stream

    def __exit__(self, *args):
        return self.stream.__exit__(*args)


sd.RawInputStream = CuedStream
try:
    wav = voice._record_stream(max_seconds=9, silence=1.0)
finally:
    sd.RawInputStream = original_stream
if wav is None:
    print('No speech segment captured.', flush=True)
else:
    with wave.open(wav, 'rb') as recording:
        samples = np.frombuffer(recording.readframes(recording.getnframes()), np.int16)
        duration = round(recording.getnframes() / recording.getframerate(), 1)
    text = voice.transcribe(wav.getvalue(), offline_required=True).casefold()
    start = time.monotonic()
    segments, _ = model.transcribe(samples.astype(np.float32) / 32768,
                                   language='en', beam_size=1, temperature=0,
                                   condition_on_previous_text=False)
    improved = ' '.join(segment.text for segment in segments).casefold()
    print({'speech_segment_captured': True,
           'duration_seconds': duration,
           'peak': int(np.abs(samples.astype(np.int32)).max()),
           'blocks_above_gate': sum(value > 700 for value in peaks),
           'total_blocks': len(peaks),
           'vosk_weather': 'weather' in text,
           'vosk_mumbai': 'mumbai' in text or 'bombay' in text,
           'whisper_weather': 'weather' in improved,
           'whisper_mumbai': 'mumbai' in improved or 'bombay' in improved,
           'whisper_seconds': round(time.monotonic() - start, 1)}, flush=True)
