"""Render synthetic LYA widget states for visual review in Windows CI.

No Brain, microphone, camera, identity or private store is initialized.
"""
from pathlib import Path
import sys

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import Crystal
from living_body import create_body_type


def main():
    app = QApplication.instance() or QApplication([])
    widget = create_body_type(Crystal)()
    widget.set_reduced_motion(True)
    assert widget.body_enabled, 'Approved body asset did not load'
    widget.show()
    output = Path(__file__).resolve().parent.parent / 'visual-creativity-qt'
    output.mkdir(exist_ok=True)
    states = (
        ('listening', 'listening', 'none', (230, 315)),
        ('thinking-coding', 'thinking', 'coding', (230, 315)),
        ('speaking', 'speaking', 'none', (230, 315)),
        ('blocked', 'idle', 'blocked', (230, 315)),
        ('docked-standby', 'standby', 'none', (96, 112)),
    )
    for name, phase, task, (width, height) in states:
        widget.setFixedSize(width, height)
        widget.preview_effect(phase, task)
        app.processEvents()
        sprite = widget.grab()
        canvas = QImage(max(420, width + 100), max(390, height + 60),
                        QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(QColor('#101d2c'))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(QPoint((canvas.width() - sprite.width()) // 2,
                                  (canvas.height() - sprite.height()) // 2), sprite)
        painter.end()
        path = output / f'{name}.png'
        assert canvas.save(str(path)), f'Could not save {path.name}'
        print(f'Rendered {name}: {canvas.width()}x{canvas.height()}')
    widget.close()


if __name__ == '__main__':
    main()
