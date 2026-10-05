"""Free on-device English streaming recognition. No downloads or audio persistence."""
import io
import os
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / 'models/speech/zipformer-en'
ENCODER = 'encoder-epoch-99-avg-1-chunk-16-left-128.int8.onnx'
DECODER = 'decoder-epoch-99-avg-1-chunk-16-left-128.onnx'
JOINER = 'joiner-epoch-99-avg-1-chunk-16-left-128.int8.onnx'


def model_path():
    return Path(os.environ.get('LYA_SHERPA_MODEL') or DEFAULT_MODEL)


def available():
    return all((model_path() / name).is_file() for name in (ENCODER, DECODER, JOINER, 'tokens.txt'))


class LocalEnglishASR:
    def __init__(self, path=None):
        import sherpa_onnx
        path = Path(path or model_path())
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(path / 'tokens.txt'), encoder=str(path / ENCODER),
            decoder=str(path / DECODER), joiner=str(path / JOINER),
            num_threads=2, provider='cpu', enable_endpoint_detection=True,
            rule1_min_trailing_silence=3.0, rule2_min_trailing_silence=2.5,
            rule3_min_utterance_length=120.0, decoding_method='greedy_search')

    def create_stream(self):
        return self.recognizer.create_stream()

    def feed(self, stream, pcm, rate=16000):
        samples = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
        stream.accept_waveform(rate, samples)
        self._decode(stream)
        return self.recognizer.get_result(stream).strip().lower()

    def _decode(self, stream):
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)

    def is_endpoint(self, stream):
        return self.recognizer.is_endpoint(stream)

    def finish(self, stream):
        stream.accept_waveform(16000, np.zeros(8000, np.float32))
        stream.input_finished()
        self._decode(stream)
        return self.recognizer.get_result(stream).strip().lower()

    def transcribe(self, wav_bytes):
        stream = self.create_stream()
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise ValueError('Local recognition expects mono PCM16 WAV.')
            rate = wav.getframerate()
            while pcm := wav.readframes(rate // 10):
                self.feed(stream, pcm, rate)
        return self.finish(stream)


@lru_cache(maxsize=1)
def load():
    return LocalEnglishASR()
