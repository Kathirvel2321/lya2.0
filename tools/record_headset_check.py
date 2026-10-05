"""Make a short owner-local headset listening copy; no network or source retention."""
import tempfile
import sys
import wave
from pathlib import Path
import sounddevice as sd
import winsound

index = None
if '--wasapi' in sys.argv:
    default_name = sd.query_devices(kind='input')['name']
    index = next(i for i, item in enumerate(sd.query_devices())
                 if item['max_input_channels'] and item['name'] == default_name
                 and sd.query_hostapis(item['hostapi'])['name'] == 'Windows WASAPI')
device = sd.query_devices(index, 'input')['name']
print('Selected input:', device, flush=True)

with sd.RawInputStream(device=index, samplerate=16000, channels=1, dtype='int16') as stream:
    print('Headset ready: five low countdown beeps, then a high beep. Speak after the high beep.', flush=True)
    for _ in range(5):
        winsound.Beep(500, 120)
        stream.read(16000)
    winsound.Beep(900, 200)
    stream.read(320)
    frames = [bytes(stream.read(320)[0]) for _ in range(600)]

path = Path(tempfile.mkdtemp(prefix='lya-headset-check-')) / 'voice.wav'
with wave.open(str(path), 'wb') as output:
    output.setnchannels(1)
    output.setsampwidth(2)
    output.setframerate(16000)
    output.writeframes(b''.join(frames))
print(path, flush=True)
