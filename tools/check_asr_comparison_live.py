"""Owner-ready twenty-second input comparison. No recording saved or network."""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio import voice
from desktop.setup_speech import _load_voice


def main():
    import sounddevice as sd
    import winsound
    import vosk
    from faster_whisper import WhisperModel
    from faster_whisper.vad import get_speech_timestamps
    vosk.SetLogLevel(-1)
    snapshots = ROOT / 'models/speech/models--Systran--faster-whisper-base.en/snapshots'
    whisper_path = next(p for p in snapshots.iterdir() if (p / 'model.bin').is_file())
    whisper = WhisperModel(str(whisper_path), device='cpu', compute_type='int8',
                           cpu_threads=2, local_files_only=True)
    paths = (('US English', Path.home() / 'AppData/Local/LYA/models/vosk-model-small-en-us-0.15'),
             ('Indian English', ROOT / 'models/speech/vosk-model-small-en-in-0.4'))
    models = [(name, path, vosk.Model(str(path))) for name, path in paths]
    renderer = _load_voice(keep_warm=True)
    try:
        renderer.speak('After five countdown beeps and one long high beep, please say what time is it. You will have twenty seconds.',
                       engine='offline_piper', play=True, allow_interjections=False)
    finally:
        renderer.close()
    with voice._mic_lock, sd.RawInputStream(samplerate=16000, channels=1, dtype='int16',
                                           device=voice._input_device(sd)) as stream:
        for number in range(5, 0, -1):
            print('Countdown: ' + str(number), flush=True)
            winsound.Beep(500, 120)
            stream.read(16000)
        print('TWENTY SECOND WINDOW OPEN: say what time is it after the long high beep.', flush=True)
        winsound.Beep(1000, 400)
        frames = []
        for _ in range(1000):
            data, overflow = stream.read(320)
            if overflow:
                raise RuntimeError('Microphone overflow; comparison invalid')
            frames.append(bytes(data))
    samples = np.frombuffer(b''.join(frames), np.int16).astype(np.float32) / 32768
    frames = None
    timestamps = get_speech_timestamps(samples)
    print('Speech detector found segments: ' + str(bool(timestamps)), flush=True)
    for name, path, model in models:
        voice._local = model
        os.environ['LYA_VOSK_MODEL'] = str(path)
        try:
            text = voice.transcribe(voice._wav((samples * 32768).astype(np.int16).tobytes()).getvalue())
            print(name + ' accepted: ' + text, flush=True)
        except voice.RecognitionUncertain as error:
            print(name + ' uncertain candidate: ' + error.candidate, flush=True)
    segments, _ = whisper.transcribe(samples, language='en', beam_size=5, temperature=0,
                                     condition_on_previous_text=False, vad_filter=True)
    print('Whisper base candidate: ' + ' '.join(s.text.strip() for s in segments), flush=True)
    samples = None


if __name__ == '__main__':
    main()
