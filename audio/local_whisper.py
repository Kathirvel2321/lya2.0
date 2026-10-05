"""English command recognition using installed weights; never downloads at runtime."""
import io
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / 'models/speech/whisper-small-en'
FILES = ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt')


def model_path():
    return Path(os.environ.get('LYA_WHISPER_MODEL') or DEFAULT_MODEL)


def available():
    return all((model_path() / name).is_file() for name in FILES)


@lru_cache(maxsize=1)
def load(path):
    # Requiring the tokenizer also prevents faster-whisper's tokenizer fallback download.
    if not all((Path(path) / name).is_file() for name in FILES):
        raise RuntimeError('Local English command model is incomplete.')
    from faster_whisper import WhisperModel
    return WhisperModel(path, device='cpu', compute_type='int8', cpu_threads=4,
                        num_workers=1, local_files_only=True)


def transcribe(wav_bytes):
    from audio.voice import RecognitionUncertain
    model = load(str(model_path()))
    segments, _ = model.transcribe(
        io.BytesIO(wav_bytes), language='en', beam_size=5, temperature=0,
        condition_on_previous_text=False, vad_filter=True)
    segments = list(segments)
    text = ' '.join(segment.text.strip() for segment in segments).strip()
    words = re.findall(r"[a-z']+", text.casefold())
    repeated = any(count >= 3 for count in Counter(zip(words, words[1:], words[2:])).values())
    # Library default failure thresholds are rejection heuristics, not accuracy proof.
    # Reject the whole question rather than forwarding only its confident clauses.
    if not text or repeated or any(segment.avg_logprob < -1.0 or segment.compression_ratio > 2.4 or
                       segment.no_speech_prob > 0.6 for segment in segments):
        raise RecognitionUncertain('Please repeat the question; local recognition was uncertain.', text)
    return text
