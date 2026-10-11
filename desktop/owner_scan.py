"""Native face-enrollment artwork; only detector observations are labelled as data."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class FaceScan(QWidget):
    def __init__(self, reduced_motion=False, parent=None):
        super().__init__(parent)
        self.setAccessibleName('LYA local face profile scan')
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.image, self.tracking = None, None
        self.feedback = ''
        self.sample, self.guiding, self.phase = 0, True, 0.
        self.reduced_motion = reduced_motion
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.hide()

    def tick(self):
        self.phase += .04
        self.update()

    def showEvent(self, event):
        if not self.reduced_motion:
            self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        self.image = self.tracking = None
        self.feedback = ''
        super().hideEvent(event)

    def set_capture(self, sample, guiding):
        self.sample, self.guiding = sample, guiding
        self.setAccessibleDescription(self.instruction())
        self.update()

    def instruction(self):
        return ('Look at the lens', 'Turn slightly to one side', 'Turn slightly to the other side')[min(2, self.sample)]

    def camera_rect(self):
        wide = self.width() >= 900 and self.height() >= 560
        left, right = (216, 194) if wide else (8, 8)
        top, reserve = (48, 80) if self.height() < 300 else (66, 138)
        available = QRectF(left, top, max(1, self.width()-left-right), max(1, self.height()-reserve))
        width = min(available.width(), available.height()*4/3)
        return QRectF(available.center().x()-width/2, available.center().y()-width*3/8, width, width*.75)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor('#06121a'))
        cyan, muted, amber = '#8de4eb', '#81949f', '#c9aa76'

        def text(x, y, content, size=11, color=muted):
            p.setFont(QFont('Segoe UI', size))
            p.setPen(QColor(color))
            p.drawText(QPointF(x, y), content)

        def line(x1, y1, x2, y2, color='#29434c', width=1):
            p.setPen(QPen(QColor(color), width))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        def ring(cx, cy, radius, start, span, color, width=1):
            p.setPen(QPen(QColor(color), width))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx-radius, cy-radius, radius*2, radius*2), round(start*16), round(span*16))

        wide = self.width() >= 900 and self.height() >= 560
        diamond=QPainterPath()
        diamond.moveTo(17,10)
        diamond.lineTo(27,22)
        diamond.lineTo(17,34)
        diamond.lineTo(7,22)
        diamond.closeSubpath()
        p.setPen(QPen(QColor(cyan),1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(diamond)
        text(42, 28, 'L  Y  A', 15, cyan)
        text(self.width()-140, 25, 'FACE SCAN MODE', 8 if self.width()<500 else 9, cyan)
        line(8, 43, self.width()-8, 43)
        view = self.camera_rect()
        frame = QRectF(216,66,self.width()-224,self.height()-138) if wide else view
        p.setBrush(QColor('#081219'))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(frame)
        path = QPainterPath()
        path.moveTo(frame.left()+18, frame.top())
        path.lineTo(frame.right()-18, frame.top())
        path.lineTo(frame.right(), frame.top()+18)
        path.lineTo(frame.right(), frame.bottom()-18)
        path.lineTo(frame.right()-18, frame.bottom())
        path.lineTo(frame.left()+18, frame.bottom())
        path.lineTo(frame.left(), frame.bottom()-18)
        path.lineTo(frame.left(), frame.top()+18)
        path.closeSubpath()
        p.save()
        p.setClipPath(path)
        if self.image is not None:
            p.drawImage(view, self.image)
            shade = QLinearGradient(view.topLeft(), view.bottomLeft())
            shade.setColorAt(0, QColor(3, 14, 21, 10))
            shade.setColorAt(1, QColor(3, 14, 21, 85))
            p.fillRect(view, shade)
        else:
            message = 'Voice guidance' if self.guiding else 'Waiting for camera frames'
            if view.width() < 220:
                message = 'Guiding…' if self.guiding else 'Camera…'
            text(view.left()+12, view.center().y(), message, 10, cyan)
        cx, cy = view.center().x(), view.center().y()
        radius = min(view.width()*.40, view.height()*.44)
        # Decorative arcs are not a depth map, liveness result or confidence score.
        for index in range(3):
            r = radius+index*7
            ring(cx, cy, r, 12+index*7, 142, '#36606a')
            ring(cx, cy, r, 198+index*3, 126, '#28434e')
        sweep = 70+math.degrees(self.phase)
        ring(cx, cy, radius+16, sweep, 32, amber, 1.4)
        ring(cx, cy, radius+16, sweep+180, 24, cyan, 1.4)
        for angle in range(0, 360, 15):
            a = math.radians(angle)
            r = radius+24
            line(cx+math.cos(a)*r, cy+math.sin(a)*r,
                 cx+math.cos(a)*(r+3), cy+math.sin(a)*(r+3), '#395965')
        tracking = self.tracking
        count = tracking['faces'] if tracking is not None else 0
        if self.image is not None and count == 1:
            x, y, w, h = tracking['box']
            face = QRectF(view.x()+x*view.width(), view.y()+y*view.height(), w*view.width(), h*view.height())
            for x, y, dx, dy in ((face.left(), face.top(), 1, 1), (face.right(), face.top(), -1, 1),
                                  (face.left(), face.bottom(), 1, -1), (face.right(), face.bottom(), -1, -1)):
                line(x, y, x+dx*18, y, cyan, 1.4)
                line(x, y, x, y+dy*18, cyan, 1.4)
            points = [QPointF(view.x()+x*view.width(), view.y()+y*view.height()) for x, y in tracking['points']]
            p.setPen(QPen(QColor(141, 228, 235, 65), .8))
            for a, b in ((0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 4)):
                p.drawLine(points[a], points[b])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#c4f6f4'))
            for point in points:
                p.drawEllipse(point, 2.3, 2.3)
        p.restore()
        p.setPen(QPen(QColor('#568590'), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        for x, y, dx, dy in ((frame.left()+18, frame.top(), 1, 1), (frame.right()-18, frame.bottom(), -1, -1)):
            line(x, y, x+dx*38, y, cyan, 1.8)
        progress = min(3, self.sample)
        if wide:
            text(8, 94, 'Identity scan', 21, '#e3edef')
            text(8, 123, 'One profile. Three views.', 10)
            text(8, 145, 'Processed on this laptop.', 10)
            labels = ('Phone verified', 'Camera preview', 'Facial landmarks', 'Profile samples', 'Voice profile next')
            details = ('Signed owner proof', 'Active · local only' if self.image is not None else 'Waiting for guidance',
                       'Five points located' if count == 1 else 'Keep only your face in view',
                       f'{progress} of 3 captured', 'Camera closes before voice')
            for index, (label, detail) in enumerate(zip(labels, details)):
                y = 200+index*62
                color = cyan if index == 0 or (index == 1 and self.image is not None) or (index == 2 and count == 1) else muted
                if index < 4:
                    line(20, y+14, 20, y+48)
                p.setPen(QPen(QColor(color), 1.2))
                p.setBrush(QColor('#112b34') if color == cyan else QColor('#0b171e'))
                p.drawEllipse(QPointF(20, y), 9, 9)
                text(42, y+4, label, 10, color)
                text(42, y+24, detail, 8)
            x = self.width()-174
            text(x, 99, 'CAMERA ACTIVE' if self.image is not None else 'CAMERA WAITING', 10, cyan)
            text(x, 123, 'RAM-only preview', 9)
            line(x, 146, self.width()-8, 146)
            text(x, 178, 'DETECTED FACES', 8)
            text(x, 211, '2+' if count == 2 else f'{count:02}', 24, amber if count != 1 else cyan)
            text(x, 252, 'LANDMARKS', 8)
            text(x, 285, '05' if count == 1 else '—', 24, cyan)
            text(x, 335, 'VIEWS CAPTURED', 8)
            text(x, 368, f'{progress} / 3', 24, cyan)
            for index in range(3):
                p.fillRect(QRectF(x+index*53, 386, 45, 3), QColor(cyan if index < progress else '#253a43'))
            text(x, 425, 'Phone = owner proof', 9, amber)
            text(x, 447, 'Face = local profile', 9)
        elif self.height() >= 300:
            text(10, 61, f'Face view {min(3, self.sample+1)} / 3', 9, cyan)
        y = self.height()-(49 if self.height() >= 300 else 17)
        line(8, y-12, self.width()-8, y-12)
        instruction = self.feedback or self.instruction()
        if self.image is not None and count == 2:
            instruction = 'Keep only your face in view'
        elif self.image is not None and count == 0:
            instruction = 'Move your face into view'
        text(10, y+9, instruction, 13 if self.width() >= 600 else 10, '#d6eaeb')
        if self.width() >= 600:
            text(10, y+31, 'Local capture · no photos saved · Escape or × cancels · spoken commands paused', 9)
