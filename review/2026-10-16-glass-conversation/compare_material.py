"""Controlled native render: identical background, content and panel geometry."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'desktop'))
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from experience import CompactPanel

spec = importlib.util.spec_from_file_location('previous_glass', Path(__file__).with_name('glass_style_before.py'))
before = importlib.util.module_from_spec(spec)
spec.loader.exec_module(before)


class EarlierPanel(CompactPanel):
    def paintEvent(self, event):
        before.paint_glass(self)


class FlatDesktop(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#647282'))
        painter.end()


def main():
    application = QApplication.instance() or QApplication([])
    if sys.platform == 'win32':
        for name in ('segoeui.ttf', 'segoeuib.ttf'):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get('SystemRoot', r'C:\Windows'))/'Fonts'/name))
        application.setFont(QFont('Segoe UI', 10))
    desktop = FlatDesktop()
    desktop.resize(1080, 560)
    panels = []
    for index, cls in enumerate((EarlierPanel, CompactPanel)):
        x = 35 + index*520
        label = QLabel('EARLIER MATERIAL' if index == 0 else 'CURRENT MATERIAL', desktop)
        label.setGeometry(x+12, 15, 460, 38)
        label.setStyleSheet('background: transparent; color: #f0f4f8; font: 13px "Segoe UI";')
        panel = cls()
        panel.setParent(desktop)
        panel.setWindowFlags(Qt.WindowType.Widget)
        panel.setGeometry(x, 65, 480, 450)
        panel.set_mode('chat')
        panel.set_reduced_motion(True)
        panel.show_transcript('You: Compare these notes for me.\n\nLYA: Tell me which details matter most.')
        panel.footnote.setText('SAME SIZE · SAME TEXT · SAME BACKGROUND')
        if index == 0:
            panel.entry.setStyleSheet('background: rgba(6,12,18,220); border: 1px solid rgba(150,215,230,68); border-radius: 20px; padding: 13px 18px;')
        panel.show()
        panels.append(panel)
    desktop.show()
    application.processEvents()
    path = Path(__file__).with_name('same-background-comparison.png')
    assert desktop.grab().save(str(path))
    print(path)
    for panel in panels:
        panel.close()
    desktop.close()


if __name__ == '__main__':
    main()
