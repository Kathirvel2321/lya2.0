"""One microphone reader, command forwarding, optional local transcription.
Set LYA_VOSK_MODEL to an existing Vosk model directory for offline voice.
Offline is the default. Remote recognition requires an explicit caller opt-in.
"""
import io
import os
import re
import threading
import time
import wave

WAKE_WORDS=("lya","leya","liya","laya","elya","elia","ilya","leah","lia","lea","leia","aliya","alia","layer")
# Vosk renders some Laya pronunciations as "layer"; this broad wake alias can
# also wake on that ordinary word. Waking never grants permission to act.
WAKE_PATTERN = re.compile(r"\b(?:" + "|".join(WAKE_WORDS) + r")\b", re.IGNORECASE)
CONVERSATION_SECONDS=45
QUIET={"on":False}
LAST_WAV={"wav":None}
_SPEAKING=threading.Event()
_THINKING=threading.Event()
COMMAND_SILENCE=2.5
COMMAND_MAX_SECONDS=120
_engine=None
_mic_lock=threading.Lock()
_local=None
_CLAP_WAKE = object()


class RecognitionUncertain(RuntimeError):
    """Do not send an uncertain or truncated spoken question to the brain."""
    def __init__(self, message, candidate=''):
        super().__init__(message)
        self.candidate = candidate  # Transient diagnostic only; excluded from error strings/logs.


class SpeechActivity:
    """Streaming state for the already-installed local Silero VAD (32ms frames)."""
    def __init__(self):
        import numpy as np
        from faster_whisper.vad import get_vad_model
        self.session = getattr(get_vad_model(), 'session', None)
        if self.session is None or {item.name for item in self.session.get_inputs()} != {'input', 'h', 'c'}:
            raise RuntimeError('Installed VAD does not support this streaming format.')
        self.pending = b''
        self.h = np.zeros((1, 1, 128), np.float32)
        self.c = np.zeros_like(self.h)
        self.context = np.zeros((1, 64), np.float32)
        self.active = False

    def feed(self, pcm):
        import numpy as np
        self.pending += pcm
        while len(self.pending) >= 1024:
            block, self.pending = self.pending[:1024], self.pending[1024:]
            samples = np.frombuffer(block, np.int16).astype(np.float32)[None, :] / 32768
            probability, self.h, self.c = self.session.run(
                None, {'input': np.concatenate([self.context, samples], axis=1),
                       'h': self.h, 'c': self.c})
            self.context = samples[:, -64:]
            self.active = float(probability.reshape(-1)[-1]) >= 0.5
        return self.active

# --- Passive listener telemetry --------------------------------------------------
# Aggregate counters only: microphone audio is never stored, logged or transmitted.
LOUD_PEAK=700  # Same peak gate the command recorder uses before it starts a capture.
_MIC_TEST_MIN_SECONDS=1.0
_MIC_TEST_MAX_SECONDS=30.0
_STATS_LOCK=threading.Lock()
_STATS={"state":"stopped","device":None,"samples":0,"peak":0,"loud_blocks":0,"claps":0,
        "speaking_blocks":0,"state_since":None,"last_audio":None,"stream_open":False,"window":None,
        "level":0.0}


def _note_state(state, device=None):
    """Record a listener lifecycle change. Raw audio and transcripts are never stored."""
    with _STATS_LOCK:
        _STATS["state"]=str(state)
        _STATS["state_since"]=time.monotonic()
        if device:
            _STATS["device"]=str(device)
        if state=="stopped":
            _STATS["stream_open"]=False
            _STATS["last_audio"]=None
        elif state=="listening":
            _STATS["stream_open"]=True


def _input_device_name():
    """Best-effort selected input device name; never opens a stream."""
    try:
        import sounddevice as sd
        return str(sd.query_devices(_input_device(sd), "input").get("name", "")).strip() or None
    except Exception:
        return None


