"""Camera-only local preview. Questions and replies belong to LYA's conversation."""
import base64
import json
import math
import os
from pathlib import Path
import sys
import time

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer, Signal, QRectF, QBuffer, QByteArray
from PySide6.QtGui import QFont, QPainter, QPixmap, QPen, QColor, QImageReader
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
from vision.answers import scene_result, LABELS

ROOT = Path(__file__).resolve().parents[1]


class VisionCanvas(QLabel):
    """Keep the original image and scale once when painting, including on resize."""
    items = ()
    selected = None

    def image_rect(self):
        target = QRectF(self.rect())
        size = self.pixmap().size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        target.setSize(size)
        target.moveCenter(QRectF(self.rect()).center())
        return target

    def paintEvent(self, event):
        if self.pixmap() is None or self.pixmap().isNull():
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        target = self.image_rect()
        painter.drawPixmap(target.toRect(), self.pixmap())
        painter.setClipRect(target)
        sx, sy = target.width() / self.pixmap().width(), target.height() / self.pixmap().height()
        painter.setFont(QFont('Segoe UI', 10))
        for number, item in enumerate(self.items, 1):
            x1, y1, x2, y2 = item['box']
            box = QRectF(target.left() + x1 * sx, target.top() + y1 * sy, (x2-x1)*sx, (y2-y1)*sy)
            active = item == self.selected
            painter.setPen(QPen(QColor('#86f4ee' if active else '#638995'), 2 if active else 1,
                                Qt.PenStyle.SolidLine if active else Qt.PenStyle.DashLine))
            painter.drawRoundedRect(box, 5, 5)
            if active:
                edge = min(15., box.width()/3, box.height()/3)
                for x, dx in ((box.left(), edge), (box.right(), -edge)):
                    for y, dy in ((box.top(), edge), (box.bottom(), -edge)):
                        painter.drawLine(x, y, x+dx, y)
                        painter.drawLine(x, y, x, y+dy)
            label = f"{number:02} · {item['label'].title()}" + (' · FOCUS' if active else '')
            width = min(target.width(), painter.fontMetrics().horizontalAdvance(label) + 16)
            tag = QRectF(min(box.left(), target.right()-width), max(target.top(), box.top()-26), width, 24)
            painter.fillRect(tag, QColor('#16343e' if active else '#10212a'))
            painter.drawText(tag.adjusted(8, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter, label)
        painter.end()


class VisionDialog(QDialog):
    answer_ready = Signal(int, str)
    session_ended = Signal()
    focus_cleared = Signal()

    def __init__(self, parent=None, access_check=None):
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
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        row.addWidget(self.status, 1)
        self.live_button = QPushButton('Start camera')
        self.live_button.clicked.connect(lambda: self.toggle_live())
        self.resume_button = QPushButton('Live view')
        self.resume_button.clicked.connect(self.clear_focus)
        row.addWidget(self.resume_button)
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
        self.access_check = access_check or (lambda: None)  # Standalone/guest view is denied by default.
        self.owner_token = None
        self.checked_pixmap = QPixmap()
        self.checked_at = 0.0
        self.live_pixmap = QPixmap()
        self.answer_details = None
        self.focus_active = False
        self.access_timer = QTimer(self)
        self.access_timer.setInterval(1000)
        self.access_timer.timeout.connect(self.check_access)

    def authorized(self):
        try:
            token = self.access_check()
            return bool(token and (self.owner_token is None or token == self.owner_token))
        except Exception:
            return False

    def check_access(self):
        if not self.authorized():
            self.stop_camera('Camera locked · verify the LYA owner again', notify_pending=True)
        elif self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.write(b'lease\n')

    def clear_focus(self):
        was_active = self.focus_active
        self.focus_active = False
        self.answer_details = None
        self.scene.items, self.scene.selected = (), None
        if not self.live_pixmap.isNull():
            self.scene.setPixmap(self.live_pixmap)
        self.scene.update()
        if was_active:
            self.focus_cleared.emit()

    def focus_item(self, item):
        if self.focus_active:
            self.scene.selected = item
            self.scene.update()

    def toggle_live(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.stop_camera()
            return
        if not self.authorized():
            self.stop_camera('Camera locked · sign in as the verified LYA owner', notify_pending=True)
            return
        try:
            self.owner_token = self.access_check()
        except Exception:
            self.owner_token = None
        if not self.owner_token:
            self.stop_camera('Camera locked · sign in as the verified LYA owner', notify_pending=True)
            return
        self.stopping = False
        self.output.clear()
        self.last_result = None
        self.last_seen = 0.0
        self.scene.clear()
        self.scene.setText('Starting camera…')
        self.status.setText('Starting · local only')
        self.live_button.setText('Stop camera')
        # Keep provider credentials and unrelated application environment out of the camera worker.
        environment = QProcessEnvironment()
        for name in ('SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP'):
            if name in os.environ:
                environment.insert(name, os.environ[name])
        for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
            environment.insert(name, '2')
        environment.insert('PYTHONNOUSERSITE', '1')
        self.process.setProcessEnvironment(environment)
        self.process.start(sys.executable, [str(ROOT / 'vision' / 'scan.py'), '--camera-live',
                                          str(self.owner_token.verified_until)])
        self.access_timer.start()
        self.timer.start(95000)

    def stop_camera(self, message='Camera off · local only · nothing saved', notify_pending=False):
        self.stopping = True
        self.timer.stop()
        self.access_timer.stop()
        pending, self.pending_question = self.pending_question, None
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(500)
        self.output.clear()
        self.last_result = None
        self.last_seen = 0.0
        self.owner_token = None
        self.clear_focus()
        self.live_pixmap = QPixmap()
        self.checked_pixmap = QPixmap()
        self.checked_at = 0.0
        self.scene.clear()
        self.scene.setText('CAMERA OFF')
        self.status.setText(message)
        self.live_button.setText('Start camera')
        self.session_ended.emit()
        if pending and notify_pending:
            reply = ('Camera access is locked. Sign in as the verified LYA owner first.' if 'locked' in message else
                     'The camera stopped before I could check. Please try again.')
            self.answer_ready.emit(pending[0], reply)

    def ask(self, question, request_id=0):
        if not question.strip():
            return
        self.clear_focus()
        self.pending_question = (request_id, question)
        if not self.authorized():
            self.check_access()
            return
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
        if self.checked_pixmap.isNull() or self.checked_at != scene.get('analyzed_at'):
            return  # Never mark current pixels with detections from a different image.
        if not self.authorized():
            self.check_access()
            return
        request_id, question = self.pending_question
        self.pending_question = None
        self.answer_details = dict(scene_result(question, scene), request_id=request_id)
        self.focus_active = bool(self.answer_details['items'])
        if self.focus_active:
            self.scene.items = self.answer_details['items']
            self.scene.selected = self.answer_details['selected']
            self.scene.setPixmap(self.checked_pixmap)
            self.status.setText('Checked frame · numbered objects · local only · nothing saved')
        self.answer_ready.emit(request_id, self.answer_details['text'])

    @staticmethod
    def packet_pixmap(encoded, width, height):
        if not isinstance(encoded, str) or len(encoded) > 2_000_000:
            raise ValueError('Invalid camera image size')
        data = QByteArray(base64.b64decode(encoded, validate=True))
        buffer = QBuffer(data)
        buffer.open(QBuffer.OpenModeFlag.ReadOnly)
        reader = QImageReader(buffer, b'JPG')
        if reader.size().width() != width or reader.size().height() != height:
            raise ValueError('Camera image dimensions do not match')
        image = reader.read()
        if image.isNull():
            raise ValueError('Invalid camera frame')
        return QPixmap.fromImage(image)

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
        packets = bytes(self.output[:end]).split(b'\n')
        packet = packets[-1]
        del self.output[:end + 1]
        try:
            result = json.loads(packet)
            if not isinstance(result, dict):
                raise ValueError('Invalid camera packet')
            if 'error' in result:
                raise ValueError(result['error'])
            image = result.pop('image')
            width, height = result['width'], result['height']
            if (type(width) is not int or type(height) is not int or
                    not 1 <= width <= 1280 or not 1 <= height <= 720):
                raise ValueError('Invalid camera dimensions')
            objects = result.get('objects', [])
            if not isinstance(objects, list) or len(objects) > 12:
                raise ValueError('Invalid camera object count')
            for item in objects:
                box = item['box']
                if (item['label'] not in LABELS or len(box) != 4 or
                        not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box) or
                        not 0 <= box[0] < box[2] <= width or not 0 <= box[1] < box[3] <= height or
                        not math.isfinite(item['confidence']) or not .45 <= item['confidence'] <= 1):
                    raise ValueError('Invalid camera detection')
            faces, hands = result.get('faces', []), result.get('hands', [])
            if not isinstance(faces, list) or len(faces) > 12 or not isinstance(hands, list) or len(hands) > 2:
                raise ValueError('Invalid camera landmark count')
            for hand in hands:
                points = hand['points']
                if (len(points) != 21 or not math.isfinite(hand['confidence']) or not 0 <= hand['confidence'] <= 1 or
                        not all(len(p) == 2 and all(math.isfinite(v) and abs(v) <= 5120 for v in p) for p in points)):
                    raise ValueError('Invalid camera landmarks')
            analyzed_at = result.get('analyzed_at', 0)
            if not isinstance(analyzed_at, (int, float)) or not math.isfinite(analyzed_at) or not 0 <= analyzed_at <= time.monotonic()+1:
                raise ValueError('Invalid analysis time')
            checked = result.pop('checked_image', None)
            # Qt may batch several video packets after the one carrying checked pixels.
            # Retain that image only when its analysis and dimensions match the latest result.
            if checked is None and self.checked_at != analyzed_at:
                for earlier in reversed(packets[:-1]):
                    candidate = json.loads(earlier)
                    if (isinstance(candidate, dict) and candidate.get('analyzed_at') == analyzed_at and
                            candidate.get('width') == width and candidate.get('height') == height and
                            'checked_image' in candidate):
                        checked = candidate['checked_image']
                        break
            if checked is not None:
                self.checked_pixmap = self.packet_pixmap(checked, width, height)
                self.checked_at = analyzed_at
            self.live_pixmap = self.packet_pixmap(image, width, height)
            if not self.focus_active:
                self.scene.setPixmap(self.live_pixmap)
            self.last_result = result
            self.last_seen = time.monotonic()
            if not self.focus_active:
                self.status.setText(f"Live · {width} × {height} · verified owner · local only")
            self._answer_pending()
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            self.stop_camera(f'Camera stopped: {str(exc)[:180]}', notify_pending=True)

    def _finished(self, *_):
        if not self.stopping:
            self.stop_camera('Camera session ended', notify_pending=True)

    def _error(self, *_):
        if not self.stopping:
            self.stop_camera('Camera unavailable. Check camera permissions and other apps.', notify_pending=True)

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)

    def hideEvent(self, event):
        self.stop_camera()
        super().hideEvent(event)

    def changeEvent(self, event):
        if self.isMinimized():
            self.stop_camera('Camera off · minimized')
        super().changeEvent(event)

    def reject(self):
        self.close()
