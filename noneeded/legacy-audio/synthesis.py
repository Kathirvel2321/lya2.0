"""Local-only speech rendering. No model download, network or microphone at runtime."""
import json
import re
import unicodedata
from pathlib import Path

MODELS = Path(__file__).resolve().parents[1] / 'models' / 'voice'
# These are pacing styles, not a claim of emotion-conditioned synthesis.
SPEEDS = {'warm': 0.96, 'neutral': 1.0, 'cheerful': 1.04, 'calm': 0.90, 'serious': 0.94}
VOICES = {'en': ('af_heart', 'en-us'), 'hi': ('hf_alpha', 'hi'),
          'fr': ('ff_siwis', 'fr-fr'), 'es': ('ef_dora', 'es'),
          'it': ('if_sara', 'it'), 'pt': ('pf_dora', 'pt-br')}


def prepare(text):
    text = re.sub(r'```.*?(?:```|$)', ' Code is available on screen. ', str(text), flags=re.S)
    text = re.sub(r'https?://\S+', ' link on screen ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*#`_]', '', text)
    text = ' '.join(text.split())
    if len(text) > 900:
        text = text[:850].rsplit(' ', 1)[0] + '. The rest is on screen.'
    return text


def segments(text, language='auto'):
    """Script routing for Tamil/English/Hindi; Latin languages require explicit choice."""
    if language not in {'auto', 'ta', *VOICES}:
        raise ValueError('Unsupported speech language')
    current, lang = '', None
    for char in text:
        code = ord(char)
        detected = ('ta' if 0x0B80 <= code <= 0x0BFF else
                    'hi' if 0x0900 <= code <= 0x097F else
                    (language if language in VOICES else 'en') if char.isascii() and char.isalpha() else None)
        if detected is None and char.isalpha():
            # Do not silently mispronounce an unsupported script using English.
            if 'LATIN' not in unicodedata.name(char, ''):
                raise ValueError('No installed voice for this script')
            detected = language if language in VOICES else 'en'
        if detected and lang and detected != lang and current.strip():
            yield lang, current.strip()
            current = ''
        lang = detected or lang
        current += char
    if current.strip():
        yield lang or ('en' if language == 'auto' else language), current.strip()


def session(path):
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.add_session_config_entry('session.intra_op.allow_spinning', '0')
    options.add_session_config_entry('session.inter_op.allow_spinning', '0')
    return ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])


class KokoroSession:
    """Adapt upstream 0.4.9's int32 speed to the pinned export's float input."""
    def __init__(self, runtime):
        self.runtime = runtime
        self.speed = 1.0
        self._model_path = runtime._model_path

    def get_inputs(self):
        return self.runtime.get_inputs()

    def run(self, outputs, inputs):
        import numpy as np
        inputs = dict(inputs, speed=np.asarray([self.speed], dtype=np.float32))
        return self.runtime.run(outputs, inputs)


class Renderer:
    """One female acoustic model; pronunciation rules change, speaker never does.

    English is cross-language synthesis with a Tamil-trained voice. Phoneme
    coverage is checked, but native English quality still needs listening QA.
    """
    def __init__(self):
        self.runtime = None
        self.piper = {}

    def utterances(self, text, language='auto', style='warm'):
        import numpy as np
        from piper import PiperVoice
        from piper.config import PiperConfig, SynthesisConfig
        parts = list(segments(prepare(text), language))
        if any(lang not in ('en', 'ta') for lang, _ in parts):
            raise ValueError('The single voice is currently qualified for Tamil/English testing only')
        speed = SPEEDS.get(style, SPEEDS['warm'])
        if self.runtime is None:
            self.runtime = session(MODELS / 'ta_IN-rasa_female-medium.onnx')
        for lang, part in parts:
            if lang not in self.piper:
                config = PiperConfig.from_dict(json.loads((MODELS / 'ta_IN-rasa_female-medium.onnx.json').read_text('utf-8')))
                config.espeak_voice = 'ta' if lang == 'ta' else 'en-us'
                self.piper[lang] = PiperVoice(self.runtime, config)
            voice = self.piper[lang]
            for sentence in re.findall(r'.+?(?:[.!?]+(?=\s|$)|$)', part):
                for phrase in re.findall(r'.{1,120}(?:\s|$)|\S{1,120}', sentence):
                    phrase = phrase.strip()
                    if not phrase:
                        continue
                    phones = voice.phonemize(phrase)
                    if any(p not in voice.config.phoneme_id_map for row in phones for p in row):
                        raise ValueError('Unsupported pronunciation; text remains available')
                    chunks = list(voice.synthesize(phrase, SynthesisConfig(length_scale=1 / speed)))
                    if chunks:
                        yield phrase, np.concatenate([c.audio_float_array for c in chunks]), chunks[0].sample_rate

    def audio(self, text, language='auto', style='warm'):
        for _, samples, rate in self.utterances(text, language, style):
            yield samples, rate


def sapi(text, style='warm'):
    import win32com.client
    engine = win32com.client.Dispatch('SAPI.SpVoice')
    candidates = [v for v in engine.GetVoices() if v.GetAttribute('Gender') == 'Female'
                  and any((int(x, 16) & 0x3ff) == 9 for x in v.GetAttribute('Language').split(';'))]
    if not candidates:
        raise RuntimeError('No installed female English fallback voice')
    engine.Voice = candidates[0]
    engine.Rate = -1 if style in ('calm', 'serious') else 0
    engine.Speak(prepare(text), 16)


def speak(text, language='auto', style='warm', engine='neural', renderer=None, event=None):
    """Bounded prefetch overlaps the next phrase with playback. No audio files."""
    clean = prepare(text)
    if not clean:
        return
    parts = list(segments(clean, language))
    if engine == 'economy':
        if any(lang != 'en' for lang, _ in parts):
            raise RuntimeError('Economy voice supports English only')
        if event:
            event({'kind': 'caption', 'text': clean})
        return sapi(clean, style)
    import queue
    import threading
    import sounddevice as sd
    pending = queue.Queue(maxsize=2)
    cancelled = threading.Event()
    def put(item):
        while not cancelled.is_set():
            try:
                pending.put(item, timeout=.1)
                return
            except queue.Full:
                pass
    def produce():
        try:
            for item in (renderer or Renderer()).utterances(clean, language, style):
                if cancelled.is_set():
                    break
                put(item)
        except Exception:
            put(RuntimeError('Local voice failed'))
        finally:
            put(None)
    producer = threading.Thread(target=produce, daemon=True)
    producer.start()
    try:
        while True:
            item = pending.get(timeout=60)
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            phrase, samples, rate = item
            sd.play(samples, rate, blocking=False)
            if event:
                event({'kind': 'caption', 'text': phrase})
            sd.wait()
    finally:
        cancelled.set()
        sd.stop()
        producer.join(timeout=2)
        # A stuck producer must not share a cached renderer with the next request.
        if producer.is_alive():
            raise RuntimeError('Speech worker did not stop')
