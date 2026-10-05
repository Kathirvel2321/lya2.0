"""Compare owner-authorized local WAV with installed ASR; no transcript files/network."""
import argparse
import gc
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read_audio(path):
    with wave.open(str(path), 'rb') as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError('Expected mono PCM16 WAV.')
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), np.int16).astype(np.float32) / 32768
    divisor = math.gcd(rate, 16000)
    return resample_poly(samples, 16000 // divisor, rate // divisor).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('recording', type=Path)
    parser.add_argument('--whisper-only', action='store_true', help='Compare installed small English model only')
    parser.add_argument('--vad-only', action='store_true', help='Skip the no-VAD comparison')
    args = parser.parse_args()
    samples = read_audio(args.recording)
    if args.whisper_only:
        from faster_whisper import WhisperModel
        import time
        whisper = WhisperModel(str(ROOT / 'models/speech/whisper-small-en'), device='cpu',
                               compute_type='int8', cpu_threads=4, local_files_only=True)
        for vad in ((True,) if args.vad_only else (False, True)):
            started = time.perf_counter()
            segments, _ = whisper.transcribe(samples, language='en', beam_size=5, temperature=0,
                                             condition_on_previous_text=False, vad_filter=vad)
            segments = list(segments)
            print('Local Whisper small candidate, VAD=' + str(vad) + ': ' +
                  ' '.join(s.text.strip() for s in segments)[:1000], flush=True)
            print('Decode seconds:', round(time.perf_counter() - started, 2), flush=True)
            print('Rejection signals:', [(round(s.avg_logprob, 3), round(s.compression_ratio, 3),
                                         round(s.no_speech_prob, 3)) for s in segments], flush=True)
        return
    enhanced_path = args.recording.parent / 'question-enhanced.wav'
    import sherpa_onnx
    config = sherpa_onnx.OfflineSpeechDenoiserConfig(model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(
        gtcrn=sherpa_onnx.OfflineSpeechDenoiserGtcrnModelConfig(model=str(ROOT / 'models/speech/gtcrn_simple.onnx'))))
    denoiser = sherpa_onnx.OfflineSpeechDenoiser(config)
    enhanced = denoiser(samples, 16000)
    with wave.open(str(enhanced_path), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(enhanced.sample_rate)
        output.writeframes((np.clip(enhanced.samples, -1, 1) * 32767).astype(np.int16).tobytes())
    print('Private enhanced listening copy:', enhanced_path, flush=True)
    from audio.local_asr import load
    print('Filtered streaming candidate:', load().transcribe(enhanced_path.read_bytes()), flush=True)
    from faster_whisper.vad import get_speech_timestamps
    regions = get_speech_timestamps(samples)
    print('Local speech detector found speech:', bool(regions), flush=True)
    import vosk
    vosk.SetLogLevel(-1)
    paths = (('Current Vosk', Path.home() / 'AppData/Local/LYA/models/vosk-model-small-en-us-0.15'),
             ('Indian Vosk', ROOT / 'models/speech/vosk-model-small-en-in-0.4'))
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes()
    for name, path in paths:
        model = vosk.Model(str(path))
        recognizer = vosk.KaldiRecognizer(model, 16000)
        recognizer.SetWords(True)
        parts = []
        for i in range(0, len(pcm), 4000):
            if recognizer.AcceptWaveform(pcm[i:i + 4000]):
                parts.append(json.loads(recognizer.Result()).get('text', ''))
        parts.append(json.loads(recognizer.FinalResult()).get('text', ''))
        print(name + ' candidate (not a verified transcript): ' + ' '.join(parts)[:600], flush=True)
        del recognizer, model
        gc.collect()
    from faster_whisper import WhisperModel
    snapshots = ROOT / 'models/speech/models--Systran--faster-whisper-base.en/snapshots'
    path = next(p for p in snapshots.iterdir() if (p / 'model.bin').is_file())
    whisper = WhisperModel(str(path), device='cpu', compute_type='int8', cpu_threads=2, local_files_only=True)
    segments, _ = whisper.transcribe(samples, language='en', beam_size=5, temperature=0,
                                     condition_on_previous_text=False, vad_filter=True)
    print('Whisper base candidate (not verified): ' + ' '.join(s.text.strip() for s in segments)[:600], flush=True)


if __name__ == '__main__':
    main()
