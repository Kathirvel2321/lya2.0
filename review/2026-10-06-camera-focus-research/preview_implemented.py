"""Render the actual camera widget with drawn objects/fake detections; no sensor or model."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'desktop')]
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication
from camera_eyes import VisionDialog
from security.policy import Session

app = QApplication([])
QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
image = QImage(1280, 720, QImage.Format.Format_RGB32)
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
background = QLinearGradient(0, 0, 1280, 720)
background.setColorAt(0, QColor('#203c47'))
background.setColorAt(1, QColor('#0b151e'))
p.fillRect(image.rect(), background)
p.fillRect(0, 550, 1280, 170, QColor('#273e46'))
p.setPen(QPen(QColor('#516971'), 2))
p.drawLine(0, 550, 1280, 550)
p.setFont(QFont('Segoe UI', 19))
p.setPen(QColor('#bad8df'))
p.drawText(36, 52, 'SYNTHETIC PREVIEW · illustrated objects and fake detections')
p.setPen(QPen(QColor('#98b4bc'), 3))
p.setBrush(QColor('#172831'))
p.drawRoundedRect(QRectF(165, 325, 125, 238), 16, 16)
p.setBrush(QColor('#3a5766'))
p.drawRoundedRect(QRectF(174, 343, 107, 196), 8, 8)
p.setPen(QPen(QColor('#8cc0b0'), 3))
p.setBrush(QColor('#325e50'))
p.drawRoundedRect(QRectF(532, 297, 158, 267), 25, 25)
p.drawRect(QRectF(575, 230, 70, 82))
p.setBrush(QColor('#c2c5ad'))
p.drawRoundedRect(QRectF(565, 214, 90, 25), 5, 5)
p.drawRect(QRectF(535, 390, 153, 82))
p.setPen(QPen(QColor('#9eafaa'), 4))
p.setBrush(QColor('#8b9d9b'))
p.drawRoundedRect(QRectF(983, 418, 133, 146), 15, 15)
p.setBrush(Qt.BrushStyle.NoBrush)
p.drawEllipse(QRectF(1094, 441, 65, 85))
p.setBrush(QColor('#283d43'))
p.drawEllipse(QRectF(983, 408, 133, 25))
p.end()

token = Session('admin', 'Synthetic owner', 'fake-session', 'fake-person', time.time()+60)
dialog = VisionDialog(access_check=lambda: token)
dialog.resize(1000, 605)
dialog.checked_pixmap = QPixmap.fromImage(image)
dialog.live_pixmap = dialog.checked_pixmap
dialog.checked_at = time.monotonic()
dialog.last_result = {'width': 1280, 'height': 720, 'ready': True,
                      'analyzed_at': dialog.checked_at, 'faces': [], 'hands': [], 'objects': [
    {'label': 'cell phone', 'confidence': .9, 'box': [160, 319, 296, 568]},
    {'label': 'bottle', 'confidence': .9, 'box': [527, 208, 696, 570]},
    {'label': 'cup', 'confidence': .9, 'box': [977, 402, 1165, 570]}]}
dialog.pending_question = (1, 'find my bottle')
dialog._answer_pending()
dialog.show()
app.processEvents()
out = Path(__file__).resolve().parent
assert dialog.grab().save(str(out / 'camera-focus-implemented.png'))
dialog.pending_question = (2, 'what all can you see?')
dialog._answer_pending()
dialog.focus_item(dialog.answer_details['items'][2])
dialog.status.setText('Checked frame · tour item 3 of 3 · local only · nothing saved')
app.processEvents()
assert dialog.grab().save(str(out / 'camera-tour-implemented.png'))
dialog.close()
print('Saved two native-widget previews with synthetic fixtures; no camera opened.')
