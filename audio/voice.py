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
_engine=None
_mic_lock=threading.Lock()
_local=None
_CLAP_WAKE = object()

# --- Passive listener telemetry --------------------------------------------------
# Aggregate counters only: microphone audio is never stored, logged or transmitted.
LOUD_PEAK=700  # Same peak gate the command recorder uses before it starts a capture.
_MIC_TEST_MIN_SECONDS=1.0
_MIC_TEST_MAX_SECONDS=30.0
_STATS_LOCK=threading.Lock()
_STATS={"state":"stopped","device":None,"samples":0,"peak":0,"loud_blocks":0,"claps":0,
        "speaking_blocks":0,"state_since":None,"last_audio":None,"stream_open":False,"window":None}


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
    """Best-effort default input device name; never raises and never opens a stream."""
    try:
        import sounddevice as sd
        return str(sd.query_devices(kind="input").get("name","")).strip() or None
    except Exception:
        return None


def _reset_listener_stats():
    """Clear the aggregate counters without touching the listener itself."""
    with _STATS_LOCK:
        _STATS.update(samples=0,peak=0,loud_blocks=0,claps=0,speaking_blocks=0,
                      state_since=time.monotonic(),last_audio=None)


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
            "speaking_blocks":stats["speaking_blocks"],"mic_test":bool(testing)}


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
    return "hearing", ("Sound crossed the recorder's loudness gate, so a dead, muted or mis-selected "
                       "microphone is not the cause of the wake failure.")


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
        audio=sd.rec(int(seconds*16000),samplerate=16000,channels=1,dtype="int16")
        sd.wait()
    return _wav(audio.tobytes())


def _wav(pcm):
    buf=io.BytesIO()
    with wave.open(buf,"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm)
    buf.seek(0)
    return buf


def _record_stream(max_seconds=25,silence=0.8,thresh=700,stop_event=None,clap_enabled=False):
    import numpy as np
    import sounddevice as sd
    from collections import deque
    parts=[];pre=deque(maxlen=20);quiet=0;started=False
    clap = DoubleClap(int(os.environ.get('LYA_CLAP_THRESHOLD', '150'))) if clap_enabled else None
    if _SPEAKING.is_set():
        return None
    with _mic_lock, sd.RawInputStream(samplerate=16000,channels=1,dtype="int16") as stream:
        _note_state('listening', _input_device_name())
        try:
            deadline=time.monotonic()+max_seconds
            while time.monotonic()<deadline:
                if _SPEAKING.is_set() or (stop_event is not None and stop_event.is_set()):
                    return None
                data,overflow=stream.read(320);pcm=bytes(data)
                _note_audio(pcm,thresh)
                if overflow:
                    raise RuntimeError('Microphone input overflow')
                if clap is not None and clap.feed(pcm):
                    _note_clap()
                    return _CLAP_WAKE
                loud=float(np.abs(np.frombuffer(pcm,np.int16).astype(np.int32)).max())>thresh
                if loud and not started:
                    parts.extend(pre);started=True
                if started:
                    parts.append(pcm);quiet=0 if loud else quiet+1
                    if quiet>=silence/0.02:break
                else:pre.append(pcm)
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


def transcribe(wav_bytes, offline_required=True):
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
    match = WAKE_PATTERN.search(low)
    active = (time.monotonic() - last_wake_time) < CONVERSATION_SECONDS
    if match:
        remainder = text[match.end():].strip(" ,.!?")
        if remainder.casefold() == 'wake up':
            remainder = ''
        now = time.monotonic()
        if on_wake:
            on_wake(remainder or "wake up lya", quiet)
        return True, now
    elif active:
        now = time.monotonic()
        if on_wake:
            on_wake(text, quiet)
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
    with _mic_lock, sd.RawInputStream(samplerate=16000, channels=1, dtype='int16') as stream:
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


def wake_loop(on_wake, clap_enabled=False, stop_event=None, offline_required=True, on_ready=None, on_error=None):
    """Detect the wake phrase locally; only transcribe later commands remotely."""
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
    last = 0.0
    failures = 0
    _note_state('starting')
    while stop_event is None or not stop_event.is_set():
        if _SPEAKING.is_set():
            if last:
                last = time.monotonic()  # Give the user a full turn after LYA finishes.
            time.sleep(0.1)
            continue
        try:
            active = bool(last) and time.monotonic() - last < CONVERSATION_SECONDS
            if not active:
                if not _wait_for_wake(_local, clap_enabled, stop_event, on_ready):
                    return
                _, last = process_utterance('wake up lya', last, on_wake, QUIET['on'])
                failures = 0
                continue
            wav = _record_stream(max_seconds=25, silence=0.8, stop_event=stop_event,
                                 clap_enabled=clap_enabled)
            if stop_event is not None and stop_event.is_set():
                return
            if wav is None:
                continue
            if wav is _CLAP_WAKE:
                _, last = process_utterance('wake up lya', last, on_wake, QUIET['on'])
                failures = 0
                continue
            data = wav.getvalue()
            text = transcribe(data, offline_required=offline_required)
            failures = 0
        except Exception as error:
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
        _, last = process_utterance(text, last, on_wake, QUIET["on"])
    _note_state('stopped')
