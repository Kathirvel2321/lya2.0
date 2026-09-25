"""LYA INITIALIZATION — the owner's first-run experience.

Replaces the flat "owner introduction" with a voice-led, camera-aware walkthrough
that reports the machine's real state instead of decorating it.

Design rules kept from the earlier milestones:
  * every status shown is produced by a real probe or a real measurement;
  * no invented telemetry, no fake "SECURE" claims;
  * nothing is captured, stored or transmitted without an explicit owner action;
  * rendering stops when the window is hidden or idle, and reduced motion wins;
  * every sensor is injected, so the whole flow runs headless in tests.

Sensors are used only when the owner starts them. Enrolment is committed through
`storage.store`, which refuses a second admin and writes only encrypted rows.
"""
from __future__ import annotations

import importlib.util
import queue
import secrets
import sys
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QProcess, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

ROOT = Path(__file__).resolve().parents[1]
if not __package__ and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # support activate-lya.cmd without PYTHONPATH
HELPER = ROOT / "security" / "HelloVerifier.exe"

CYAN = "#63e6ff"
CYAN_DIM = "#2b7f92"
AMBER = "#ffc861"
GREEN = "#7dffb0"
RED = "#ff7a7a"
INK = "#04080d"
PANEL = (7, 15, 24, 236)

FACE_PROMPTS = ("Hold still — look at the lens",
                "Turn your head left",
                "Turn your head right")
ACT_LABEL = "boss"


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


@dataclass(frozen=True)
class Layer:
    """One honestly probed subsystem."""
    key: str
    label: str
    ok: bool
    detail: str
    unlocks: str = ""


def layer(layers, key: str) -> Layer:
    for item in layers:
        if item.key == key:
            return item
    return Layer(key, key.upper(), False, "not probed")


def biometric_readiness(layers) -> tuple[bool, str]:
    """Installed pieces are not proof that biometric login is connected."""
    need = ("optics", "camera", "mic", "asr", "embed", "antispoof")
    missing = [layer(layers, key).label for key in need if not layer(layers, key).ok]
    if missing:
        return False, "not enrolled · missing " + ", ".join(missing)
    return False, "not enrolled · biometric verification is not connected"


def probe_layers() -> list[Layer]:
    """Probe the real machine. Opens no sensor, creates no secret, sends nothing."""
    layers: list[Layer] = []

    try:
        from storage import store  # noqa: F401
        core, core_detail = True, "brain + encrypted store importable"
    except Exception as exc:  # pragma: no cover - import guard
        core, core_detail = False, f"{type(exc).__name__}: {exc}"
    layers.append(Layer("core", "NEURAL CORE", core, core_detail,
                        "conversation and command routing"))

    try:
        from security import vault
        present = Path(vault.KEY_PATH).is_file()
        vault_ok = True
        vault_detail = ("DPAPI-protected key present" if present
                        else "key is created on the first protected write")
    except Exception as exc:
        vault_ok, vault_detail = False, f"{type(exc).__name__}: {exc}"
    layers.append(Layer("vault", "ENCRYPTION VAULT", vault_ok, vault_detail,
                        "encrypted notes, memory and templates"))

    try:
        from storage.store import get_data_dir
        target = Path(get_data_dir())
        store_ok, store_detail = target.is_dir(), f"{target} · person-scoped SQLite"
    except Exception as exc:
        store_ok, store_detail = False, f"{type(exc).__name__}: {exc}"
    layers.append(Layer("store", "SECURE STORE", store_ok, store_detail,
                        "your admin profile and private memory"))

    optics_ok, optics_detail = False, "vision models not verified"
    try:
        from vision import scan
        optics_ok = scan.models_ready()
        if optics_ok:
            optics_detail = "YuNet + NanoDet present and hash-verified"
    except Exception as exc:
        optics_detail = f"{type(exc).__name__}: {exc}"
    layers.append(Layer("optics", "OPTIC ARRAY", optics_ok, optics_detail,
                        "live face presence scan — presence, not identity"))

    cv_ok = _module_available("cv2")
    layers.append(Layer("camera", "CAMERA RUNTIME", cv_ok,
                        "OpenCV available" if cv_ok else "OpenCV (cv2) missing",
                        "camera preview and face detection"))

    mic_ok = _module_available("sounddevice")
    layers.append(Layer("mic", "MICROPHONE", mic_ok,
                        "sounddevice available" if mic_ok else "sounddevice missing",
                        "voice calibration and live waveform"))

    tts_ok = _module_available("piper") and _module_available("onnxruntime")
    layers.append(Layer("tts", "VOICE OUTPUT", tts_ok,
                        "Piper engine installed; playback unverified" if tts_ok
                        else "Piper voices unavailable — text only",
                        "LYA speaks every step"))

    asr_ok = False
    asr_detail = "no spoken-code verifier is connected to this flow"
    layers.append(Layer("asr", "SPEECH RECOGNITION", asr_ok, asr_detail,
                        "spoken-code challenge for voice enrolment"))

    embed_ok = False
    layers.append(Layer("embed", "FACE EMBEDDING", embed_ok,
                        "no face-template encoder is connected to this flow",
                        "encrypted ArcFace template for recognition"))

    anti_ok = False
    layers.append(Layer("antispoof", "ANTI-SPOOF LAYER", anti_ok,
                        "no liveness verifier is connected to this flow",
                        "live face challenge verification"))

    hello_ok = HELPER.is_file()
    layers.append(Layer("hello", "WINDOWS CHECKPOINT", hello_ok,
                        "helper found; Windows proof not run" if hello_ok
                        else "run security\\build-hello.cmd",
                        "the proof that creates your admin profile"))
    return layers