def _input_device(sd):
    """Use Windows' native default input when available; otherwise PortAudio's default."""
    selected = os.environ.get('LYA_MICROPHONE', '').strip()
    if selected:
        matches = [(i, d) for i, d in enumerate(sd.query_devices())
                   if d['max_input_channels'] and d['name'] == selected]
        for i, device in matches:
            if sd.query_hostapis(device['hostapi'])['name'] == 'Windows WASAPI':
                return i
        if matches:
            return matches[0][0]
        raise RuntimeError('Selected microphone is unavailable. Choose a microphone from the LYA menu.')
    try:
        return next(api['default_input_device'] for api in sd.query_hostapis()
                    if api['name'] == 'Windows WASAPI' and api['default_input_device'] >= 0)
    except (StopIteration, KeyError, TypeError, OSError):
        return None


def _reset_listener_stats():
    """Clear the aggregate counters without touching the listener itself."""
    with _STATS_LOCK:
        _STATS.update(samples=0,peak=0,loud_blocks=0,claps=0,speaking_blocks=0,
                      state_since=time.monotonic(),last_audio=None,level=0.0)


def _note_audio(pcm, threshold=None, suppressed=False):
    """Fold one block of microphone audio into counters; returns the block RMS.

    Counting must never break listening, so a counter failure is swallowed and
    reported as 0.0. No sample, transcript or file is retained anywhere.
    """
    try:
        import numpy as np
        samples=np.frombuffer(pcm[:len(pcm)//2*2],np.int16)
        if not samples.size:
            return 0.0
        peak=int(np.abs(samples.astype(np.int32)).max())
        rms=float(np.sqrt(np.mean(samples.astype(np.float32)**2)))
    except Exception:
        return 0.0
    now=time.monotonic()
    with _STATS_LOCK:
        window=_STATS["window"]
        active=window is not None and not window["done"]
        limit=threshold if threshold is not None else (window["threshold"] if active else LOUD_PEAK)
        loud=peak>limit
        _STATS["samples"]+=int(samples.size)
        _STATS["peak"]=max(_STATS["peak"],peak)
        _STATS["loud_blocks"]+=1 if loud else 0
        _STATS["speaking_blocks"]+=1 if suppressed else 0
        _STATS["last_audio"]=now
        _STATS['level'] = 0.65 * _STATS['level'] + 0.35 * min(1.0, rms / 1800.0)
        if active:
            window["samples"]+=int(samples.size)
            window["blocks"]+=1
            window["peak"]=max(window["peak"],peak)
            window["loud_blocks"]+=1 if loud else 0
            window["rms_sum"]+=rms
            window["rms_min"]=rms if window["rms_min"] is None else min(window["rms_min"],rms)
            window["rms_max"]=max(window["rms_max"],rms)
            window["suppressed"]+=1 if suppressed else 0
    return rms


def _note_clap():
    """Count a detected double clap; the clap sound itself is never kept."""
    with _STATS_LOCK:
        _STATS["claps"]+=1
        window=_STATS["window"]
        if window is not None and not window["done"]:
            window["claps"]+=1


def listener_health():
    """Return aggregate listening facts the self-test and status command can report."""
    now=time.monotonic()
    with _STATS_LOCK:
        stats=dict(_STATS)
        window=stats["window"]
        testing=window is not None and not window["done"]
        state="testing" if testing else stats["state"]
        seconds=now-stats["state_since"] if stats["state_since"] else None
        idle=now-stats["last_audio"] if stats["last_audio"] else None
    return {"state":state,"device":stats["device"],"samples":stats["samples"],"peak":stats["peak"],
            "loud_blocks":stats["loud_blocks"],"claps":stats["claps"],
            "state_seconds":round(seconds,1) if seconds is not None else None,
            "idle_seconds":round(idle,1) if idle is not None else None,
            "listening":bool(stats["stream_open"]),"speaking":_SPEAKING.is_set(),
            "speaking_blocks":stats["speaking_blocks"],"mic_test":bool(testing),"level":stats['level']}


def mic_test_start(seconds=5.0, threshold=None):
    """Open a counting window on the live listener stream; never opens a second one."""
    try:
        seconds=float(seconds)
    except (TypeError, ValueError):
        seconds=5.0
    seconds=min(max(seconds,_MIC_TEST_MIN_SECONDS),_MIC_TEST_MAX_SECONDS)
    device=_input_device_name()
    with _STATS_LOCK:
        if device:
            _STATS["device"]=device
        _STATS["window"]={"started":time.monotonic(),"seconds":seconds,"done":False,
                          "device":_STATS["device"],
                          "threshold":LOUD_PEAK if threshold is None else int(threshold),
                          "samples":0,"blocks":0,"peak":0,"loud_blocks":0,"claps":0,"suppressed":0,
                          "rms_sum":0.0,"rms_min":None,"rms_max":0.0,
                          "listening":bool(_STATS["stream_open"])}
    return listener_health()


def _mic_test_verdict(report):
    """Name what the counted window showed; this is a heuristic, not a diagnosis."""
    if not report["listening"]:
        return "no-listener", ("The microphone listener was not running, so nothing could be counted. "
                               "Turn Voice wake on, then run this test again.")
    if not report["blocks"]:
        return "no-audio", "The listener held no audio blocks in this window, so nothing was measured."
    if not report["peak"]:
        return "silent", ("The microphone returned digital silence. Check the selected input device, the mute "
                          "switch and Windows microphone privacy settings.")
    if not report["loud_blocks"]:
        return "too-quiet", ("Sound arrived but never crossed the " + str(report["threshold"]) +
                             " peak gate the command recorder uses. Raise the input level or speak closer "
                             "to the microphone.")
    return "hearing", ("Sound crossed the recorder's loudness gate. It may be speech or background noise. "
                       "This does not verify the chosen microphone, voice clarity or recognized words.")


def mic_test_report():
    """Summarize the counted window; None when no self-test was started."""
    with _STATS_LOCK:
        window=_STATS["window"]
        if window is None:
            return None
        window["done"]=True
        report=dict(window)
    blocks=report["blocks"]
    report["elapsed"]=round(time.monotonic()-report.pop("started"),1)
    report.pop("done")
    report["rms_mean"]=round(report.pop("rms_sum")/blocks,1) if blocks else 0.0
    report["rms_min"]=round(report["rms_min"],1) if report["rms_min"] is not None else None
    report["rms_max"]=round(report["rms_max"],1)
    report["verdict"],report["detail"]=_mic_test_verdict(report)
    return report


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
_PLAYBACK_STOP = threading.Event()  # Set to cancel a queued/in-flight legacy utterance.


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
    # F4: keep the legacy engine rate and the neural tone mapping in one place.
    if _engine is None:
        try:
            import pyttsx3
            _engine = pyttsx3.init()
        except Exception:
            _engine = None
    if _engine is not None:
        try:
            _engine.setProperty('rate', rate)
        except Exception:
            pass
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
    return True


def stop_speaking():
    """Interrupt ongoing speech playback immediately."""
    _STOP_PLAYBACK.set()
    _PLAYBACK_STOP.set()
    with _playback_lock:
        if _playback_process is not None:
            _playback_process.kill()
    _SPEAKING.clear()


_playback_lock = threading.Lock()
_playback_process = None
_playback_thread = None


def speak(text, tone=None, voice_name=None, block=False, *args, **kwargs):
    """Legacy callers share the local renderer; never use online TTS implicitly.

    Non-blocking by default (F1): the synthesis runs on a single background
    worker thread and this call returns immediately. `block=True` keeps the
    old synchronous contract for the few callers that need it.
    """
    import json
    import subprocess
    import sys
    from pathlib import Path
    if QUIET['on'] or not str(text).strip():
        return
    tone = tone or _CURRENT_TONE.get('tone', 'neutral')
    style = {'happy': 'cheerful', 'excited': 'cheerful', 'sad': 'calm',
             'worried': 'calm'}.get(tone, tone or 'warm')
    payload = json.dumps(dict(text=str(text)[:1000], style=style)).encode('utf-8')

    if block:
        _speak_blocking(payload, subprocess, sys, Path)
        return

    # F1/F2: a single persistent worker thread owns playback, so repeated
    # legacy utterances queue sequentially and late requests supersede a
    # pending one without ever blocking the caller.
    global _playback_thread
    _PLAYBACK_STOP.clear()
    _SPEAKING.set()

    def work():
        try:
            _speak_blocking(payload, subprocess, sys, Path)
        except Exception:
            pass
        finally:
            if not _PLAYBACK_STOP.is_set():
                _SPEAKING.clear()

    thread = threading.Thread(target=work, name='lya-legacy-speak', daemon=True)
    _playback_thread = thread
    thread.start()


def _speak_blocking(payload, subprocess, sys, Path):
    """Run one synthesis+playback to completion. Called on the worker thread
    (or the caller's thread when block=True); never on a Qt thread."""
    global _playback_process
    with _playback_lock:
        if _playback_process is not None:
            _playback_process.kill()
        _STOP_PLAYBACK.clear()
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve().parents[1] / 'desktop' / 'setup_speech.py')],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        _playback_process = process
        _SPEAKING.set()
    try:
        process.communicate(payload, timeout=120)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
    finally:
        with _playback_lock:
            if _playback_process is process:
                _playback_process = None
                _SPEAKING.clear()


