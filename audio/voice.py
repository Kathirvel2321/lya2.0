"""One microphone reader, command forwarding, optional local transcription.
Set LYA_VOSK_MODEL to an existing Vosk model directory for offline voice.
Otherwise voice mode uses Google speech recognition; text/build stay offline.
"""
import io
import os
import re
import threading
import time
import wave

WAKE_WORDS=("lya","leya","liya")
CONVERSATION_SECONDS=45
QUIET={"on":False}
LAST_WAV={"wav":None}
_SPEAKING=threading.Event()
_engine=None
_mic_lock=threading.Lock()
_local=None


DEFAULT_VOICE = os.environ.get("LYA_VOICE", "en-US-AvaNeural")
EMOTIONS = {
    "excited":  {"rate": "+15%", "pitch": "+4Hz"},
    "playful":  {"rate": "+10%", "pitch": "+2Hz"},
    "happy":    {"rate": "+8%",  "pitch": "+2Hz"},
    "sad":      {"rate": "-12%", "pitch": "-3Hz"},
    "worried":  {"rate": "+4%",  "pitch": "+3Hz"},
    "serious":  {"rate": "-6%",  "pitch": "-2Hz"},
    "angry":    {"rate": "+10%", "pitch": "-1Hz"},
    "tired":    {"rate": "-15%", "pitch": "-4Hz"},
    "neutral":  {"rate": "+0%",  "pitch": "+0Hz"},
}
_CURRENT_TONE = {"tone": "neutral"}
_STOP_PLAYBACK = threading.Event()


def set_quiet(on): QUIET["on"] = bool(on)
def get_last_wav(): return LAST_WAV["wav"]


def set_tone(tone):
    """Set the emotional tone for upcoming speech synthesis."""
    if tone in EMOTIONS:
        _CURRENT_TONE["tone"] = tone
    return True


def set_rate(rate, base=175):
    global _engine
    try:
        rate = int(rate)
    except (TypeError, ValueError):
        rate = base
    if not 60 <= rate <= 400:          # sane bounds; ignore nonsense
        rate = base
    # Map numerical rate to closest emotional tone for neural TTS
    if rate >= 195:
        _CURRENT_TONE["tone"] = "excited"
    elif rate >= 185:
        _CURRENT_TONE["tone"] = "playful"
    elif rate <= 145:
        _CURRENT_TONE["tone"] = "sad"
    elif rate <= 165:
        _CURRENT_TONE["tone"] = "serious"
    else:
        _CURRENT_TONE["tone"] = "neutral"
    try:
        if _engine is None:
            import pyttsx3
            _engine = pyttsx3.init()
        _engine.setProperty("rate", rate)
        return True
    except Exception:
        return False


def stop_speaking():
    """Interrupt ongoing speech playback immediately."""
    _STOP_PLAYBACK.set()
    _SPEAKING.clear()


def _play_mp3_interruptible(mp3_path, stop_event=None):
    """Play MP3 file using Windows native Multimedia Command Interface (MCI) with interrupt support."""
    if not os.path.exists(mp3_path) or os.name != "nt":
        return False
    import ctypes
    winmm = ctypes.windll.winmm
    alias = f"lya_mp3_{int(time.time() * 1000)}"
    res = winmm.mciSendStringW(f'open "{mp3_path}" type mpegvideo alias {alias}', None, 0, None)
    if res != 0:
        return False
    try:
        winmm.mciSendStringW(f"play {alias}", None, 0, None)
        buf = ctypes.create_unicode_buffer(128)
        while True:
            if stop_event and stop_event.is_set():
                winmm.mciSendStringW(f"stop {alias}", None, 0, None)
                break
            winmm.mciSendStringW(f"status {alias} mode", buf, 128, None)
            if buf.value in ("stopped", ""):
                break
            time.sleep(0.04)
        return True
    except Exception:
        return False
    finally:
        winmm.mciSendStringW(f"close {alias}", None, 0, None)


