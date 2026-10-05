"""Render only synthetic LYA widgets; no desktop/sensor/store/model access."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path[:0] = [str(ROOT / 'desktop'), str(ROOT)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=('before', 'after', 'after-light'), default='after')
    args = parser.parse_args()
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QImage, QPainter, QColor, QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication
    from app import Crystal
    from experience import CompactPanel
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    for font in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    app.setFont(QFont('Segoe UI', 10))
    panel = CompactPanel()
    panel.reduced = True
    panel.set_mode('chat')
    panel.show_answer('Tomorrow, with a little more room.',
                      'You asked: I have college tomorrow, Lya. Help me plan my morning.\n\n'
                      'LYA: Let us make the morning easier.\n\n'
                      '1. Pack your bag tonight.\n2. Leave time for breakfast and travel.\n'
                      '3. Tell me when your first class starts.\n\n'
                      'This is sample interface text, not an alarm or task result.')
    panel.entry.setPlaceholderText('Continue the conversation...')
    panel.state_label.setText('CONVERSATION')
    panel.footnote.setText('SYNTHETIC DESIGN PREVIEW')
    panel.resize(570, 635)
    panel.show()
    orb = Crystal()
    orb.clearMask()
    orb.set_artwork(True)
    orb.set_reduced_motion(True)
    orb.setMinimumSize(1, 1)
    orb.setMaximumSize(16777215, 16777215)
    orb.setFixedSize(225, 310)
    orb.show()
    app.processEvents()
    canvas = QImage(1200, 850, QImage.Format.Format_ARGB32)
    canvas.fill(QColor('#edf0ef' if args.name == 'after-light' else '#070e18'))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor('#506273' if args.name == 'after-light' else '#9db4c7'))
    painter.setFont(QFont('Segoe UI', 11))
    painter.drawText(55, 55, 'LYA  /  CRYSTAL CONVERSATION')
    painter.drawText(55, 80, 'Synthetic widgets. No live conversation or sensor capture.')
    painter.drawPixmap(110, 140, orb.grab())
    painter.drawPixmap(550, 128, panel.grab())
    orb.setFixedSize(128, 128)
    orb.circle_mix = 1.0
    for index, phase in enumerate(('listening', 'thinking', 'speaking')):
        orb.set_voice_phase(phase)
        orb.phase = 1.3
        orb.voice_level = 0.45
        app.processEvents()
        painter.drawPixmap(60 + index * 145, 565, orb.grab())
        painter.drawText(QRectF(60 + index * 145, 705, 128, 24), Qt.AlignmentFlag.AlignCenter, phase.upper())
    painter.end()
    folder = ROOT / 'review/2026-10-05-conversation-design'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (args.name + '.png')
    if not canvas.save(str(path)):
        raise RuntimeError('Preview export failed.')
    if args.name == 'after':
        modes = QImage(1100, 560, QImage.Format.Format_ARGB32)
        modes.fill(QColor('#070e18'))
        painter = QPainter(modes)
        painter.setPen(QColor('#9db4c7'))
        painter.setFont(QFont('Segoe UI', 11))
        painter.drawText(50, 55, 'LYA / COMPACT RESPONSE AND COMPOSER')
        painter.drawText(50, 80, 'Synthetic widgets at their actual preferred dimensions.')
        panel.set_mode('answer')
        panel.show_answer('A little room for tomorrow.',
                          'You asked: Lya, help me plan my morning.\n\n'
                          'LYA: Pack tonight. Leave time for breakfast and travel.\n'
                          'When does your first class start?')
        panel.resize(500, 320)
        app.processEvents()
        painter.drawPixmap(50, 125, panel.grab())
        panel.set_mode('input')
        panel.entry.setPlaceholderText('Talk naturally, or type here...')
        panel.resize(460, 100)
        app.processEvents()
        painter.drawPixmap(590, 125, panel.grab())
        painter.drawText(590, 270, 'Input opens on click or when you start typing.')
        painter.drawText(590, 300, 'The reply keeps its title and readable paragraphs.')
        painter.drawText(590, 330, 'Your words stay literal, including markup characters.')
        painter.end()
        if not modes.save(str(folder / 'after-modes.png')):
            raise RuntimeError('Mode preview export failed.')
    panel.close()
    orb.close()
    print(str(path))


if __name__ == '__main__':
    main()
