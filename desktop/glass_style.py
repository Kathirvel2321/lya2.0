"""Native glass surface: fixed gradients and a small active glint, no live blur."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient


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


def make_material(width, height, dpr, opaque):
    """Bake one translucent material at the current size; no desktop capture."""
    surface = QPixmap(round(width*dpr), round(height*dpr))
    surface.setDevicePixelRatio(dpr)
    surface.fill(Qt.GlobalColor.transparent)
    p = QPainter(surface)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(10, 10, width - 20, height - 20)
    path = QPainterPath()
    path.addRoundedRect(rect, 22, 22)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(0, 5, 13, 52), 6))
    p.drawPath(path.translated(0, 2))

    # Actual alpha transmission, rather than a nearly opaque navy rectangle.
    fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
    fill.setColorAt(0, QColor(21, 53, 85, 255 if opaque else 158))
    fill.setColorAt(.42, QColor(8, 30, 56, 255 if opaque else 190))
    fill.setColorAt(1, QColor(5, 24, 46, 255 if opaque else 205))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawPath(path)
    p.save()
    p.setClipPath(path)

    # Broad softbox reflection with feathered edges; fixed in material space.
    light = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top()+height*.58)
    for position, alpha in ((0, 7), (.15, 14), (.27, 40), (.34, 46), (.44, 14), (.57, 0), (1, 0)):
        light.setColorAt(position, QColor(181, 222, 255, alpha))
    p.fillRect(rect, light)
    # The top-right reflection curls into the thickness of the glass.
    softbox = QRadialGradient(QPointF(rect.right()-28, rect.top()+20), width*.48)
    softbox.setColorAt(0, QColor(198, 231, 255, 38))
    softbox.setColorAt(.35, QColor(132, 199, 255, 17))
    softbox.setColorAt(1, QColor(132, 199, 255, 0))
    p.fillRect(rect, softbox)
    contrast = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    contrast.setColorAt(0, QColor(3, 17, 35, 0))
    contrast.setColorAt(.27, QColor(3, 17, 35, 30))
    contrast.setColorAt(.8, QColor(3, 17, 35, 15))
    contrast.setColorAt(1, QColor(3, 17, 35, 0))
    p.fillRect(rect, contrast)
    bottom = QRadialGradient(QPointF(rect.right()-42, rect.bottom()+36), width*.55)
    bottom.setColorAt(0, QColor(91, 207, 255, 28))
    bottom.setColorAt(1, QColor(91, 207, 255, 0))
    p.fillRect(rect, bottom)
    p.restore()

    # Recessed inner edge + luminous outer rim convey physical thickness.
    inner = QPainterPath()
    inner.addRoundedRect(rect.adjusted(3.3, 3.3, -3.3, -3.3), 19, 19)
    bevel = QLinearGradient(rect.topLeft(), rect.bottomRight())
    bevel.setColorAt(0, QColor(202, 241, 255, 102))
    bevel.setColorAt(.18, QColor(137, 214, 255, 33))
    bevel.setColorAt(.53, QColor(38, 108, 159, 16))
    bevel.setColorAt(.83, QColor(114, 222, 255, 55))
    bevel.setColorAt(1, QColor(194, 238, 255, 117))
    p.fillPath(path.subtracted(inner), bevel)
    rim = QLinearGradient(rect.topLeft(), rect.bottomRight())
    rim.setColorAt(0, QColor(192, 239, 255, 222))
    rim.setColorAt(.3, QColor(99, 190, 231, 130))
    rim.setColorAt(.66, QColor(55, 133, 183, 112))
    rim.setColorAt(1, QColor(157, 232, 255, 215))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(rim, 1.05))
    p.drawPath(path)
    p.setPen(QPen(QColor(185, 230, 255, 29), .65))
    p.drawPath(inner)
    p.end()
    return surface


def paint_glass(widget):
    # Activity colours and the glint do not invalidate the expensive material.
    key = (widget.width(), widget.height(), min(widget.devicePixelRatioF(), 2), widget.opaque)
    if getattr(widget, '_glass_material_key', None) != key:
        widget._glass_material = make_material(*key)
        widget._glass_material_key = key
    p = QPainter(widget)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if widget.isWindow():
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(widget.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    p.drawPixmap(0, 0, widget._glass_material)
    state = getattr(widget, '_activity', 'idle')
    rect = QRectF(widget.rect()).adjusted(10, 10, -10, -10)
    if state != 'idle':
        color = QColor(ACTIVITY[state][0])
        color.setAlpha(155)
        p.setPen(QPen(color, 1.15))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 22, 22)
    if state in MOVING:
        x = rect.left() + 28 + (rect.width() - 56) * getattr(widget, '_edge_phase', 0)
        p.setPen(QPen(QColor(ACTIVITY[state][0]), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x - 8, rect.top()), QPointF(x + 8, rect.top()))
    p.end()