def speak(text, tone=None, voice_name=None, *args, **kwargs):
    """Speak text with natural 21yo human tone via edge-tts, falling back to local pyttsx3."""
    global _engine
    if QUIET["on"]:
        return
    _STOP_PLAYBACK.clear()
    _SPEAKING.set()
    text_str = str(text).strip()
    if not text_str:
        _SPEAKING.clear()
        return

    # 1. Try Microsoft Edge Neural TTS (ultra-clean, human, 21yo natural voice)
    played = False
    chosen_voice = voice_name or os.environ.get("LYA_VOICE", DEFAULT_VOICE)
    chosen_tone = tone or _CURRENT_TONE.get("tone", "neutral")
    emo = EMOTIONS.get(chosen_tone, EMOTIONS["neutral"])

    try:
        import asyncio
        import edge_tts
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_mp3 = f.name
        try:
            async def _synth():
                comm = edge_tts.Communicate(text_str, chosen_voice, rate=emo["rate"], pitch=emo["pitch"])
                await comm.save(tmp_mp3)
            asyncio.run(_synth())
            if os.path.exists(tmp_mp3) and os.path.getsize(tmp_mp3) > 0 and not _STOP_PLAYBACK.is_set():
                played = _play_mp3_interruptible(tmp_mp3, stop_event=_STOP_PLAYBACK)
        finally:
            if os.path.exists(tmp_mp3):
                try:
                    os.remove(tmp_mp3)
                except Exception:
                    pass
    except Exception:
        played = False

    # 2. Local fallback: pyttsx3 (offline Windows speech)
    if not played and not _STOP_PLAYBACK.is_set():
        try:
            if _engine is None:
                import pyttsx3
                _engine = pyttsx3.init()
                _engine.setProperty("rate", 175)
            _engine.say(text_str)
            _engine.runAndWait()
        except Exception:
            pass

    _SPEAKING.clear()


def _record(seconds):
    import sounddevice as sd
    with _mic_lock:
        audio=sd.rec(int(seconds*16000),samplerate=16000,channels=1,dtype="int16")
        sd.wait()
    return _wav(audio.tobytes())


