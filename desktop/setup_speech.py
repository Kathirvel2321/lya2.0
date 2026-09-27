"""Private local speech worker with phrase-timed caption events."""
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VOICE_ROOT = ROOT / 'external-work'


def _load_voice(keep_warm=False):
    sys.path.insert(0, str(VOICE_ROOT))
    from alya_voice.audit import Auditor
    from alya_voice.runtime import Voice
    # LYA never stores spoken text or a fingerprint of it in the desktop path.
    return Voice(timbre='native', keep_warm=keep_warm,
                 auditor=Auditor(VOICE_ROOT / 'out' / 'audit', enabled=False))


def speak_local(text, language='auto', style='everyday', engine='offline_piper'):
    voice = _load_voice()
    try:
        return voice.speak(text, language=language, style=style, engine=engine,
                           allow_remote=False, allow_interjections=False)
    finally:
        voice.close()


if __name__ == '__main__':
    import logging
    logging.disable(logging.CRITICAL)
    voice = _load_voice(keep_warm=True)
    if '--warm-piper' in sys.argv:
        try:
            voice._engine('offline_piper')._voice('en')
        except Exception:
            pass  # A missing model is reported when speech is requested.
    while True:
        line = sys.stdin.buffer.readline(16385)
        if not line:
            break
        if len(line) > 16384:
            sys.exit(1)
        payload = json.loads(line.decode('utf-8'))
        if isinstance(payload, str):
            payload = {'text': payload}
        if not isinstance(payload, dict) or not isinstance(payload.get('text'), str) or len(payload['text']) > 1000:
            sys.exit(1)
        request = payload.pop('id', 0)
        def event(data):
            print(json.dumps(dict(data, id=request)), flush=True)
        try:
            def caption(chunk):
                event({'kind': 'caption', 'text': chunk.text,
                       'duration_ms': max(1, round(chunk.seconds * 1000))})
            voice.speak(**payload, allow_remote=False, allow_interjections=False,
                        on_chunk=caption)
            event({'kind': 'done'})
        except Exception:
            event({'kind': 'error'})
            # Do not reuse model state after an uncertain synthesis failure.
            voice.close()
            sys.exit(1)
    voice.close()
else:
    from PySide6.QtCore import QObject, QProcess, QTimer, Signal

    class SetupSpeech(QObject):
        speaking = Signal(bool)
        unavailable = Signal()
        caption = Signal(str, int)
        completed = Signal()

        def __init__(self, parent=None):
            super().__init__(parent)
            self.pending = None
            self.cancelled = False
            self.busy = False
            self.request = 0
            self.warming = False
            self.buffer = b''
            self.process = QProcess(self)
            self.process.started.connect(self._started)
            self.process.finished.connect(self._finished)
            self.process.errorOccurred.connect(self._error)
            self.process.readyReadStandardOutput.connect(self._read)
            self.timeout = QTimer(self)
            self.timeout.setSingleShot(True)
            self.timeout.timeout.connect(self._timed_out)
            self.idle = QTimer(self)
            self.idle.setSingleShot(True)
            self.idle.timeout.connect(self.stop)

        def say(self, text, language='auto', style='everyday', engine='offline_piper'):
            self.request += 1
            self.idle.stop()
            self.warming = False
            self.pending = dict(id=self.request, text=str(text)[:1000], language=language, style=style, engine=engine)
            if self.process.state() == QProcess.ProcessState.NotRunning:
                self._launch()
            elif not self.busy and not self.cancelled:
                self._started()  # Reuse the warm, idle worker.
            else:
                self.cancelled = True
                self.process.kill()

        def prewarm(self):
            """Load the local voice worker now, so the first answer speaks at once."""
            if self.pending is not None or self.busy or self.warming:
                return
            if self.process.state() != QProcess.ProcessState.NotRunning:
                return
            self.cancelled = False
            self.warming = True
            self.timeout.start(120000)
            self.process.start(sys.executable, [str(Path(__file__).resolve()), '--warm-piper'])

        def _launch(self):
            if self.pending is None:
                return
            self.cancelled = False
            self.busy = True
            self.buffer = b''
            arguments = [str(Path(__file__).resolve())]
            if self.pending['engine'] == 'offline_piper':
                arguments.append('--warm-piper')
            self.process.start(sys.executable, arguments)
            self.timeout.start(120000)

        def _started(self):
            if self.warming and self.pending is None:
                self.warming = False
                self.busy = False
                self.timeout.stop()
                self.idle.start(45000)     # Keep the loaded voice warm and idle.
                return
            self.warming = False
            if self.pending is None or self.cancelled:
                self.process.kill()
                return
            self.busy = True
            self.timeout.start(120000)
            self.process.write(json.dumps(self.pending).encode('utf-8') + b'\n')
            self.pending = None
            self.speaking.emit(True)

        def _read(self):
            self.buffer += bytes(self.process.readAllStandardOutput())
            if len(self.buffer) > 65536:
                self._timed_out()
                return
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                try:
                    data = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                if not isinstance(data, dict) or data.get('id') != self.request or self.cancelled or not self.busy:
                    continue
                if data.get('kind') == 'caption' and isinstance(data.get('text'), str):
                    self.caption.emit(data['text'][:1000], max(1, int(data.get('duration_ms', 1))))
                elif data.get('kind') in ('done', 'error'):
                    self.busy = False
                    self.timeout.stop()
                    self.speaking.emit(False)
                    self.completed.emit()
                    if data['kind'] == 'error':
                        self.cancelled = True
                        self.unavailable.emit()
                    else:
                        self.idle.start(45000)

        def stop(self, keep_warm=False):
            # Navigation must not unload an idle model before the next reply.
            if keep_warm and not self.busy and self.pending is None and not self.cancelled:
                return
            was_active = self.busy or self.pending is not None
            self.warming = False
            self.request += 1
            self.pending = None
            self.cancelled = True
            self.busy = False
            self.buffer = b''
            self.timeout.stop()
            self.idle.stop()
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()
            self.speaking.emit(False)
            if was_active:
                self.completed.emit()

        def _finished(self, code, _status):
            was_busy = self.busy
            self.warming = False
            self.busy = False
            self.timeout.stop()
            self.speaking.emit(False)
            if was_busy and not self.cancelled:
                self.unavailable.emit()
                self.completed.emit()
            self._launch()

        def _error(self, error):
            if error == QProcess.ProcessError.FailedToStart:
                self.pending = None
                self.busy = False
                self.timeout.stop()
                self.speaking.emit(False)
                if not self.cancelled:
                    self.unavailable.emit()
                    self.completed.emit()

        def _timed_out(self):
            self.stop()
            self.unavailable.emit()
            self.completed.emit()