# --------------------------------------------------------------- measurements

def measure_wav(wav_bytes: bytes) -> dict:
    """Real numbers about a recorded clip. Never invents a quality score."""
    if not wav_bytes:
        return {"seconds": 0.0, "rms": 0.0, "peak": 0.0, "clipped": False}
    with wave.open(__import__("io").BytesIO(wav_bytes), "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
        seconds = w.getnframes() / float(rate or 1)
    import numpy as np
    samples = np.frombuffer(frames, np.int16).astype(np.float64) / 32768.0
    if samples.size == 0:
        return {"seconds": seconds, "rms": 0.0, "peak": 0.0, "clipped": False}
    peak = float(np.max(np.abs(samples)))
    return {"seconds": round(seconds, 2),
            "rms": round(float(np.sqrt(np.mean(samples ** 2))), 4),
            "peak": round(peak, 4), "clipped": bool(peak >= 0.99)}


def voiceprint_vector(wav_bytes: bytes):
    """The numpy-only log-spectrum voiceprint. Returns None when unusable."""
    try:
        from audio import voice_auth
        return voice_auth._voiceprint(voice_auth._wav_bytes_to_float(wav_bytes))
    except Exception:
        return None


def wav_from_pcm(samples, rate: int = 16000) -> bytes:
    import io
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            int(max(-1.0, min(1.0, v)) * 32767).to_bytes(2, "little", signed=True)
            for v in samples))
    return buffer.getvalue()


# ------------------------------------------------------------------- sensors

class CameraWorker:
    """Newest-frame camera reader. Frames stay in RAM and are never written."""

    def __init__(self, index: int = 0, width: int = 640, height: int = 480):
        self.index, self.width, self.height = index, width, height
        self.frames: queue.Queue = queue.Queue(maxsize=2)
        self.reading, self.face_count = False, 0
        self._thread = None
        self._stop = threading.Event()

    def start(self) -> bool:
        if self.reading:
            return True
        try:
            import cv2
        except ImportError:
            return False
        camera = cv2.VideoCapture(self.index)
        if not camera.isOpened():
            camera.release()
            return False
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.reading = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(camera,), daemon=True)
        self._thread.start()
        return True

    def _loop(self, camera):
        import cv2
        cv2.setNumThreads(2)
        engine, last = None, 0.0
        try:
            while not self._stop.is_set():
                ok, frame = camera.read()
                if not ok:
                    time.sleep(0.06)
                    continue
                now = time.monotonic()
                faces = []
                if engine is None and now - last > 0.5:
                    last = now
                    try:
                        from vision.scan import VisionEngine
                        engine = VisionEngine(self.width, self.height)
                    except Exception:
                        engine = None
                if engine is not None and now - last >= 0.5:
                    last = now
                    try:
                        faces = engine.analyze(frame).get("faces", [])
                    except Exception:
                        faces = []
                self.face_count = len(faces)
                try:
                    self.frames.put_nowait((frame, faces))
                except queue.Full:
                    try:
                        self.frames.get_nowait()
                        self.frames.put_nowait((frame, faces))
                    except queue.Empty:
                        pass
                self._stop.wait(0.06)  # cap preview work near 16 fps on a laptop
        finally:
            camera.release()
            self.reading = False

    def newest(self):
        latest = None
        while True:
            try:
                latest = self.frames.get_nowait()
            except queue.Empty:
                return latest

    def stop(self):
        self._stop.set()
        self.reading = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)


class MicWorker:
    """Live level meter plus a bounded recording. Nothing is written to disk."""

    def __init__(self, rate: int = 16000):
        self.rate, self.level, self.recording = rate, 0.0, False
        self.ticks: queue.Queue = queue.Queue(maxsize=8)
        self._stream, self._buffer = None, []

    def start_meter(self) -> bool:
        if self._stream is not None:
            return True
        try:
            import sounddevice as sd
        except ImportError:
            return False
        try:
            self._stream = sd.InputStream(samplerate=self.rate, channels=1,
                                          dtype="float32", blocksize=1600,
                                          callback=self._meter)
            self._stream.start()
            return True
        except Exception:
            self._stream = None
            return False

    def _meter(self, indata, frames, time_info, status):  # pragma: no cover - device
        import numpy as np
        self.level = float(np.sqrt(np.mean(np.square(indata[:, 0]))))
        if self.recording:
            self._buffer.extend(indata[:, 0].tolist())
            try:
                self.ticks.put_nowait(len(self._buffer) / float(self.rate))
            except queue.Full:
                pass

    def record(self, seconds: float = 3.5) -> bytes:
        """Blocking capture; call from a worker thread, never the Qt thread."""
        if not self.start_meter():
            return b""
        self.recording, self._buffer = True, []
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            time.sleep(0.05)
        self.recording = False
        clip = wav_from_pcm(self._buffer, self.rate)
        self._buffer = []
        return clip

    def progress(self) -> float:
        try:
            return float(self.ticks.get_nowait())
        except queue.Empty:
            return 0.0

    def stop(self):
        self.recording = False
        self._buffer = []
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


# --------------------------------------------------------------- copy / voice

ACTS = ("BOOT", "IDENTITY", "OPTICS", "VOCAL", "VAULT", "ONLINE")