def _wav(pcm):
    buf=io.BytesIO()
    with wave.open(buf,"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm)
    buf.seek(0)
    return buf


def _record_stream(max_seconds=25,silence=0.8,thresh=700):
    import numpy as np
    import sounddevice as sd
    from collections import deque
    parts=[];pre=deque(maxlen=2);quiet=0;started=False
    with _mic_lock, sd.RawInputStream(samplerate=16000,channels=1,dtype="int16") as stream:
        deadline=time.monotonic()+max_seconds
        while time.monotonic()<deadline:
            data,_=stream.read(3200);pcm=bytes(data)
            loud=float(np.abs(np.frombuffer(pcm,np.int16).astype(np.int32)).max())>thresh
            if loud and not started:
                parts.extend(pre);started=True
            if started:
                parts.append(pcm);quiet=0 if loud else quiet+1
                if quiet>=silence/0.2:break
            else:pre.append(pcm)
    return _wav(b"".join(parts)) if parts else None


def _transcribe_groq(wav_bytes, api_key):
    """Transcribe audio using Groq Whisper Large v3 (fast, multilingual: 99+ languages)."""
    import json
    import urllib.request
    boundary = "----lyawhisperboundary"
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n"
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + wav_bytes + (
        f"\r\n--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"model\"\r\n\r\nwhisper-large-v3\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"temperature\"\r\n\r\n0.0\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "Mozilla/5.0 LYA/1.0",
    }
    req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("text", "").strip()


def transcribe(wav_bytes, offline_required=False):
    global _local
    # 1. If not offline_required, try Groq Whisper Large v3 (multilingual, fast)
    if not offline_required:
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_key:
            try:
                from brain.mind import get_groq_key
                groq_key = get_groq_key()
            except Exception:
                pass
        if groq_key:
            try:
                res = _transcribe_groq(wav_bytes, groq_key)
                if res:
                    return res
            except Exception:
                pass

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        pcm = wav.readframes(wav.getnframes())

    # 2. Local Vosk model (if installed)
    path = os.environ.get("LYA_VOSK_MODEL", "")
    if not path:
        try:
            from storage.store import get_data_dir
            candidate = get_data_dir() / "models" / "vosk"
            if candidate.is_dir():
                path = str(candidate)
        except Exception:
            pass
    if path:
        import json
        import vosk
        if not os.path.isdir(path):
            raise RuntimeError(f"Vosk model path does not exist: {path}")
        if _local is None:
            _local = vosk.Model(path)
        recognizer = vosk.KaldiRecognizer(_local, 16000)
        recognizer.AcceptWaveform(pcm)
        return json.loads(recognizer.FinalResult()).get("text", "").strip()

    if offline_required:
        raise RuntimeError("Offline voice needs a local Vosk model. No cloud fallback allowed.")

    # 3. Google Speech Recognition fallback
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    recognizer.operation_timeout = 8
    return recognizer.recognize_google(sr.AudioData(pcm, 16000, 2), language="en-IN").strip()


def listen(timeout=6, lang=None):
    wav = _record(timeout).getvalue()
    LAST_WAV["wav"] = wav
    try:
        return transcribe(wav)
    except Exception:
        return None


def process_utterance(text, last_wake_time=0.0, on_wake=None, quiet=False):
    """Route utterance against wake word rules and conversation window.
    Returns (handled: bool, new_wake_time: float).
    """
    low = text.casefold() if text else ""
    if not low:
        return False, last_wake_time
    if _SPEAKING.is_set() and low not in {"stop", "cancel"}:
        return False, last_wake_time
    # R04 fix: stop/cancel must ALWAYS interrupt running tasks, even after conversation window closes
    if low in {"stop", "cancel", "go to sleep", "sleep"}:
        if on_wake:
            on_wake(low, False)
        return True, 0.0
    match = re.search(r"\b(?:hey\s+|wake up\s+)?(?:lya|leya|liya)\b", low)
    active = (time.monotonic() - last_wake_time) < CONVERSATION_SECONDS
    if match:
        remainder = text[match.end():].strip(" ,.!?")
        now = time.monotonic()
        if on_wake:
            on_wake(remainder or "help", quiet)
        return True, now
    elif active:
        now = time.monotonic()
        if on_wake:
            on_wake(text, quiet)
        return True, now
    return False, last_wake_time


def wake_loop(on_wake, clap_enabled=False, stop_event=None, offline_required=False, on_ready=None):
    """Forward the recognized utterance exactly once; never start wake threads."""
    import sounddevice
    import numpy
    global _local
    path = os.environ.get("LYA_VOSK_MODEL", "")
    if not path:
        try:
            from storage.store import get_data_dir
            candidate = get_data_dir() / "models" / "vosk"
            if candidate.is_dir():
                path = str(candidate)
        except Exception:
            pass
    if path:
        import vosk
        if not os.path.isdir(path):
            raise RuntimeError(f"Vosk model path does not exist: {path}")
        if offline_required and _local is None:
            _local = vosk.Model(path)  # Validate before opening the microphone.
    else:
        if offline_required:
            raise RuntimeError("Offline voice needs a local Vosk model. Microphone not started.")
        try:
            import speech_recognition
        except ImportError:
            pass
    if on_ready:
        on_ready()
    last = 0.0
    while stop_event is None or not stop_event.is_set():
        try:
            wav = _record_stream()
            if wav is None:
                continue
            LAST_WAV["wav"] = wav.getvalue()
            text = transcribe(wav.getvalue(), offline_required=offline_required)
        except Exception:
            time.sleep(0.5)
            continue
        _, last = process_utterance(text, last, on_wake, QUIET["on"])
