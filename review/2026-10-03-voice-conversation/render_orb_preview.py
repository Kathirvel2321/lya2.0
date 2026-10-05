"""Render the actual Qt orb on synthetic backgrounds; no desktop screenshots."""
import os
import sys
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'desktop'))
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from app import Crystal


def main():
    app = QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf', 'segoeuib.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
    orb = Crystal()
    orb.clearMask()
    orb.setMinimumSize(1, 1)
    orb.setMaximumSize(1000, 1000)
    orb.resize(128, 128)
    orb.circle_mix = 1.0
    canvas = QImage(1000, 460, QImage.Format.Format_ARGB32)
    canvas.fill(QColor('#07111e'))
    painter = QPainter(canvas)
    painter.setPen(QColor('#ecf7fc'))
    painter.setFont(QFont('Segoe UI', 18, QFont.Weight.DemiBold))
    painter.drawText(34, 40, 'LYA · voice lives in the circle')
    painter.setFont(QFont('Segoe UI', 10))
    painter.setPen(QColor('#8daabc'))
    painter.drawText(34, 65, 'Actual Qt rendering · synthetic input level · listening, thought, reply')
    phases = [('standby', 'Waiting for wake'), ('listening', 'Listening'), ('hearing', 'Hearing you'),
              ('thinking', 'Thinking'), ('speaking', 'Speaking — say stop'), ('uncertain', 'Please repeat')]
    for row, background in enumerate(('#07111e', '#e9f0f5')):
        painter.fillRect(0, 80 + row * 185, 1000, 185, QColor(background))
        for index, (phase, label) in enumerate(phases):
            orb.voice_phase = phase
            orb.voice_level = 0.75 if phase == 'hearing' else 0.15
            orb.phase = 1.2
            pixmap = orb.grab()
            x = 20 + index * 163
            painter.drawPixmap(x + 12, 90 + row * 185, pixmap)
            painter.setPen(QColor('#aac7d8' if row == 0 else '#344957'))
            painter.setFont(QFont('Segoe UI', 9))
            painter.drawText(x, 232 + row * 185, 160, 25, Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    path = Path(__file__).resolve().parent / 'orb-states.png'
    assert canvas.save(str(path))
    print(path)
    orb.deleteLater()
    app.processEvents()


if __name__ == '__main__':
    main()