SCRIPT = {
    "IDENTITY": ("Welcome, {salutation}. I'm LYA. Tell me your name, and I'll guide you "
                 "through your local admin setup."),
    "OPTICS": ("Start the camera when you're ready. I'll check that a face is in frame. "
               "This does not identify you, and I will not keep a picture."),
    "VOCAL": ("Press Record to check your microphone. Read the number on screen. "
              "I can measure the sound, but I cannot verify the spoken words yet."),
    "VAULT": ("Now verify with Windows. Your PIN stays with Windows. After that, "
              "you decide whether to create your encrypted admin profile."),
    "ONLINE": ("Your local admin profile is ready, {salutation}. "
               "Face and voice sign-in are not enrolled yet."),
}

GREETING = "Welcome, {salutation}. Your local admin profile is ready. Face and voice sign-in are not enrolled yet."


class HudCanvas(QWidget):
    """The painted surface. Every pixel is driven by a real reading."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layers: list[Layer] = []
        self.act_index = 0
        self.boot_lines: list[tuple[str, str, bool]] = []
        self.boot_shown = 0
        self.headline, self.caption, self.badge = "", "", ""
        self.spoken_caption = ""
        self.progress = 0.0
        self.wave: list[float] = []
        self.level = 0.0
        self.video = None            # QImage or None
        self.faces: list = []
        self.phase = 0.0             # animation phase, advanced only while active
        self.reduced = False
        self.running = False
        self.sprite = QPixmap(str(ROOT / "desktop" / "assets" / "obsidian-baked.png"))
        if not self.sprite.isNull():
            self.sprite = self.sprite.scaled(200, 230, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._advance)

    # -- animation control: nothing loops when the window is idle or hidden ----
    def _advance(self):
        if not self.reduced:
            self.phase = (self.phase + 0.03) % (2 * 3.14159265)
        self.update()

    def set_active(self, active: bool):
        self.running = bool(active)
        if self.running:
            self.timer.start()
        else:
            self.timer.stop()

    def hideEvent(self, event):
        self.set_active(False)
        super().hideEvent(event)

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Segoe UI", 10))
        w, h = self.width(), self.height()
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0.0, QColor(9, 18, 30))
        sky.setColorAt(0.55, QColor(5, 11, 18))
        sky.setColorAt(1.0, QColor(3, 6, 10))
        p.fillRect(0, 0, w, h, QBrush(sky))
        self._grid(p, w, h)
        self._core(p, w, h)
        self._video(p, w, h)
        self._waveform(p, w, h)
        self._rail(p, w, h)
        self._ledger(p, w, h)
        self._footer(p, w, h)

    def _grid(self, p, w, h):
        p.setPen(QPen(QColor(99, 230, 255, 35), 1))
        p.drawLine(28, 34, w - 28, 34)
        p.drawLine(28, h - 24, w - 28, h - 24)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(QPen(QColor(160, 233, 248), 1))
        p.drawText(QRectF(32, 9, 260, 20), Qt.AlignmentFlag.AlignLeft,
                   "LYA  /  OWNER INITIALIZATION")
        p.setPen(QPen(QColor(119, 153, 170), 1))
        p.drawText(QRectF(w - 220, 9, 188, 20), Qt.AlignmentFlag.AlignRight,
                   f"{self.act_index + 1:02d}  /  {len(ACTS):02d}")

    def _core(self, p, w, h):
        cx, cy = w * 0.5, h * 0.44
        radius = min(w, h) * 0.20
        if not self.reduced and self.running:
            p.setPen(QPen(QColor(99, 230, 255, 70), 1))
            p.drawEllipse(QPointF(cx, cy), radius * 1.30, radius * 1.30)
            p.setPen(QPen(QColor(99, 230, 255, 34), 1))
            p.drawEllipse(QPointF(cx, cy), radius * 1.52, radius * 1.52)
            if self.video is None:          # radar sweep only when not on camera
                import math
                a = self.phase
                p.setPen(QPen(QColor(99, 230, 255, 120), 2))
                p.drawArc(QRectF(cx - radius * 1.52, cy - radius * 1.52,
                                 radius * 3.04, radius * 3.04),
                          int(math.degrees(a) * 16), 32 * 16)
        p.setBrush(QBrush(QColor(10, 26, 38, 220)))
        p.setPen(QPen(QColor(99, 230, 255, 150), 1))
        p.drawEllipse(QPointF(cx, cy), radius, radius)
        if self.video is None and not self.sprite.isNull():
            p.setOpacity(0.96)
            sw, sh = self.sprite.width() * 0.78, self.sprite.height() * 0.78
            p.drawPixmap(QRectF(cx - sw / 2, cy - sh / 2, sw, sh), self.sprite,
                         QRectF(self.sprite.rect()))
            p.setOpacity(1.0)
        arm = radius * 1.16
        p.setPen(QPen(QColor(99, 230, 255, 210), 2))
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            p.drawLine(QPointF(cx + dx * arm, cy + dy * arm - dy * arm * 0.30),
                       QPointF(cx + dx * arm, cy + dy * arm))
            p.drawLine(QPointF(cx + dx * arm, cy + dy * arm),
                       QPointF(cx + dx * arm - dx * arm * 0.30, cy + dy * arm))
        if self.progress > 0.0:
            p.setPen(QPen(QColor(43, 127, 146), 1))
            p.drawArc(QRectF(cx - radius * 1.36, cy - radius * 1.36,
                             radius * 2.72, radius * 2.72), 0, 360 * 16)
            p.setPen(QPen(QColor(99, 230, 255, 255), 3))
            p.drawArc(QRectF(cx - radius * 1.36, cy - radius * 1.36,
                             radius * 2.72, radius * 2.72),
                      90 * 16, -int(360 * 16 * min(1.0, self.progress)))

    def _video(self, p, w, h):
        """Camera takes the hero position while an explicit scan is running."""
        if self.video is None:
            return
        vw, vh = int(w * 0.38), int(h * 0.44)
        x, y = int(w * 0.5 - vw / 2), int(h * 0.44 - vh / 2)
        p.setOpacity(0.92)
        p.drawImage(QRectF(x, y, vw, vh), self.video)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor(99, 230, 255, 120), 1))
        p.drawRect(QRectF(x, y, vw, vh))
        sx, sy = vw / max(1, self.video.width()), vh / max(1, self.video.height())
        p.save()
        p.setClipRect(QRectF(x, y, vw, vh))
        for box in self.faces[:4]:
            bx, by = x + box[0] * sx, y + box[1] * sy
            bw, bh = (box[2] - box[0]) * sx, (box[3] - box[1]) * sy
            p.setPen(QPen(QColor(125, 255, 176, 220), 1))
            p.drawRect(QRectF(bx, by, bw, bh))
        p.restore()
        p.fillRect(QRectF(x, y + vh - 24, vw, 24), QColor(4, 10, 16, 220))
        p.setPen(QPen(QColor(232, 250, 255, 220), 1))
        font = QFont(p.font())
        font.setPointSize(7)
        p.setFont(font)
        p.drawText(QRectF(x + 10, y + vh - 22, vw - 20, 18), Qt.AlignmentFlag.AlignLeft,
                   f"OPTIC  /  {len(self.faces)} FACE(S)  /  NOT STORED")
        p.setFont(QFont())

    def _waveform(self, p, w, h):
        if not self.wave:
            return
        x0, y0, ww, hh = w * 0.5 - w * 0.18, h * 0.905, w * 0.36, 40
        p.setPen(QPen(QColor(99, 230, 255, 40), 1))
        p.drawLine(QPointF(x0, y0 + hh / 2), QPointF(x0 + ww, y0 + hh / 2))
        p.setPen(QPen(QColor(99, 230, 255, 220), 2))
        count = len(self.wave)
        if count < 2:
            return
        step = ww / (count - 1)
        prev = None
        for i, value in enumerate(self.wave):
            px = x0 + i * step
            py = y0 + hh / 2 - max(1.0, min(1.0, value)) * hh / 2
            if prev:
                p.drawLine(QPointF(prev[0], prev[1]), QPointF(px, py))
            prev = (px, py)

    def _rail(self, p, w, h):
        x, top, gap = 30, 60, 62
        font = QFont(p.font())
        font.setPointSize(8)
        p.setFont(font)
        p.setPen(QPen(QColor(43, 127, 146, 200), 1))
        p.drawLine(QPointF(x, top), QPointF(x, top + gap * (len(ACTS) - 1)))
        for i, act in enumerate(ACTS):
            y = top + gap * i
            done = i < self.act_index
            current = i == self.act_index
            color = QColor(GREEN) if done else (QColor(CYAN) if current else QColor(60, 80, 92))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(x, y), 4.5 if current else 3.0,
                          4.5 if current else 3.0)
            p.setPen(QPen(color if current else QColor(120, 150, 165, 160), 1))
            p.drawText(QRectF(x + 14, y - 9, 120, 18), Qt.AlignmentFlag.AlignLeft, act)
        p.setFont(QFont())

    def _ledger(self, p, w, h):
        x = w - 250
        y = 83
        relevant = {
            0: ("core", "vault", "store", "tts", "hello"),
            1: ("core", "vault", "hello"),
            2: ("optics", "camera", "embed", "antispoof"),
            3: ("mic", "tts", "asr"),
            4: ("vault", "store", "hello"),
            5: ("core", "vault", "store", "hello"),
        }[self.act_index]
        font = QFont(p.font())
        font.setPointSize(8)
        p.setFont(font)
        p.setPen(QPen(QColor(120, 150, 165, 190), 1))
        p.drawText(QRectF(x, y - 27, 220, 16), Qt.AlignmentFlag.AlignLeft,
                   "CONNECTION CHECK")
        for key in relevant:
            item = layer(self.layers, key)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(GREEN) if item.ok else QColor(AMBER)))
            p.drawEllipse(QPointF(x + 4, y), 3, 3)
            p.setPen(QPen(QColor(214, 240, 248) if item.ok else QColor(200, 170, 120), 1))
            p.drawText(QRectF(x + 14, y - 8, 226, 16), Qt.AlignmentFlag.AlignLeft,
                       f"{item.label}  {'FOUND' if item.ok else 'NOT CONNECTED'}")
            y += 26
        p.setFont(QFont())

    def _footer(self, p, w, h):
        font = QFont(p.font())
        font.setPointSize(21)
        font.setWeight(QFont.Weight.Light)
        p.setFont(font)
        p.setPen(QPen(QColor(238, 250, 255), 1))
        p.drawText(QRectF(160, h - 122, w - 320, 38), Qt.AlignmentFlag.AlignCenter,
                   self.headline)
        font.setPointSize(10)
        p.setFont(font)
        p.setPen(QPen(QColor(140, 180, 196), 1))
        p.drawText(QRectF(165, h - 83, w - 330, 48),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                   self.spoken_caption or self.caption)
        p.setPen(QPen(QColor(99, 230, 255, 210), 1))
        p.drawText(QRectF(32, h - 19, w - 64, 16), Qt.AlignmentFlag.AlignLeft, self.badge)
        p.setFont(QFont())


def _row(*widgets):
    from PySide6.QtWidgets import QHBoxLayout as _H
    holder = QWidget()
    line = _H(holder)
    line.setContentsMargins(0, 0, 0, 0)
    line.setSpacing(8)
    for widget in widgets:
        line.addWidget(widget)
    return holder


def _setup_speech(parent):
    """Reuse the reviewed Piper speech path; text-only when it is unavailable."""
    try:
        from desktop.setup_speech import SetupSpeech
    except ImportError:  # pragma: no cover - alternate import path
        try:
            from setup_speech import SetupSpeech
        except Exception:
            return None
    try:
        return SetupSpeech(parent)
    except Exception:  # pragma: no cover - voices missing
        return None


class ActivationDialog(QDialog):
    """The owner's first run: real probes, real sensors, real consent."""

    authenticated = Signal(object)

    def __init__(self, reduced_motion=False, camera=None, mic=None, db_path=None):
        super().__init__()
        self.reduced = reduced_motion
        self.camera = camera if camera is not None else CameraWorker()
        self.mic = mic if mic is not None else MicWorker()
        self.db_path = db_path
        self.setWindowTitle("LYA - initialization")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.resize(1000, 760)
        self.setMinimumSize(850, 650)
        self.setStyleSheet("QDialog{background:#08111a;color:#eaf4f8;font:14px 'Segoe UI';}")

        self.layers = probe_layers()
        self.ready, self.reason = biometric_readiness(self.layers)
        self.act = 0
        self.salutation = ACT_LABEL
        self.face_samples, self.voice_clips, self.voice_codes = [], [], []
        self.verified_until = 0.0
        self.verified_name = ""
        self.proof_nonce = ""
        self.hello_failure = ""
        self.created = None
        self.closing = False
        self.speaking = False
        self.busy = False
        self._recording = False
        self._record_done = threading.Event()
        self._record_clip = b""
        self.pump = QTimer(self)
        self.pump.timeout.connect(self._pump)

        self.canvas = HudCanvas(self)
        self.canvas.layers = self.layers
        self.canvas.reduced = reduced_motion

        from PySide6.QtWidgets import QComboBox
        self.pages = QStackedWidget(self)
        self.pages.setStyleSheet("QStackedWidget{background:#0a1520;border-top:1px solid #244351;}")
        self._build_pages(QComboBox)

        bar = QHBoxLayout()
        self.close_btn = self._button("Close", self.reject, quiet=True)
        self.back = self._button("Back", lambda: self.go(-1), quiet=True)
        self.next = self._button("Begin", lambda: self.go(1), primary=True)
        self.voice_toggle = self._button("Voice on", self.toggle_voice, quiet=True)
        self.voice_toggle.setCheckable(True)
        self.voice_toggle.setChecked(True)
        self.replay = self._button("Say again", self.say, quiet=True)
        for widget in (self.close_btn, self.back, self.voice_toggle, self.replay, self.next):
            bar.addWidget(widget)
        self.bar = QWidget(self)
        self.bar.setStyleSheet("background:#08111a;border-top:1px solid #1c3745;")
        self.bar.setLayout(bar)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.canvas, 1)
        outer.addWidget(self.pages, 0)
        outer.addWidget(self.bar, 0)

        self.speech = _setup_speech(self)
        if self.speech is not None:
            self.speech.speaking.connect(self._speaking)
            self.speech.unavailable.connect(self._speech_missing)
            self.speech.caption.connect(self._speech_caption)
        self.process = QProcess(self)
        self.process.finished.connect(self._hello_done)
        self.process.errorOccurred.connect(self._hello_failed)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self._hello_timeout)

        self.boot_lines = [(item.label, item.detail, item.ok) for item in self.layers]
        self.boot_lines.append(("SETUP CHECK COMPLETE",
                                "continue to owner setup; unavailable parts remain locked", True))
        self.boot_timer = QTimer(self)
        self.boot_timer.setInterval(120)
        self.boot_timer.timeout.connect(self._boot_step)
        self.canvas.boot_lines = self.boot_lines
        self.render()
        self._sync()

    # ------------------------------------------------------------------- chrome
    @staticmethod
    def _button(label, slot, primary=False, quiet=False):
        button = QPushButton(label)
        button.setAutoDefault(False)
        if primary:
            button.setObjectName("primary")
        button.setStyleSheet(
            "QPushButton{background:#11222f;color:#d9eef5;border:1px solid #315668;"
            "border-radius:10px;padding:11px 18px;font-size:13px;}"
            "QPushButton:hover{border-color:#72d9ed;background:#173345;}"
            "QPushButton#primary{background:#0f4f63;color:#f2feff;border:1px solid #2f8fa8;}"
            "QPushButton:disabled{color:#4a6572;border-color:#162a34;}")
        button.clicked.connect(slot)
        return button

    @staticmethod
    def _label(text, size=9, color="#8eb4c2"):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color:{color};font-size:{max(13, size)}px;")
        return label

    def _build_pages(self, combo_cls):
        def page():
            widget = QWidget()
            widget.setStyleSheet("QWidget{background:#0a1520;} QLabel{background:transparent;}")
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(24, 6, 24, 10)
            layout.setSpacing(6)
            self.pages.addWidget(widget)
            return layout

        boot = page()
        self.skip_boot = self._button("Skip boot", self._boot_finish, quiet=True)
        boot.addWidget(self.skip_boot)
        boot.addStretch()

        ident = page()
        row = QHBoxLayout()
        self.salutation_box = combo_cls()
        for option in ("boss", "sir", "ma'am", "friend"):
            self.salutation_box.addItem(option)
        self.salutation_box.setStyleSheet(
            "background:#0d2230;color:#cfeaf2;border:1px solid #1d4c5c;"
            "border-radius:8px;padding:6px;")
        self.name = QLineEdit()
        self.name.setPlaceholderText("your name")
        self.name.setStyleSheet(
            "background:#0d2230;color:#eafcff;border:1px solid #2f8fa8;"
            "border-radius:8px;padding:7px;")
        self.name.setAccessibleName("Display name")
        row.addWidget(self._label("I address you as", 8))
        row.addWidget(self.salutation_box)
        row.addWidget(self._label("and your name is", 8))
        row.addWidget(self.name, 1)
        ident.addLayout(row)
        self.salutation_box.currentTextChanged.connect(self._salutation_changed)
        self.name.textChanged.connect(self._name_changed)

        optics = page()
        self.optics_status = self._label("camera is off")
        self.camera_toggle = self._button("Start camera", self._toggle_camera)
        self.capture_face = self._button("Capture sample", self._take_face)
        optics.addWidget(self._label(
            "Face presence only - no identity match, no stored image", 8))
        optics.addWidget(_row(self.optics_status, self.camera_toggle, self.capture_face))

        vocal = page()
        self.vocal_status = self._label("microphone is off")
        self.code_label = self._label("-", 14, CYAN)
        self.record = self._button("Record sample", self._take_voice)
        vocal.addWidget(self._label("Speak the number aloud when the meter moves", 8))
        vocal.addWidget(self.code_label)
        vocal.addWidget(_row(self.vocal_status, self.record))

        vault = page()
        self.vault_status = self._label("no proof yet")
        self.verify = self._button("Verify with Windows", self._hello, primary=True)
        self.consent = QCheckBox(
            "Create my encrypted admin profile on this Windows account")
        self.consent.setStyleSheet("color:#cfeaf2;")
        self.consent.setAccessibleName("Confirm local admin profile creation")
        vault.addWidget(self._label("Your PIN stays with Windows. LYA never sees it.", 8))
        vault.addWidget(_row(self.vault_status, self.verify))
        vault.addWidget(self.consent)

        online = page()
        self.online_status = self._label("")
        online.addStretch()
        online.addWidget(self.online_status, 1)
        online.addStretch()

        self.consent.toggled.connect(self._sync)

    # ------------------------------------------------------------------ render
    def render(self):
        canvas, act = self.canvas, ACTS[self.act]
        canvas.act_index = self.act
        canvas.boot_shown = canvas.boot_shown
        if act == "BOOT":
            total = max(1, len(self.boot_lines))
            shown = canvas.boot_shown
            label, detail, ok = (self.boot_lines[min(shown, total - 1)]
                                 if shown < total else ("", "", True))
            canvas.headline = "CHECKING CONNECTIONS" if shown < total else "SETUP CHECK COMPLETE"
            canvas.caption = detail or "all subsystems reported"
            canvas.badge = f"SUBSYSTEMS {min(shown, total)}/{total} · {'FOUND' if ok else 'NEEDS SETUP'}"
            canvas.progress = min(1.0, shown / total)
        elif act == "IDENTITY":
            who = self.name.text().strip()
            canvas.headline = f"Welcome, {self.salutation}."
            canvas.caption = (f"I will call you {who}." if who
                              else SCRIPT["IDENTITY"].format(salutation=self.salutation))
            canvas.badge = "ACT 02 / IDENTITY"
            canvas.progress = 1.0 if who else 0.0
        elif act == "OPTICS":
            canvas.headline = "Let me see you"
            canvas.caption = (FACE_PROMPTS[min(len(self.face_samples), 2)]
                              + "  ·  face presence only")
            canvas.badge = f"SAMPLES {len(self.face_samples)}/3 · NOT AN IDENTITY MATCH"
            canvas.progress = min(1.0, len(self.face_samples) / 3.0)
        elif act == "VOCAL":
            canvas.headline = "Let me hear you"
            canvas.caption = "Press Record, then say the six digits aloud · microphone check only"
            canvas.badge = f"CLIPS {len(self.voice_clips)}/3 · MICROPHONE PATH ONLY"
            canvas.progress = min(1.0, len(self.voice_clips) / 3.0)
        elif act == "VAULT":
            canvas.headline = "Secure vault"
            canvas.caption = SCRIPT["VAULT"]
            canvas.badge = ("WINDOWS CHECKPOINT PASSED"
                            if time.monotonic() < self.verified_until
                            else "WINDOWS CHECKPOINT PENDING")
            canvas.progress = 1.0 if time.monotonic() < self.verified_until else 0.0
        else:
            canvas.headline = f"Welcome, {self.salutation}."
            canvas.caption = SCRIPT["ONLINE"].format(salutation=self.salutation)
            canvas.badge = "BIOMETRICS · " + self.reason.upper()
            canvas.progress = 1.0
        canvas.update()

    def _sync(self):
        act, name = ACTS[self.act], self.name.text().strip()
        verified = time.monotonic() < self.verified_until and name == self.verified_name
        self.back.setEnabled(self.act > 0 and not self.busy)
        self.next.setText({"BOOT": "Begin", "IDENTITY": "Continue", "OPTICS": "Continue",
                           "VOCAL": "Continue", "VAULT": "Create admin",
                           "ONLINE": "Finish"}[act])
        enabled = {"BOOT": self.canvas.boot_shown >= len(self.boot_lines),
                   "IDENTITY": bool(name), "OPTICS": True, "VOCAL": True,
                   "VAULT": bool(verified and self.consent.isChecked()),
                   "ONLINE": True}[act]
        self.next.setEnabled(bool(enabled) and not self.busy)
        self.replay.setEnabled(self.speech is not None and not self.busy)
        if act == "OPTICS":
            self.capture_face.setEnabled(self.camera.reading and not self.busy
                                         and len(self.face_samples) < 3)
        if act == "VOCAL":
            self.record.setEnabled(not self.busy and len(self.voice_clips) < 3)
        self.render()

    # -------------------------------------------------------------------- boot
    def showEvent(self, event):
        super().showEvent(event)
        self.canvas.set_active(True)
        if self.reduced:
            self._boot_finish()
        else:
            self.canvas.boot_shown = 0
            self.boot_timer.start()

    def _boot_step(self):
        if self.canvas.boot_shown >= len(self.boot_lines):
            return
        self.canvas.boot_shown += 1
        self.render()
        self._sync()
        if self.canvas.boot_shown >= len(self.boot_lines):
            self.boot_timer.stop()
            self.skip_boot.hide()
            self.canvas.set_active(False)   # no idle animation at rest

    def _boot_finish(self):
        self.boot_timer.stop()
        self.canvas.boot_shown = len(self.boot_lines)
        self.skip_boot.hide()
        self.canvas.set_active(False)
        self.render()
        self._sync()

    def hideEvent(self, event):
        self.boot_timer.stop()
        self.canvas.set_active(False)
        self._stop_sensors()
        self._stop_speech()
        super().hideEvent(event)

    # -------------------------------------------------------------- navigation
    def go(self, delta):
        if self.busy:
            return
        if ACTS[self.act] == "VAULT" and delta > 0:
            self._commit()
            return
        if ACTS[self.act] == "ONLINE" and delta > 0:
            self._finish()
            return
        target = self.act + delta
        if target < 0 or target >= len(ACTS):
            return
        if delta > 0 and ACTS[self.act] == "BOOT":
            self._boot_finish()
        if ACTS[self.act] in ("OPTICS", "VOCAL"):
            self._stop_sensors()
        self.act = target
        self.pages.setCurrentIndex(self.act)
        self._after_act()
        self._sync()
        self.say()

    def _after_act(self):
        act = ACTS[self.act]
        self.canvas.set_active(act == "BOOT" and self.boot_timer.isActive())
        if act == "OPTICS":
            self.optics_status.setText("camera running" if self.camera.reading
                                       else "camera is off")
            if self.camera.reading:
                self.pump.start(40)
        if act == "VOCAL":
            code = " ".join(str(secrets.randbelow(10)) for _ in range(6))
            self.voice_codes.append(code)
            self.code_label.setText(code)
            self.vocal_status.setText("microphone off · press Record sample")
        if act == "ONLINE":
            self.online_status.setText(GREETING.format(salutation=self.salutation))
            self._stop_sensors()

    # ---------------------------------------------------------------- narration
    def say(self):
        if self.speech is None or not self.voice_toggle.isChecked():
            return
        act = ACTS[self.act]
        if act == "BOOT":
            text = "Waking up. Checking every system I depend on."
        elif act == "ONLINE":
            text = GREETING.format(salutation=self.salutation)
        elif act == "IDENTITY" and self.name.text().strip():
            text = (GREETING.format(salutation=self.salutation)
                     + f" I have you as {self.name.text().strip()}.")
        else:
            text = SCRIPT.get(act)
        if text:
            self.speech.say(text.format(salutation=self.salutation))

    def toggle_voice(self):
        self.voice_toggle.setText("Voice on" if self.voice_toggle.isChecked() else "Voice off")
        if self.voice_toggle.isChecked():
            self.say()
        else:
            self._stop_speech()

    def _stop_speech(self):
        if self.speech is not None:
            try:
                self.speech.stop()
            except Exception:
                pass

    def _speaking(self, active):
        self.speaking = bool(active)
        if not active:
            self.canvas.spoken_caption = ""
        self.canvas.update()

    def _speech_caption(self, text, _duration):
        self.canvas.spoken_caption = text
        self.canvas.update()

    def _speech_missing(self):
        self.voice_toggle.setChecked(False)
        self.voice_toggle.setText("Voice unavailable")

    def _salutation_changed(self, value):
        self.salutation = value
        self.render()

    def _name_changed(self, _text):
        if self.verified_name and self.name.text().strip() != self.verified_name:
            self.verified_name = ""
            self.verified_until = 0.0
            self.vault_status.setText("name changed · verify with Windows again")
        self._sync()

    # ------------------------------------------------------------------ optics
    def _toggle_camera(self):
        if self.camera.reading:
            self.camera.stop()
            self.pump.stop()
            self.camera_toggle.setText("Start camera")
            self.optics_status.setText("camera is off")
            self.canvas.video = None
            self.canvas.faces = []
            self.canvas.set_active(False)
            self._sync()
            return
        if not self.camera.start():
            self.optics_status.setText("no camera found")
            return
        self.camera_toggle.setText("Stop camera")
        self.optics_status.setText("camera running")
        self.pump.start(40)
        self.canvas.set_active(True)
        self._sync()

    def _take_face(self):
        if not self.camera.reading or len(self.face_samples) >= 3:
            return
        packet = self.camera.newest()
        if packet is None:
            self.optics_status.setText("no frame yet")
            return
        frame, faces = packet
        if not faces:
            self.optics_status.setText("no face detected - step into frame")
            return
        index = len(self.face_samples)
        self.face_samples.append(tuple(frame.shape[:2]))
        following = (FACE_PROMPTS[index + 1] if index + 1 < len(FACE_PROMPTS)
                     else "all three samples captured")
        self.optics_status.setText(f"sample {index + 1}/3 captured · next: {following}")
        self._sync()

    # ------------------------------------------------------------------- vocal
    def _take_voice(self):
        if self._recording or len(self.voice_clips) >= 3:
            return
        self._stop_speech()
        if not self.mic.start_meter():
            self.vocal_status.setText("no microphone available")
            return
        self.busy, self._recording = True, True
        self._record_done, self._record_clip = threading.Event(), b""
        self.pump.start(40)
        self.canvas.set_active(True)
        self._sync()

        def capture():
            clip = self.mic.record(3.5)
            if not self.closing:
                self._record_clip = clip
            self._record_done.set()

        threading.Thread(target=capture, daemon=True).start()

    def _pump(self):
        """Live picture, live level, and the completion of a real recording."""
        canvas = self.canvas
        if self.camera.reading:
            packet = self.camera.newest()
            if packet is not None:
                frame, faces = packet
                try:
                    import cv2
                    from PySide6.QtGui import QImage
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    height, width = rgb.shape[:2]
                    canvas.video = QImage(rgb.data, width, height, 3 * width,
                                          QImage.Format.Format_RGB888).copy()
                    canvas.faces = faces
                except Exception:
                    canvas.video = None
        if ACTS[self.act] == "VOCAL" and self.busy:
            canvas.wave.append(min(1.0, self.mic.level * 6.0))
            del canvas.wave[:-160]
        if self._recording and self._record_done.is_set():
            clip, self._recording, self.busy = self._record_clip, False, False
            self._record_clip = b""
            canvas.progress = 0.0
            if clip:
                stats = measure_wav(clip)
                if stats["seconds"] >= 0.5 and stats["rms"] >= 0.01 and not stats["clipped"]:
                    self.voice_clips.append(stats)
                    self.vocal_status.setText(
                        f"sample {len(self.voice_clips)}/3 · {stats['seconds']}s · "
                        f"level {stats['rms']} · microphone path measured")
                else:
                    self.vocal_status.setText("sample too quiet or clipped · please record again")
            else:
                self.vocal_status.setText("no audio captured")
            self.mic.stop()
            self.pump.stop()
            self.canvas.set_active(False)
            self._sync()
        canvas.update()

    def _stop_sensors(self):
        self.pump.stop()
        self.camera.stop()
        self.mic.stop()
        self.canvas.video = None
        self.canvas.faces = []
        self.canvas.wave = []
        self.canvas.progress = 0.0
        self._record_clip = b""

    # ------------------------------------------------------------------- vault
    def _hello(self):
        if self.busy or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        if not HELPER.is_file():
            self.vault_status.setText("helper missing · run security\\build-hello.cmd")
            return
        self.busy = True
        self.verified_until = 0.0
        self.verified_name = ""
        self.hello_failure = ""
        self.proof_nonce = secrets.token_urlsafe(24)
        self.vault_status.setText("complete the secure Windows prompt...")
        self.timeout.start(100000)
        self.process.start(str(HELPER),
                           ["verify", str(int(self.winId())), self.proof_nonce])
        self._sync()

    def _hello_done(self, code, status):
        self.timeout.stop()
        result = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace").strip()
        nonce, self.proof_nonce = self.proof_nonce, ""
        self.busy = False
        if self.hello_failure:
            self.vault_status.setText(self.hello_failure)
        elif (code == 0 and status == QProcess.ExitStatus.NormalExit
                and nonce and result == "Verified:" + nonce):
            self.verified_until = time.monotonic() + 90
            self.verified_name = self.name.text().strip()
            self.vault_status.setText("Windows checkpoint passed")
        else:
            self.vault_status.setText("not verified - you stay a guest")
        self._sync()

    def _hello_failed(self, _error):
        self.timeout.stop()
        self.busy = False
        self.proof_nonce = ""
        detail = self.process.errorString().casefold()
        self.hello_failure = ("Windows Application Control blocked the helper · admin setup stays locked"
                              if "policy" in detail or "blocked" in detail
                              else "Windows verification could not run · admin setup stays locked")
        self.vault_status.setText(self.hello_failure)
        self._sync()

    def _hello_timeout(self):
        self.busy = False
        self.proof_nonce = ""
        self.process.kill()
        self.vault_status.setText("verification timed out")
        self._sync()

    def _commit(self):
        """Write the admin profile only after a fresh Windows proof and consent."""
        if (self.busy or not self.consent.isChecked()
                or time.monotonic() >= self.verified_until
                or not self.name.text().strip()
                or self.name.text().strip() != self.verified_name):
            self.vault_status.setText("verify with Windows and confirm the consent box")
            self._sync()
            return
        from security.policy import Session
        try:
            from storage.store import register_device_admin
            person_id = register_device_admin(self.name.text().strip(), db_path=self.db_path)
        except PermissionError:
            self.vault_status.setText("an admin already exists - sign in as that name")
            self._sync()
            return
        except Exception:
            self.vault_status.setText("profile creation failed - nothing was written")
            self._sync()
            return
        self.created = person_id
        self.vault_status.setText(f"admin profile created: {person_id}")
        session = Session(role="admin", person=self.name.text().strip(),
                          id="session_" + secrets.token_urlsafe(18),
                          person_id=person_id, verified_until=time.time() + 300)
        self.authenticated.emit(session)
        self.act = len(ACTS) - 1
        self.pages.setCurrentIndex(self.act)
        self._after_act()
        self._sync()
        self.say()

    def _finish(self):
        self._stop_sensors()
        self._stop_speech()
        self.accept()

    def reject(self):
        self.closing = True
        self.timeout.stop()
        self.verified_until = 0.0
        self.verified_name = ""
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
        self._stop_sensors()
        self._stop_speech()
        super().reject()


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="LYA initialization")
    parser.add_argument("--reduced-motion", action="store_true")
    args = parser.parse_args()
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = ActivationDialog(reduced_motion=args.reduced_motion)
    dialog.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