def _record(seconds):
    import sounddevice as sd
    with _mic_lock:
        audio=sd.rec(int(seconds*16000),samplerate=16000,channels=1,dtype="int16",
                     device=_input_device(sd))
        sd.wait()
    return _wav(audio.tobytes())


def _wav(pcm):
    buf=io.BytesIO()
    with wave.open(buf,"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm)
    buf.seek(0)
    return buf


def _record_stream(max_seconds=25,silence=0.8,thresh=700,stop_event=None,clap_enabled=False,
                   endpoint_model=None,on_state=None,use_vad=False):
    import numpy as np
    import sounddevice as sd
    from collections import deque
    parts=[];pre=deque(maxlen=50);quiet=0;started=False
    clap = DoubleClap(int(os.environ.get('LYA_CLAP_THRESHOLD', '150'))) if clap_enabled else None
    if _SPEAKING.is_set() or _THINKING.is_set():
        return None
    endpoint = None
    activity = None
    if use_vad:
        try:
            activity = SpeechActivity()
        except (ImportError, FileNotFoundError, RuntimeError):
            pass  # Portable fallback retains local Vosk speech gating.
    endpoint_quiet = None
    previous_partial = ''
    if endpoint_model is not None and activity is None:
        import json
        import vosk
        endpoint = vosk.KaldiRecognizer(endpoint_model, 16000)
    with _mic_lock, sd.RawInputStream(samplerate=16000,channels=1,dtype="int16",
                                      device=_input_device(sd)) as stream:
        _note_state('listening', _input_device_name())
        if on_state:
            on_state('listening')
        try:
            deadline=time.monotonic()+max_seconds
            while time.monotonic()<deadline:
                if (_SPEAKING.is_set() or _THINKING.is_set() or
                        (stop_event is not None and stop_event.is_set())):
                    return None
                data,overflow=stream.read(320);pcm=bytes(data)
                _note_audio(pcm,thresh)
                if overflow:
                    raise RuntimeError('Microphone input overflow')
                if clap is not None and clap.feed(pcm):
                    _note_clap()
                    return _CLAP_WAKE
                recognized = False
                if endpoint is not None:
                    if endpoint.AcceptWaveform(pcm):
                        recognized = bool(json.loads(endpoint.Result()).get('text', '').strip())
                        previous_partial = ''
                        if recognized:
                            endpoint_quiet = 0
                    else:
                        partial = json.loads(endpoint.PartialResult()).get('partial', '').strip()
                        recognized = bool(partial and partial != previous_partial)
                        previous_partial = partial
                        if recognized:
                            endpoint_quiet = None
                loud=float(np.abs(np.frombuffer(pcm,np.int16).astype(np.int32)).max())>thresh
                speech = activity.feed(pcm) if activity is not None else (recognized if endpoint is not None else loud)
                if speech and not started:
                    parts.extend(pre);started=True
                    if on_state:
                        on_state('hearing')
                if started:
                    parts.append(pcm)
                    speaking_now = speech if activity is not None else loud or recognized
                    quiet=0 if speaking_now else quiet+1
                    if quiet>=silence/0.02 and not recognized:break
                else:pre.append(pcm)
                # Allow a brief continuation after a finalized clause. Do not
                # submit the question at the first internal recognizer endpoint.
                if endpoint_quiet is not None:
                    endpoint_quiet += 1
                    if started and endpoint_quiet >= silence / 0.02:
                        break
            else:
                if parts:
                    raise RecognitionUncertain('Question exceeded the capture limit; repeat a shorter question.')
        finally:
            _note_state('stopped')
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


def transcribe(wav_bytes, offline_required=True, *, cloud_provider='groq', cancelled=None, on_provider=None):
    global _local
    local_only = offline_required() if callable(offline_required) else offline_required
    # 1. If not offline_required, try Groq Whisper Large v3 (multilingual, fast)
    if not local_only:
        if cloud_provider == 'nvidia':
            from audio import nvidia_asr
            permitted = (lambda: not offline_required()) if callable(offline_required) else True
            return nvidia_asr.transcribe(wav_bytes, remote_allowed=permitted,
                                        cancelled=cancelled, on_model=on_provider)
        if cloud_provider != 'groq':
            raise RuntimeError('Unknown remote speech recognizer. No audio sent.')
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not groq_key:
            try:
                from brain.mind import get_groq_key
                groq_key = get_groq_key()
            except Exception:
                pass
        if not groq_key:
            raise RuntimeError('Groq speech is not configured. No audio provider was contacted.')
        try:
            res = _transcribe_groq(wav_bytes, groq_key)
        except Exception:
            raise RuntimeError('Groq speech is unavailable. No other audio provider was contacted.') from None
        if not res:
            raise RecognitionUncertain('No clear question was recognized.')
        return res

    # Installed English Whisper handles whole questions; Vosk remains the wake/stop reader.
    # Do not substitute another engine's guess after an uncertain Whisper result.
    from audio import local_whisper
    engine = os.environ.get('LYA_COMMAND_ASR', 'vosk').strip().lower()
    if engine not in ('whisper', 'vosk'):
        raise RuntimeError('Unknown local command recognizer.')
    if engine == 'whisper':
        return local_whisper.transcribe(wav_bytes)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        pcm = wav.readframes(wav.getnframes())

    # 2. Local Vosk model (if installed)
    path = os.environ.get("LYA_VOSK_MODEL", "")
    if not path:
        try:
            from storage.store import get_data_dir
            for candidate in (get_data_dir() / "models" / "vosk",
                              get_data_dir() / "models" / "vosk-model-small-en-us-0.15"):
                if candidate.is_dir():
                    path = str(candidate)
                    break
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
        recognizer.SetWords(True)
        parts = []
        words = []
        for offset in range(0, len(pcm), 4000):
            if recognizer.AcceptWaveform(pcm[offset:offset + 4000]):
                result = json.loads(recognizer.Result())
                parts.append(result.get('text', ''))
                words.extend(result.get('result', []))
        result = json.loads(recognizer.FinalResult())
        parts.append(result.get('text', ''))
        words.extend(result.get('result', []))
        text = " ".join(part for part in parts if part).strip()
        confidence = [word['conf'] for word in words if 'conf' in word]
        # Confidence is a rejection heuristic, not proof that the words are right.
        if not text or (confidence and (min(confidence) < 0.45 or
                                       sum(confidence) / len(confidence) < 0.75)):
            raise RecognitionUncertain('Please repeat the question; local recognition was uncertain.', text)
        return text

    raise RuntimeError("Offline voice needs a local Vosk model. No cloud fallback allowed.")


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
    command = low.strip(' \t\r\n,.!?')
    if _SPEAKING.is_set() and command not in {"stop", "cancel"}:
        return False, last_wake_time
    # R04 fix: stop/cancel must ALWAYS interrupt running tasks, even after conversation window closes
    if command in {"stop", "cancel", "go to sleep", "sleep"}:
        if on_wake:
            on_wake(command, False)
        return True, 0.0
    match = WAKE_PATTERN.search(low)
    active = bool(last_wake_time) and (time.monotonic() - last_wake_time) < CONVERSATION_SECONDS
    if active:
        # Within a conversation the name belongs to the question, including all
        # context before it. Only a standalone wake/address is an acknowledgement.
        wake_only = re.fullmatch(r'\s*(?:(?:hey|please|wake\s+up)[\s,.!?]+)?' + WAKE_PATTERN.pattern +
                                 r'(?:[\s,.!?]+wake\s+up)?[\s,.!?]*', low)
        now = time.monotonic()
        if not wake_only and on_wake:
            on_wake(text, quiet)
        return True, now
    if match:
        remainder = text[match.end():].strip(" ,.!?")
        if remainder.casefold() == 'wake up':
            remainder = ''
        now = time.monotonic()
        if on_wake:
            on_wake(remainder or "wake up lya", quiet)
        return True, now
    return False, last_wake_time


class DoubleClap:
    """Two short impulses 0.18-0.8 seconds apart; audio is never retained."""
    def __init__(self, threshold=150):
        if not 100 <= threshold <= 20000:
            raise ValueError('LYA_CLAP_THRESHOLD must be between 100 and 20000')
        self.threshold = threshold
        self.elapsed = 0.0
        self.start = None
        self.first = None

    def feed(self, pcm):
        import numpy as np
        samples = np.frombuffer(pcm, np.int16).astype(np.float32)
        if not samples.size:
            return False
        now = self.elapsed
        self.elapsed += samples.size / 16000
        rms = float(np.sqrt(np.mean(samples * samples)))
        peak = float(np.abs(samples).max())
        # ponytail: acoustic heuristic can also hear knocks; tune the threshold,
        # use a trained sound classifier if real-room false wakes remain frequent.
        loud = rms >= self.threshold
        if loud:
            if self.start is None:
                self.start = now
                power = np.abs(np.fft.rfft(samples)) ** 2
                high = power[np.fft.rfftfreq(samples.size, 1 / 16000) >= 2000].sum()
                self.impulsive = peak >= 2.5 * rms and high > 0.45 * power.sum()
            return False
        if self.start is None:
            return False
        start, self.start = self.start, None
        if now - start > 0.12 or not self.impulsive:
            self.first = None
            return False
        if self.first is not None and 0.18 <= start - self.first <= 0.8:
            self.first = None
            return True
        self.first = start
        return False


def _wait_for_wake(model, clap_enabled, stop_event, on_ready):
    """Keep one local stream open; hear LYA's name anywhere, without a fixed phrase."""
    import json
    import sounddevice as sd
    import vosk
    names = ('liya', 'lia', 'leah', 'lea', 'leia', 'elia', 'ilya', 'aliya', 'alia', 'layer')
    grammar = json.dumps([context.format(name) for name in names
                          for context in ('{}', '[unk] {}', '{} [unk]', '[unk] {} [unk]')] + ['[unk]'])
    recognizer = vosk.KaldiRecognizer(model, 16000, grammar)
    clap = DoubleClap(int(os.environ.get('LYA_CLAP_THRESHOLD', '150'))) if clap_enabled else None
    with _mic_lock, sd.RawInputStream(samplerate=16000, channels=1, dtype='int16',
                                      device=_input_device(sd)) as stream:
        _note_state('listening', _input_device_name())
        if on_ready:
            on_ready()  # Ready means the actual microphone opened, not just the model.
        try:
            while stop_event is None or not stop_event.is_set():
                data, overflow = stream.read(320)
                pcm = bytes(data)
                # Counted even while LYA speaks (when recognition is suppressed), so a
                # silent or mis-selected microphone is still visible in the telemetry.
                _note_audio(pcm, suppressed=_SPEAKING.is_set())
                if stop_event is not None and stop_event.is_set():
                    return False
                if overflow:
                    raise RuntimeError('Microphone input overflow')
                if _SPEAKING.is_set():
                    recognizer.Reset()
                    if clap is not None:
                        clap = DoubleClap(clap.threshold)
                    continue
                if clap is not None and clap.feed(pcm):
                    _note_clap()
                    return True
                final = recognizer.AcceptWaveform(pcm)
                if not final:
                    continue  # Provisional aliases can turn ordinary speech into a false wake.
                result = json.loads(recognizer.Result())
                text = result.get('text', '')
                if WAKE_PATTERN.search(text):
                    return True
        finally:
            _note_state('stopped')
    return False


def _wait_for_interrupt(model, stop_event, on_wake, on_ready=None):
    """One local microphone reader hears only interruption while LYA is busy.

    Unrestricted recognition avoids forcing unrelated speech into a small
    command grammar. Echo cancellation is not implemented; headphones help.
    """
    import json
    import sounddevice as sd
    import vosk
    recognizer = vosk.KaldiRecognizer(model, 16000)
    previous = ''
    with _mic_lock, sd.RawInputStream(samplerate=16000, channels=1, dtype='int16',
                                      device=_input_device(sd)) as stream:
        _note_state('listening', _input_device_name())
        try:
            if on_ready:
                on_ready()
            while _SPEAKING.is_set() or _THINKING.is_set():
                if stop_event is not None and stop_event.is_set():
                    return
                data, overflow = stream.read(320)
                if stop_event is not None and stop_event.is_set():
                    return
                if overflow:
                    raise RuntimeError('Microphone input overflow')
                pcm = bytes(data)
                _note_audio(pcm, suppressed=True)
                final = recognizer.AcceptWaveform(pcm)
                result = json.loads(recognizer.Result() if final else recognizer.PartialResult())
                text = result.get('text' if final else 'partial', '').strip().casefold()
                if text in ('stop', 'cancel', 'stop speaking') and (final or text == previous):
                    if on_wake:
                        on_wake('stop', True)
                    return
                previous = text
        finally:
            _note_state('stopped')


def wake_loop(on_wake, clap_enabled=False, stop_event=None, offline_required=True, on_ready=None, on_error=None,
              on_state=None, on_retry=None, cloud_provider='groq', on_provider=None, cloud_only=False):
    """Detect wake locally; on_retry(candidate, paused) never dispatches uncertain words.

    Two uncertain turns return to local wake detection. Remote command
    transcription still requires offline_required=False. A callable privacy
    policy is checked after capture, immediately before transcription.
    """
    if cloud_provider not in ('groq', 'nvidia'):
        raise RuntimeError('Unknown remote speech recognizer. Listener not started.')
    import vosk
    global _local
    path = os.environ.get("LYA_VOSK_MODEL", "")
    if not path:
        try:
            from storage.store import get_data_dir
            for candidate in (get_data_dir() / "models" / "vosk",
                              get_data_dir() / "models" / "vosk-model-small-en-us-0.15"):
                if candidate.is_dir():
                    path = str(candidate)
                    break
        except Exception:
            pass
    if not path or not os.path.isdir(path):
        raise RuntimeError("Local wake model missing. Microphone not started.")
    if _local is None:
        _local = vosk.Model(path)  # Never stream ambient audio to a provider.
    from audio import local_whisper
    engine = os.environ.get('LYA_COMMAND_ASR', 'vosk').strip().lower()
    if engine == 'whisper' and not cloud_only:
        local_whisper.load(str(local_whisper.model_path()))  # Warm before microphone readiness.
    last = 0.0
    failures = 0
    uncertain_turns = 0
    _note_state('starting')
    while stop_event is None or not stop_event.is_set():
        try:
            if _SPEAKING.is_set() or _THINKING.is_set():
                if on_state:
                    on_state('speaking' if _SPEAKING.is_set() else 'thinking')
                _wait_for_interrupt(_local, stop_event, on_wake)
                if last:
                    last = time.monotonic()
                if stop_event is not None:
                    stop_event.wait(0.05)  # Let the UI consume an interruption signal.
                else:
                    time.sleep(0.05)
                continue
            active = bool(last) and time.monotonic() - last < CONVERSATION_SECONDS
            if not active:
                def ready():
                    if on_ready:
                        on_ready()
                    if on_state:
                        on_state('standby')
                if not _wait_for_wake(_local, clap_enabled, stop_event, ready):
                    return
                _, last = process_utterance('wake up lya', last, on_wake, QUIET['on'])
                failures = 0
                uncertain_turns = 0
                continue
            # Bound noise/dictation, but never forward a question chopped at the limit.
            wav = _record_stream(max_seconds=COMMAND_MAX_SECONDS,
                                 silence=3.0 if cloud_provider == 'nvidia' else COMMAND_SILENCE,
                                 stop_event=stop_event, clap_enabled=clap_enabled,
                                 endpoint_model=_local, on_state=on_state, use_vad=True)
            if stop_event is not None and stop_event.is_set():
                return
            if wav is None:
                continue
            if wav is _CLAP_WAKE:
                _, last = process_utterance('wake up lya', last, on_wake, QUIET['on'])
                failures = 0
                uncertain_turns = 0
                continue
            if on_state:
                on_state('transcribing')
            local_only = offline_required() if callable(offline_required) else offline_required
            if cloud_only and local_only:
                raise RecognitionUncertain('Private mode blocks online hearing. Please use text input.')
            if cloud_provider == 'nvidia' and not local_only:
                text = transcribe(wav.getvalue(), offline_required=offline_required,
                                  cloud_provider='nvidia', cancelled=stop_event, on_provider=on_provider)
            else:
                text = transcribe(wav.getvalue(), offline_required=local_only)
            if stop_event is not None and stop_event.is_set():
                return  # A slow decoder must not dispatch after voice was turned off.
            if not text.strip():
                raise RecognitionUncertain('No clear words were recognized.')
            failures = 0
            uncertain_turns = 0
        except RecognitionUncertain as error:
            if stop_event is not None and stop_event.is_set():
                return
            failures = 0
            uncertain_turns += 1
            paused = uncertain_turns >= 2
            if paused:
                last = 0.0  # Wait for a fresh wake instead of speaking retries forever.
            if on_retry:
                on_retry(error.candidate, paused)
            continue
        except Exception as error:
            if cloud_only:
                from audio.nvidia_asr import SpeechUnavailable
                if isinstance(error, (SpeechUnavailable, PermissionError)):
                    _note_state('stopped')
                    raise RuntimeError('Online hearing is unavailable or blocked. Use text or restart voice.') from None
            failures += 1
            if on_error:
                on_error(type(error).__name__)
            if failures >= 3:
                _note_state('stopped')
                raise RuntimeError('Voice input failed three times; check the microphone and restart Voice wake.') from error
            if stop_event is not None:
                stop_event.wait(0.5)
            else:
                time.sleep(0.5)
            continue
        # This turn began while awake. A long capture or decoder wait must not
        # expire its context and reinterpret an interior name as a new wake.
        last = time.monotonic()
        _, last = process_utterance(text, last, on_wake, QUIET["on"])
    _note_state('stopped')
