"""Camera-only local preview. Questions and replies belong to LYA's conversation."""
import base64
import json
from pathlib import Path
import sys
import time

from PySide6.QtCore import Qt, QProcess, QTimer, Signal
from PySide6.QtGui import QFont, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
from vision.answers import answer_scene

ROOT = Path(__file__).resolve().parents[1]


class VisionCanvas(QLabel):
    """Keep the original image and scale once when painting, including on resize."""
    def paintEvent(self, event):
        if self.pixmap().isNull():
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        size = self.pixmap().size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        target = self.rect()
        target.setSize(size)
        target.moveCenter(self.rect().center())
        painter.drawPixmap(target, self.pixmap())
        painter.end()


class VisionDialog(QDialog):
    answer_ready = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('LYA · Camera')
        self.resize(800, 495)
        self.setMinimumSize(480, 320)
        self.setFont(QFont('Segoe UI', 10))
        self.setStyleSheet('''
            QDialog { background: #080f16; }
            QLabel { color: #acd8df; font: 12px "Segoe UI"; }
            QPushButton { background: #152b35; color: #d8fbff; border: 1px solid #345762;
                          border-radius: 8px; padding: 7px 16px; }
            QPushButton:hover { background: #244451; }
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.scene = VisionCanvas('CAMERA OFF')
        self.scene.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scene.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.scene.setMinimumSize(320, 180)
        self.scene.setAccessibleName('Live camera preview')
        layout.addWidget(self.scene, 1)
        row = QHBoxLayout()
        row.setContentsMargins(12, 6, 12, 6)
        self.status = QLabel('Camera off · local only · nothing saved')
        row.addWidget(self.status, 1)
        self.live_button = QPushButton('Start camera')
        self.live_button.clicked.connect(self.toggle_live)
        row.addWidget(self.live_button)
        layout.addLayout(row)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.readyReadStandardError.connect(lambda: self.process.readAllStandardError())
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.stop_camera('Camera session ended', notify_pending=True))
        self.output = bytearray()
        self.last_result = None
        self.last_seen = 0.0
        self.pending_question = None
        self.stopping = False

    def toggle_live(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.stop_camera()
            return
        self.stopping = False
        self.output.clear()
        self.last_result = None
        self.last_seen = 0.0
        self.scene.clear()
        self.scene.setText('Starting camera…')
        self.status.setText('Starting · local only')
        self.live_button.setText('Stop camera')
        self.process.start(sys.executable, [str(ROOT / 'vision' / 'scan.py'), '--camera-live'])
        self.timer.start(95000)

    def stop_camera(self, message='Camera off · local only · nothing saved', notify_pending=False):
        self.stopping = True
        self.timer.stop()
        pending, self.pending_question = self.pending_question, None
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(500)
        self.output.clear()
        self.last_result = None
        self.last_seen = 0.0
        self.scene.clear()
        self.scene.setText('CAMERA OFF')
        self.status.setText(message)
        self.live_button.setText('Start camera')
        if pending and notify_pending:
            self.answer_ready.emit(pending[0], 'The camera stopped before I could check. Please try again.')

    def ask(self, question, request_id=0):
        if not question.strip():
            return
        self.pending_question = (request_id, question)
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.toggle_live()
        self._answer_pending()

    def _answer_pending(self):
        scene = self.last_result
        if not self.pending_question or not scene or not scene.get('ready'):
            return
        # Age the analyzed frame itself, not just the most recent video packet.
        if time.monotonic() - scene.get('analyzed_at', 0) > 2:
            return
        request_id, question = self.pending_question
        self.pending_question = None
        self.answer_ready.emit(request_id, answer_scene(question, scene))

    def _read_output(self):
        self.output.extend(bytes(self.process.readAllStandardOutput()))
        if self.stopping:
            self.output.clear()
            return
        if len(self.output) > 4_000_000:
            self.stop_camera('Camera stream stopped: preview could not keep up', notify_pending=True)
            return
        # Render only the newest complete packet. Old video frames are never replayed.
        end = self.output.rfind(b'\n')
        if end < 0:
            return
        packet = bytes(self.output[:end]).rsplit(b'\n', 1)[-1]
        del self.output[:end + 1]
        try:
            result = json.loads(packet)
            if 'error' in result:
                raise ValueError(result['error'])
            image = result.pop('image')
            pixmap = QPixmap()
            if not pixmap.loadFromData(base64.b64decode(image, validate=True), 'JPG'):
                raise ValueError('Invalid camera frame')
            self.scene.setPixmap(pixmap)
            self.last_result = result
            self.last_seen = time.monotonic()
            self.status.setText(f"Live · {result['width']} × {result['height']} · local only")
            self._answer_pending()
        except (ValueError, KeyError, TypeError) as exc:
            self.stop_camera(f'Camera stopped: {exc}', notify_pending=True)

    def _finished(self, *_):
        if not self.stopping:
            self.stop_camera('Camera session ended', notify_pending=True)

    def _error(self, *_):
        if not self.stopping:
            self.stop_camera('Camera unavailable. Check camera permissions and other apps.', notify_pending=True)

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)

    def reject(self):
        self.close()
