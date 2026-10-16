"""Native glass surface: fixed gradients and a small active glint, no live blur."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen


ACTIVITY = {
    'idle': ('#8bcbdc', ''),
    'working': ('#78dce9', 'Working on your request'),
    'research': ('#b5a3ee', 'Finding sources'),
    'reason': ('#78dce9', 'Preparing your answer'),
    'launching': ('#78dce9', 'Opening the app'),
    'approval': ('#ffc26b', 'Needs your attention'),
    'error': ('#ff879b', 'Could not finish'),
    'done': ('#86d9b6', 'Finished'),
}
MOVING = frozenset(('working', 'research', 'reason', 'launching'))


def paint_glass(widget):
    p = QPainter(widget)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if widget.isWindow():
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(widget.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    rect = QRectF(widget.rect()).adjusted(10, 10, -10, -10)
    path = QPainterPath()
    path.addRoundedRect(rect, 22, 22)
    state = getattr(widget, '_activity', 'idle')
    color = QColor(ACTIVITY[state][0])
    # Two fixed edge strokes create depth without a blur/compositing pass.
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(0, 0, 0, 48), 5))
    p.drawPath(path)
    fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
    alpha = 255 if widget.opaque else 244
    fill.setColorAt(0, QColor(22, 43, 65, alpha))
    fill.setColorAt(.46, QColor(11, 28, 48, alpha))
    fill.setColorAt(1, QColor(7, 19, 34, alpha))
    p.setBrush(fill)
    color.setAlpha(170 if state != 'idle' else 112)
    p.setPen(QPen(color, 1.15))
    p.drawPath(path)
    p.save()
    p.setClipPath(path)
    sheen = QLinearGradient(rect.topLeft(), rect.bottomRight())
    sheen.setColorAt(0, QColor(176, 222, 255, 20))
    sheen.setColorAt(.22, QColor(176, 222, 255, 4))
    sheen.setColorAt(.5, QColor(176, 222, 255, 0))
    p.fillRect(rect, sheen)
    reflection = QLinearGradient(rect.left(), rect.top(), rect.left() + rect.width()*.55, rect.top() + rect.height()*.4)
    reflection.setColorAt(0, QColor(165, 214, 255, 0))
    reflection.setColorAt(.4, QColor(165, 214, 255, 0))
    reflection.setColorAt(.55, QColor(165, 214, 255, 12))
    reflection.setColorAt(.72, QColor(165, 214, 255, 0))
    reflection.setColorAt(1, QColor(165, 214, 255, 0))
    p.fillRect(rect, reflection)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(218, 240, 255, 24), .7))
    p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 20, 20)
    if state in MOVING:
        x = rect.left() + 28 + (rect.width() - 56) * getattr(widget, '_edge_phase', 0)
        p.setPen(QPen(QColor(ACTIVITY[state][0]), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x - 8, rect.top()), QPointF(x + 8, rect.top()))
    p.restore()
    p.end()
