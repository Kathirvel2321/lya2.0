"""LYA's native crystal and glass panel. Run launch-lya.ps1 from the project root.

Person/task previews are cosmetic. Default launch has a guest brain and local
microphone wake; --no-voice disables it. Camera enrollment remains separate.
"""
import argparse
import math
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import (Qt, QPoint, QPointF, QRect, QRectF, QSize, QTimer, Signal, Property,
                            QEasingCurve, QPropertyAnimation, QObject, QRunnable, QThreadPool,
                            QLockFile, QStandardPaths)
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QImage, QImageReader, QKeySequence, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient,
                           QShortcut, QRegion, QTextCursor, QTextBlockFormat, QTextCharFormat)
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QTextBrowser, QListWidget, QListWidgetItem,
                               QStackedWidget, QMenu, QSystemTrayIcon)

from layout import Box, PERSON_COLORS, TASK_COLORS, accent, place_panel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCUMENTS = ("LYA_FOUNDATION_DECISIONS.md", "LYA_REBUILD_PLAN.md", "LYA_VISION.md", "README.md")
WINDOW_FLAGS = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
MIC_COMMANDS = ("can you hear me", "can you hear me now", "are you hearing me", "mic test",
                "microphone test", "mic check", "microphone check", "test microphone", "test mic")
MIC_TEST_SECONDS = 5


def box(rect):
    return Box(rect.x(), rect.y(), rect.width(), rect.height())


def crystal_pixmap(path):
    """Display the unchanged artwork through its silhouette; no background square.

    The outline is in the user's 1254px reference coordinates. This is a native
    paint clip, not a generated replacement or a per-frame segmentation model.
    """
    source = QPixmap(str(path))
    if source.isNull():
        raise RuntimeError(f"Crystal artwork missing: {path}")
    outline = [(695,44),(738,103),(797,340),(852,220),(857,226),(888,431),
               (901,468),(927,559),(950,601),(974,534),(979,537),(976,568),
               (971,635),(945,687),(923,723),(908,748),(893,747),(884,770),
               (862,747),(847,781),(821,827),(783,876),(752,914),(717,973),
               (681,1075),(640,1101),(621,1097),(568,1026),(509,994),(481,952),
               (456,922),(427,874),(399,843),(379,780),(355,805),(341,778),
               (302,692),(273,635),(240,577),(249,556),(257,556),(326,588),
               (319,535),(312,494),(280,449),(287,437),(334,403),(391,361),
               (476,326),(496,295),(495,246),(542,210),(579,157),(622,102),
               (663,68),(684,64)]
    canvas = QPixmap(1254, 1254)
    canvas.fill(Qt.GlobalColor.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    shape = QPainterPath()
    from PySide6.QtCore import QPointF
    shape.addPolygon(QPolygonF([QPointF(x, y) for x, y in outline]))
    shape.closeSubpath()
    p.setClipPath(shape)
    p.drawPixmap(QRect(0, 0, 1254, 1254), source)
    p.end()
    return canvas.copy(225, 35, 770, 1085).scaled(288, 408, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)


def tinted(source, color):
    result = source.copy()
    p = QPainter(result)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    c = QColor(color)
    c.setAlpha(38)
    p.fillRect(result.rect(), c)
    p.end()
    return result


class Crystal(QWidget):
    activated = Signal()
    relocated = Signal()
    menu_requested = Signal(QPoint)
    artwork_changed = Signal(bool)
    motion_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent, WINDOW_FLAGS if parent is None else Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("LYA · crystal")
        self.setAccessibleName("LYA crystal. Click to open. Right click for controls.")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(184, 252)
        self.original = QPixmap(str(HERE / "assets" / "lya-reference-body.png"))
        if self.original.isNull():
            raise RuntimeError("Approved LYA body artwork missing or unreadable")
        self.original = self.original.scaled(288, 408, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
        self.model_art = QPixmap()
        baked = HERE / "assets" / "obsidian-baked.png"
        reader = QImageReader(str(baked))
        if baked.is_file() and baked.stat().st_size <= 1_000_000 and reader.size() == QSize(288, 408):
            self.model_art = QPixmap.fromImage(reader.read())
        self.using_model = False  # Keep the measured lower-CPU original as the default.
        self.base = self.model_art if self.using_model else self.original
        self.frames = {c: tinted(self.base, c) for c in set(PERSON_COLORS.values()) | set(filter(None, TASK_COLORS.values()))}
        self.person, self.task = "guest", "idle"
        self.color = QColor(accent(self.person, self.task))
        self.start_color = QColor(self.color)
        self.target_color = QColor(self.color)
        self.previous = self.frames[self.color.name()]
        self.current = self.previous
        self.mix = 1.0
        self.reduced_motion = False
        self.started = time.monotonic()
        self.motion_until = self.started + 3.0
        self.phase = 0.0
        self.voice_phase = 'off'
        self.voice_level = 0.0
        self._press = None
        self._dragged = False
        self.paint_samples = []
        self.animation = QPropertyAnimation(self, b"blend", self)
        self.animation.setDuration(420)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(33)  # 30Hz only during a three-second interaction burst
        self.timer.timeout.connect(self.tick)
        mask = QRegion(15, 4, 154, 216, QRegion.RegionType.Ellipse) | QRegion(10, 209, 164, 38)
        self.setMask(mask)

    def set_artwork(self, enabled):
        self.using_model = bool(enabled and not self.model_art.isNull())
        self.base = self.model_art if self.using_model else self.original
        self.frames = {c: tinted(self.base, c) for c in set(PERSON_COLORS.values()) | set(filter(None, TASK_COLORS.values()))}
        self.animation.stop()
        self.previous = self.current = self.frames[accent(self.person, self.task)]
        self.start_color = self.target_color = QColor(accent(self.person, self.task))
        self.set_blend(1.0)
        self.paint_samples.clear()
        self.artwork_changed.emit(self.using_model)
        self.animate_briefly()

    def animate_briefly(self):
        if not self.reduced_motion and self.isVisible() and not self.timer.isActive():
            self.started = time.monotonic()
            self.phase = 0.0
            self.motion_until = self.started + 3.0
            self.timer.start()

    def low_power_fallback(self):
        if self.using_model:
            self.set_artwork(False)
        self.set_reduced_motion(True)

    def enterEvent(self, event):
        self.animate_briefly()
        super().enterEvent(event)

    def get_blend(self):
        return self.mix

    def set_blend(self, value):
        self.mix = value
        self.color = QColor(*(round(a + (b - a) * value) for a, b in zip(self.start_color.getRgb()[:3], self.target_color.getRgb()[:3])))
        self.update()

    blend = Property(float, get_blend, set_blend)

    def set_state(self, person=None, task=None):
        if person is not None:
            if person not in PERSON_COLORS:
                raise ValueError("Unknown presentation palette")
            self.person = person
        if task is not None:
            if task not in TASK_COLORS:
                raise ValueError("Unknown task state")
            self.task = task
        target = self.frames[accent(self.person, self.task)]
        # Capture the current blend once so quick changes do not flash backward.
        combined = QPixmap(self.current.size())
        combined.fill(Qt.GlobalColor.transparent)
        p = QPainter(combined)
        p.drawPixmap(0, 0, self.previous)
        p.setOpacity(self.mix)
        p.drawPixmap(0, 0, self.current)
        p.end()
        self.previous, self.current = combined, target
        self.start_color = QColor(self.color)
        self.target_color = QColor(accent(self.person, self.task))
        self.animation.stop()
        if self.reduced_motion or not self.isVisible():
            self.set_blend(1.0)
        else:
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
        self.animate_briefly()

    def set_reduced_motion(self, enabled):
        self.reduced_motion = enabled
        self.animation.stop()
        self.set_blend(1.0)
        if enabled:
            self.timer.stop()
            self.phase = 0
        elif self.isVisible():
            self.animate_briefly()
        self.update()
        self.motion_changed.emit(enabled)

    def tick(self):
        now = time.monotonic()
        self.phase = now - self.started
        if self.voice_phase in ('listening', 'hearing'):
            from audio import voice
            self.voice_level = voice.listener_health()['level']
        if now >= self.motion_until and self.voice_phase not in ('listening', 'hearing', 'thinking', 'speaking'):
            self.timer.stop()
            self.phase = 0.0
        self.update()

    def set_voice_phase(self, phase):
        if phase == self.voice_phase:
            return
        self.voice_phase = phase
        names = {'standby': 'Waiting for LYA or two claps', 'listening': 'Listening for your question',
                 'hearing': 'Hearing your question', 'thinking': 'Thinking',
                 'speaking': 'Speaking. Say stop to interrupt', 'uncertain': 'Please repeat your question',
                 'off': 'Voice off'}
        label = names.get(phase, phase)
        self.setAccessibleName('LYA. ' + label)
        self.setToolTip(label)
        self.animate_briefly()
        self.update()

    def paint_docked_crystal(self, painter, side):
        phase = self.voice_phase
        if self.task in ('approval', 'error'):
            cue = self.task
        elif phase in ('listening', 'hearing', 'thinking', 'speaking', 'uncertain'):
            cue = phase
        else:
            cue = self.task
        hue = QColor({
            'listening': '#68e5f2', 'hearing': '#68e5f2',
            'thinking': '#b69bff', 'speaking': '#78e1bf', 'uncertain': '#ff879b',
        }.get(cue) or accent(self.person, cue))
        time_in_state = 0 if self.reduced_motion else self.phase
        cycle = .5 + .5 * math.sin(time_in_state * 3)
        source_height = 108 if side <= 128 else 256
        source_key = self.base.cacheKey(), source_height
        if getattr(self, '_docked_source_key', None) != source_key:
            source = self.base
            if not self.using_model:
                # The approved render includes transparent margins around the crystal.
                source = source.copy(round(source.width() * .22), round(source.height() * .04),
                                     round(source.width() * .56), round(source.height() * .92))
            self._docked_source = source.scaledToHeight(
                source_height, Qt.TransformationMode.SmoothTransformation).toImage()
            self._docked_source_key = source_key

        glow = QRadialGradient(0, 2, side * .46)
        hue.setAlpha(30 if cue == 'idle' else 55)
        glow.setColorAt(0, hue)
        hue.setAlpha(0)
        glow.setColorAt(1, hue)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(-side / 2, -side / 2, side, side))

        body = self._docked_source.copy()
        width, height = body.width(), body.height()
        if cue in ('thinking', 'files'):
            position = .23 + .54 * (cycle if cue == 'thinking' else 1 - cycle)
            reflection = QLinearGradient(width * .16, height * (position - .22),
                                         width * .82, height * (position + .22))
            peak, strength = .51, 156 if cue == 'thinking' else 146
        elif cue == 'speaking':
            reflection = QLinearGradient(0, height * .72, width, height * .28)
            peak, strength = .25 + .5 * cycle, 166
        else:
            reflection = QLinearGradient(0, height * .19, width, height * .82)
            peak, strength = .51, 72 if cue == 'idle' else 205
            if cue in ('listening', 'hearing'):
                strength = round(115 + 90 * max(cycle, min(1, self.voice_level)))

        reflection.setColorAt(0, hue)
        reflection.setColorAt(1, hue)
        hue.setAlpha(strength // 4)
        reflection.setColorAt(peak - .17, hue)
        reflection.setColorAt(peak + .17, hue)
        hue.setAlpha(strength)
        reflection.setColorAt(peak, hue)
        surface = QPainter(body)
        surface.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        surface.fillRect(body.rect(), reflection)
        surface.end()
        h = side * .84
        w = h * width / height
        painter.drawImage(QRectF(-w / 2, -h / 2, w, h), body, QRectF(body.rect()))

    def showEvent(self, event):
        if not self.reduced_motion:
            self.animate_briefly()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        self.animation.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        start = time.perf_counter()
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        # Explicit alpha clear prevents trails in a translucent native window.
        if self.isWindow():
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.scale(self.width() / 184, self.height() / 252)
        morph = getattr(self, 'circle_mix', 0.0)
        p.setOpacity(1 - morph)
        # One complete gentle movement ends at its starting position.
        drift = 0 if self.reduced_motion else math.sin(min(self.phase / 3.0, 1) * math.tau) * 2.2
        glow = QRadialGradient(92, 116, 86)
        c = QColor(self.color)
        c.setAlpha(44)
        glow.setColorAt(0, c)
        c.setAlpha(0)
        glow.setColorAt(1, c)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(6, 24, 172, 182))
        destination = QRectF(23, 4 + drift, 138, 195)
        spin = getattr(self, 'spin_frame', None)
        p.drawPixmap(destination, spin if spin is not None else self.previous, QRectF(self.previous.rect()))
        p.setOpacity(self.mix * (1 - morph))
        p.drawPixmap(destination, spin if spin is not None else self.current, QRectF(self.current.rect()))
        p.setOpacity(1 - morph)
        # A quiet plinth and suspended facet give the original artwork an anchor.
        c = QColor(self.color)
        c.setAlpha(110)
        p.setPen(QPen(c, .8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(QPolygonF([QPointF(62, 196), QPointF(92, 187),
                                QPointF(122, 196), QPointF(92, 203)]))
        p.drawLine(QPointF(92, 199), QPointF(92, 206))
        if self.width() <= 88:
            p.setOpacity(0)  # Keep the docked crystal clear of unreadably small labels.
        p.setBrush(QColor(12, 20, 30, 235))
        p.setPen(QPen(QColor(180, 205, 220, 95), 1))
        p.drawRoundedRect(QRectF(24, 214, 136, 25), 6, 6)
        p.setPen(self.color)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        label = "L Y A" if self.task == "idle" else "LYA  /  " + self.task.upper()
        p.drawText(QRectF(15, 211, 154, 31), Qt.AlignmentFlag.AlignCenter, label)
        if morph:
            p.resetTransform()
            p.setOpacity(morph)
            p.translate(self.width() / 2, self.height() / 2)
            self.paint_docked_crystal(p, min(self.width(), self.height()))
        p.end()
        self.paint_samples.append((time.perf_counter() - start) * 1000)
        self.paint_samples = self.paint_samples[-600:]
        if self.using_model and len(self.paint_samples) >= 30 and sum(self.paint_samples[-30:]) / 30 > 8:
            QTimer.singleShot(0, self.low_power_fallback)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.menu_requested.emit(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._origin = self.pos()
            self._dragged = False

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        delta = event.globalPosition().toPoint() - self._press
        if delta.manhattanLength() > QApplication.startDragDistance():
            self._dragged = True
        if self._dragged:
            proposed = self._origin + delta
            screen = QApplication.screenAt(event.globalPosition().toPoint()) or self.screen()
            area = screen.availableGeometry()
            self.move(max(area.left(), min(proposed.x(), area.right() - self.width() + 1)),
                      max(area.top(), min(proposed.y(), area.bottom() - self.height() + 1)))
            self.relocated.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._press is not None:
            if not self._dragged:
                self.activated.emit()
            self._press = None

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Space):
            self.activated.emit()
        else:
            super().keyPressEvent(event)


class ResponseText(QTextBrowser):
    """Format plain text with native paragraph styles; never interpret reply HTML."""

    def setPlainText(self, text):
        normal = QTextCharFormat()
        normal.setFontWeight(QFont.Weight.Normal)
        normal.setForeground(QColor('#d8e2e8'))
        self.setCurrentCharFormat(normal)
        super().setPlainText(text)
        block = self.document().begin()
        while block.isValid():
            cursor = QTextCursor(block)
            paragraph = QTextBlockFormat()
            paragraph.setLineHeight(143, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            paragraph.setRightMargin(10)
            cursor.setBlockFormat(paragraph)
            line = block.text()
            prefix = next((part for part in ('You asked:', 'You:', 'LYA:') if line.startswith(part)), '')
            if prefix:
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(prefix))
                style = QTextCharFormat()
                style.setFontWeight(QFont.Weight.DemiBold)
                style.setForeground(QColor('#9dd7df' if prefix == 'LYA:' else '#b8c2cb'))
                cursor.mergeCharFormat(style)
            block = block.next()
        # Subsequent streamed caption text inherits the normal response style.
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(normal)
        self.setTextCursor(cursor)
        self.moveCursor(QTextCursor.MoveOperation.Start)


class GlassPanel(QWidget):
    submitted = Signal(str)
    dismissed = Signal()
    files_requested = Signal()
    document_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, WINDOW_FLAGS if parent is None else Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("LYA · conversation")
        self.resize(480, 510)
        self.color = QColor("#9cdfe8")
        self.opaque = False
        self.setStyleSheet("""
            /* Hallmark · component: conversation panel · genre: atmospheric · theme: LYA glass
               Pre-emit critique: P4 H5 E4 S4 R5 V4 */
            QWidget { color: #eaf1f5; font-family: 'Segoe UI'; font-size: 13px; }
            QLabel { background: transparent; }
            QLabel#panelBrand { color: #f1f7fa; font-size: 16px; font-weight: 700; letter-spacing: 1px; }
            QLabel#panelStatus, QLabel#panelFootnote, QLabel#panelContext { color: #c4d3dc; font-size: 11px; }
            QLabel#panelTitle { color: #f1f7fa; font-size: 25px; font-weight: 600; }
            QPushButton { background: transparent; border: 1px solid transparent;
                border-radius: 7px; padding: 6px 9px; color: #c4d3dc; }
            QPushButton:hover { background: rgba(175,216,233,22); color: #f1f7fa; }
            QPushButton:pressed { background: rgba(175,216,233,38); }
            QPushButton:disabled { color: #8195a0; }
            QPushButton#panelClose { padding: 0; font-size: 19px; }
            QPushButton#panelSend { background: #c4e8f0; color: #102733;
                border: 1px solid transparent; border-radius: 10px; padding: 0 14px;
                font-weight: 600; }
            QPushButton#panelSend:hover { background: #e1f5f8; }
            QPushButton#panelSend:pressed { background: #a3ccd9; }
            QPushButton#panelSend:disabled { background: #405560; color: #b7ccd7; }
            QLineEdit { background: rgba(9,18,26,188); border: 1px solid rgba(178,213,229,66);
                border-radius: 10px; padding: 0 13px; selection-background-color: #296882;
                placeholder-text-color: #9fb4c1; }
            QLineEdit:hover { border-color: #7898a8; }
            QTextBrowser { background: transparent; border: 1px solid transparent;
                border-radius: 6px; color: #d8e2e8; font-size: 15px; selection-background-color: #296882; }
            QListWidget { background: transparent; border: 1px solid transparent; border-radius: 6px; }
            QListWidget::item { background: rgba(175,216,233,12); border: 1px solid rgba(175,216,233,32);
                border-radius: 8px; padding: 0; margin-bottom: 8px; }
            QListWidget::item:hover { background: rgba(175,216,233,22); }
            QListWidget::item:selected { background: #224153; border-color: #90d7e5; }
            QPushButton:focus, QPushButton#panelSend:focus, QLineEdit:focus,
                QTextBrowser:focus, QListWidget:focus { border-color: #a9e3f1; }
            QPushButton#panelSend:focus { border-color: #284c61; }
            QScrollBar:vertical { background: transparent; width: 5px; margin: 0; }
            QScrollBar::handle:vertical { background: #6d8a9a; border-radius: 2px; min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 23, 30, 24)
        outer.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(10)
        brand = QLabel("LYA")
        brand.setObjectName("panelBrand")
        header.addWidget(brand)
        header.addStretch()
        self.state_label = QLabel("Conversation")
        self.state_label.setObjectName("panelStatus")
        header.addWidget(self.state_label)
        close = QPushButton("×")
        close.setObjectName("panelClose")
        close.setFixedSize(32, 32)
        close.setAccessibleName("Close result panel")
        close.setToolTip("Close panel · Escape")
        close.clicked.connect(self.dismissed)
        header.addWidget(close)
        outer.addLayout(header)
        self.eyebrow = QLabel("Read-only")
        self.eyebrow.setObjectName("panelContext")
        outer.addWidget(self.eyebrow)
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("panelTitle")
        outer.addWidget(self.title_label)
        self.stack = QStackedWidget()
        self.answer = ResponseText()
        self.answer.document().setDocumentMargin(1)
        self.answer.setOpenExternalLinks(False)
        self.answer.setOpenLinks(False)
        self.answer.setAccessibleName("LYA response")
        self.files = QListWidget()
        self.files.setAccessibleName("Project documents. Press Enter to preview a selected document.")
        self.files.itemActivated.connect(lambda item: self.document_requested.emit(item.data(Qt.ItemDataRole.UserRole)))
        self.stack.addWidget(self.answer)
        self.stack.addWidget(self.files)
        outer.addWidget(self.stack, 1)
        quick = QHBoxLayout()
        quick.setSpacing(4)
        show_files = QPushButton("Project files")
        show_files.clicked.connect(self.files_requested)
        quick.addWidget(show_files)
        for label, command in (("Colors", "colors"), ("Help", "help")):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, c=command: self.submitted.emit(c))
            quick.addWidget(button)
        quick.addStretch()
        outer.addLayout(quick)
        composer = QHBoxLayout()
        composer.setSpacing(8)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Ask LYA")
        self.entry.setAccessibleName("Type a command to LYA")
        self.entry.setMaxLength(2000)
        self.entry.setFixedHeight(44)
        self.entry.returnPressed.connect(self.send)
        composer.addWidget(self.entry, 1)
        send = QPushButton("Send")
        send.setObjectName("panelSend")
        send.setAccessibleName("Send command")
        send.setFixedHeight(44)
        send.clicked.connect(self.send)
        composer.addWidget(send)
        outer.addLayout(composer)
        self.footnote = QLabel("Camera and microphone off")
        self.footnote.setWordWrap(True)
        self.footnote.setObjectName("panelFootnote")
        outer.addWidget(self.footnote)
        self.show_answer("How can I help?", "Ask LYA a question or open Project files to browse your saved plans.\n\nDrag the crystal to move it. Right-click it for voice, appearance and other controls.")

    def send(self):
        text = self.entry.text().strip()
        self.entry.clear()
        if text:
            self.submitted.emit(text)

    def show_answer(self, title, message):
        self.title_label.setText(title)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.stack.setCurrentWidget(self.answer)
        self.answer.setPlainText(message)
        self.eyebrow.hide()

    def show_documents(self):
        self.title_label.setText("Project documents")
        self.eyebrow.show()
        self.files.clear()
        labels = {"LYA_FOUNDATION_DECISIONS.md": "Foundation decisions", "LYA_REBUILD_PLAN.md": "The rebuild plan",
                  "LYA_VISION.md": "The LYA vision", "README.md": "Project guide"}
        for name in DOCUMENTS:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, labels[name] + ", " + name)
            item.setSizeHint(QSize(340, 60))
            self.files.addItem(item)
            row = QWidget()
            row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(16, 8, 12, 8)
            row_layout.setSpacing(3)
            title = QLabel(labels[name])
            title.setStyleSheet("color: #edf4f8; font-size: 13px; font-weight: 600;")
            filename = QLabel(name)
            filename.setStyleSheet("color: #afc5d4; font-size: 10px;")
            row_layout.addWidget(title)
            row_layout.addWidget(filename)
            self.files.setItemWidget(item, row)
        self.stack.setCurrentWidget(self.files)
        self.files.setCurrentRow(0)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isWindow():
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        body = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        # One deeper cut gives the rim the same silhouette on light and dark desktops.
        path = QPainterPath()
        path.moveTo(body.left() + 11, body.top())
        path.lineTo(body.right() - 24, body.top())
        path.lineTo(body.right(), body.top() + 24)
        path.lineTo(body.right(), body.bottom() - 11)
        path.lineTo(body.right() - 11, body.bottom())
        path.lineTo(body.left() + 11, body.bottom())
        path.lineTo(body.left(), body.bottom() - 11)
        path.lineTo(body.left(), body.top() + 11)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.save()
        p.translate(0, 3)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for width, alpha in ((8, 14), (5, 22), (2, 33)):
            p.setPen(QPen(QColor(2, 9, 17, alpha), width))
            p.drawPath(path)
        p.restore()
        glass = QLinearGradient(body.topLeft(), body.bottomRight())
        glass.setColorAt(0.0, QColor(22, 42, 57, 255 if self.opaque else 225))
        glass.setColorAt(0.52, QColor(12, 26, 39, 255 if self.opaque else 237))
        glass.setColorAt(1.0, QColor(15, 33, 47, 255 if self.opaque else 231))
        p.setBrush(glass)
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        reflection = QLinearGradient(body.topLeft(), QPointF(body.center().x(), body.bottom()))
        reflection.setColorAt(0.0, QColor(185, 224, 244, 36))
        reflection.setColorAt(0.65, QColor(185, 224, 244, 0))
        p.fillRect(body, reflection)
        p.restore()
        rim = QLinearGradient(body.topRight(), body.bottomLeft())
        highlight = QColor(self.color)
        highlight.setAlpha(200)
        rim.setColorAt(0.0, highlight)
        rim.setColorAt(0.21, QColor(187, 220, 236, 133))
        rim.setColorAt(0.61, QColor(148, 185, 203, 51))
        rim.setColorAt(1.0, QColor(148, 185, 203, 98))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(rim, 1.1))
        p.drawPath(path)
        p.setPen(QPen(QColor(199, 230, 245, 42), 1))
        p.drawLine(QPointF(body.left() + 13, body.top() + 2),
                   QPointF(body.right() - 25, body.top() + 2))
        if self.state_label.isVisible():
            header = self.layout().itemAt(0).layout().geometry()
            p.setPen(QPen(QColor(187, 220, 236, 40), 1))
            y = header.bottom() + 5
            p.drawLine(header.left(), y, header.right(), y)
        p.end()


class ReadSignals(QObject):
    finished = Signal(int, str, str, bool)


class VoiceSignals(QObject):
    wake_detected = Signal(str, bool)
    status = Signal(str)
    phase = Signal(str)
    retry = Signal(str, bool)


class BrainSignals(QObject):
    finished = Signal(int, object)


class BrainJob(QRunnable):
    def __init__(self, brain, text, cancelled, generation, signals):
        super().__init__()
        self.brain, self.text, self.cancelled = brain, text, cancelled
        self.generation, self.signals = generation, signals

    def run(self):
        from brain.workflow import Answer
        try:
            if self.text.casefold().strip() == "brain demo":
                import subprocess
                executable = Path(sys.executable)
                if executable.name.lower() == "pythonw.exe":
                    executable = executable.with_name("python.exe")
                p = subprocess.run([str(executable), "-B", str(ROOT / "brain/demo.py")],
                                   capture_output=True, text=True, encoding="utf-8", timeout=20,
                                   env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"},
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                answer = Answer(p.stdout if p.returncode == 0 else "The isolated demo failed. Run brain/demo.py to inspect it.", "demo")
            else:
                answer = self.brain.respond(self.text, self.cancelled)
        except Exception:
            answer = Answer("The brain request failed safely.", "error")
        if self.cancelled.is_set():
            self.brain.clear_temporary()
        self.signals.finished.emit(self.generation, answer)


class ReadDocument(QRunnable):
    def __init__(self, generation, name, signals):
        super().__init__()
        self.generation, self.name, self.signals = generation, name, signals

    def run(self):
        try:
            text = read_project_document(self.name)
            self.signals.finished.emit(self.generation, self.name, text, True)
        except Exception as exc:
            self.signals.finished.emit(self.generation, "Could not read that file", str(exc), False)


def read_project_document(name):
    if name not in DOCUMENTS:
        raise PermissionError("Only the listed project documents can be previewed here.")
    path = (ROOT / name).resolve()
    if path.parent != ROOT:
        raise PermissionError("The document resolves outside the project.")
    with path.open("r", encoding="utf-8-sig") as source:
        text = source.read(64001)
    return text[:64000] + ("\n\n[Preview limited to 64,000 characters.]" if len(text) > 64000 else "")


class Desktop(QObject):
    panel_type = GlassPanel

    def __init__(self, application, reduced_motion=False):
        super().__init__()
        self.app = application
        self.orb = Crystal()
        self.panel = self.panel_type()
        self.generation = 0
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        from brain.workflow import Brain
        from brain.research import default_researcher
        import threading
        self.brain = Brain(researcher=default_researcher())
        from cloud.desktop_connections import CHAT, CHAT_CHOICE, PublicModel
        from security import provider_credentials
        provider = provider_credentials.read(CHAT_CHOICE)
        if provider in CHAT:
            self.brain.client = PublicModel(provider)
        from brain.oracle import OracleModel
        if isinstance(self.brain.client, OracleModel):
            self.panel.footnote.setText("CLOUD TEXT  ·  CAMERA & MICROPHONE OFF")
        self.brain_busy = False
        self.brain_cancel = threading.Event()
        self.brain_signals = BrainSignals(self)
        self.brain_signals.finished.connect(self.on_brain)
        self.signals = ReadSignals(self)
        self.signals.finished.connect(self.on_document)
        self.voice_signals = VoiceSignals(self)
        self.voice_signals.wake_detected.connect(self.on_voice)
        self.voice_signals.status.connect(self.on_voice_status)
        self.voice_signals.phase.connect(self.on_voice_phase)
        self.voice_signals.retry.connect(self.on_voice_retry)
        self.voice_thread = None
        self.voice_stop_event = None
        self._voice_restart = 0
        self.cloud_voice = False
        self.cloud_asr = 'groq'
        self._mic_test_timer = None
        self.orb.activated.connect(self.toggle_panel)
        self.orb.relocated.connect(self.position_panel)
        self.orb.menu_requested.connect(self.open_menu)
        self.panel.dismissed.connect(self.close_panel)
        self.panel.submitted.connect(self.command)
        self.panel.files_requested.connect(self.show_files)
        self.panel.document_requested.connect(self.read_document)
        self.motion = QPropertyAnimation(self.panel, b"pos", self)
        self.motion.setDuration(260)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade = QPropertyAnimation(self.panel, b"windowOpacity", self)
        self.fade.setDuration(210)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.shortcuts = []
        for widget in (self.orb, self.panel):
            for keys, callback in (("Escape", self.close_panel), ("Ctrl+Q", self.quit), ("Ctrl+M", self.toggle_motion)):
                shortcut = QShortcut(QKeySequence(keys), widget)
                shortcut.activated.connect(callback)
                self.shortcuts.append(shortcut)
        self.orb.set_reduced_motion(reduced_motion)
        self.tray = QSystemTrayIcon(QIcon(self.orb.base), self)
        self.orb.artwork_changed.connect(lambda _: self.tray.setIcon(QIcon(self.orb.base)))
        self.tray.setToolTip("LYA · native interface preview")
        self.tray.activated.connect(lambda reason: self.wake() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.menu = self.make_menu()
        self.tray.setContextMenu(self.menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.orb.screen().availableGeometryChanged.connect(self.recenter)
        self.app.screenRemoved.connect(lambda *_: self.recenter())
        self.recenter()
        from desktop.news import NewsController
        self.news = NewsController(self)

    def show_technology_updates(self):
        self.news.show_brief()

    def show_routine_drafts(self):
        from desktop.routines import RoutineDialog
        if getattr(self, 'routine_dialog', None) is None:
            self.routine_dialog = RoutineDialog()
        self.routine_dialog.show()
        self.routine_dialog.raise_()
        self.routine_dialog.activateWindow()

    def show_connections(self):
        from desktop.connections import ConnectionsDialog
        dialog = ConnectionsDialog()
        dialog.exec()

    def make_menu(self):
        menu = QMenu()
        menu.addAction("Open LYA", self.wake)
        menu.addAction("Technology updates", self.show_technology_updates)
        menu.addAction("Routine drafts", self.show_routine_drafts)
        if sys.platform == "win32":
            menu.addAction("Connections…", self.show_connections)
        menu.addAction("Project files", self.show_files)
        menu.addAction("Sign in / register admin", lambda: self.command("register admin"))
        review_visitors = getattr(self, 'review_visitors', None)
        if review_visitors is not None:
            menu.addAction("Review visitors", review_visitors)
        model_art = QAction("Use 3D model artwork (baked, experimental)", menu, checkable=True)
        model_art.setChecked(self.orb.using_model)
        model_art.setEnabled(not self.orb.model_art.isNull())
        model_art.toggled.connect(self.orb.set_artwork)
        def reflect_artwork(enabled):
            model_art.blockSignals(True)
            model_art.setChecked(enabled)
            model_art.blockSignals(False)
        self.orb.artwork_changed.connect(reflect_artwork)
        menu.addAction(model_art)
        persons = menu.addMenu("Preview person color (no authentication)")
        for person in PERSON_COLORS:
            persons.addAction(person.title(), lambda checked=False, p=person: self.set_state(person=p))
        tasks = menu.addMenu("Preview task color")
        for task in TASK_COLORS:
            tasks.addAction(task.title(), lambda checked=False, t=task: self.set_state(task=t))
        menu.addSeparator()
        self.voice_action = QAction("Voice wake", menu, checkable=True)
        self.voice_action.setChecked(self.voice_thread is not None and self.voice_thread.is_alive())
        self.voice_action.toggled.connect(lambda checked: self.start_voice(self.cloud_voice) if checked else self.stop_voice())
        menu.addAction(self.voice_action)
        menu.addAction('Use Windows Voice Access input', self.prepare_system_dictation)
        self.microphone_menu = menu.addMenu("Microphone")
        self.microphone_menu.aboutToShow.connect(self.refresh_microphones)
        recognition = menu.addMenu('Command recognition (local)')
        for label, engine in [('Whisper English (experimental)', 'whisper'), ('Legacy Vosk', 'vosk')]:
            recognition.addAction(label, lambda checked=False, value=engine: self.select_command_asr(value))
        menu.addAction("Microphone self-test", self.microphone_self_test)
        self.motion_action = QAction("Reduce motion", menu, checkable=True)
        self.motion_action.setChecked(self.orb.reduced_motion)
        self.motion_action.toggled.connect(self.orb.set_reduced_motion)
        self.orb.motion_changed.connect(self.motion_action.setChecked)
        menu.addAction(self.motion_action)
        opaque = QAction("Opaque panel for maximum readability", menu, checkable=True)
        opaque.toggled.connect(self.set_opaque)
        menu.addAction(opaque)
        menu.addAction("Recenter crystal", self.recenter)
        menu.addAction("Sleep", self.sleep)
        menu.addAction("Quit LYA", self.quit)
        return menu

    def refresh_microphones(self):
        """List input metadata only. Opening the menu never starts recording."""
        self.microphone_menu.clear()
        selected = os.environ.get('LYA_MICROPHONE', '')
        choices = [('Follow Windows default', '')]
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            native = [d['name'] for d in devices if d['max_input_channels'] and
                      sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI']
            choices.extend((name, name) for name in dict.fromkeys(native))
        except Exception:
            self.microphone_menu.addAction('Input list unavailable').setEnabled(False)
        for label, name in choices:
            action = QAction(label, self.microphone_menu, checkable=True)
            action.setChecked(selected == name)
            action.triggered.connect(lambda checked=False, value=name: self.select_microphone(value))
            self.microphone_menu.addAction(action)

    def select_command_asr(self, engine):
        from audio import local_whisper
        if engine == 'whisper' and not local_whisper.available():
            self.panel.footnote.setText('WHISPER MODEL MISSING · RUN THE LOCAL MODEL SETUP')
            return
        os.environ['LYA_COMMAND_ASR'] = engine
        self.panel.footnote.setText('LOCAL COMMAND RECOGNIZER SELECTED · APPLIES TO NEXT QUESTION')

    def prepare_system_dictation(self):
        """Accept OS dictation in the existing composer; never opens a microphone."""
        self.stop_voice()
        self.voice_action.blockSignals(True)
        self.voice_action.setChecked(False)
        self.voice_action.blockSignals(False)
        self.wake()
        self.panel.entry.setFocus()
        self.panel.footnote.setText('WINDOWS VOICE ACCESS INPUT · SAY PRESS ENTER TO SEND')

    def select_microphone(self, name):
        """Session-only choice; wait for the old reader before restarting it."""
        if name:
            os.environ['LYA_MICROPHONE'] = name
        else:
            os.environ.pop('LYA_MICROPHONE', None)
        was_running = bool(self.voice_thread and self.voice_thread.is_alive())
        self.stop_voice()
        generation = self._voice_restart
        self.panel.footnote.setText('MICROPHONE SELECTED · VOICE RESTARTING' if was_running else
                                    'MICROPHONE SELECTED · VOICE OFF')
        if not was_running:
            return
        def restart():
            if generation != self._voice_restart:
                return
            if self.voice_thread and self.voice_thread.is_alive():
                QTimer.singleShot(50, restart)
            else:
                self.start_voice(self.cloud_voice)
        QTimer.singleShot(50, restart)

    def open_menu(self, position):
        self.menu.popup(position)

    def set_opaque(self, enabled):
        self.panel.opaque = enabled
        self.panel.update()

    def toggle_motion(self):
        self.motion_action.setChecked(not self.motion_action.isChecked())

    def recenter(self, *_):
        area = self.app.primaryScreen().availableGeometry()
        self.orb.move(area.right() - self.orb.width() - 32, area.bottom() - self.orb.height() - 24)
        self.position_panel()

    def panel_target(self):
        screen = self.app.screenAt(self.orb.geometry().center()) or self.app.primaryScreen()
        return place_panel(box(self.orb.geometry()), box(screen.availableGeometry()))

    def position_panel(self):
        self.motion.stop()
        target = self.panel_target()
        self.panel.resize(target.width, target.height)
        self.panel.move(target.x, target.y)

    def open_panel(self):
        if self.panel.isVisible():
            self.panel.raise_()
            return
        self.orb.show()
        self.position_panel()
        destination = self.panel.pos()
        offset = 28 if destination.x() < self.orb.x() else -28
        self.panel.setWindowOpacity(1 if self.orb.reduced_motion else 0)
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()
        self.panel.entry.setFocus()
        if hasattr(self, 'news'): self.news.opened()
        if not self.orb.reduced_motion:
            self.motion.setStartValue(destination + QPoint(offset, 14))
            self.motion.setEndValue(destination)
            self.fade.setStartValue(0.0)
            self.fade.setEndValue(1.0)
            self.motion.start()
            self.fade.start()

    def toggle_panel(self):
        self.close_panel() if self.panel.isVisible() else self.open_panel()

    def close_panel(self):
        from audio import voice
        voice._THINKING.clear()
        self.brain_cancel.set()
        if not self.brain_busy:
            self.brain.clear_temporary()
        self.generation += 1
        if not self.brain_busy:
            self.pool.clear()
        self.motion.stop()
        self.fade.stop()
        self.panel.hide()
        self.panel.show_answer("Right here with you.", "The previous result is closed. Type help or show files.")
        self.set_state(task="idle")

    def wake(self):
        if hasattr(self, 'news'): self.news.opened()
        self.orb.show()
        self.open_panel()
        self.panel.raise_()
        self.panel.activateWindow()

    def sleep(self):
        if hasattr(self, 'news'): self.news.suspend()
        if getattr(self, 'routine_dialog', None) is not None: self.routine_dialog.hide()
        if not self.tray.isVisible():
            self.close_panel()  # Keep a recoverable orb if Windows has no tray.
            return
        self.close_panel()
        self.orb.hide()

    def on_voice(self, text, quiet=False):
        """Handle wake word and speech utterances forwarded from the audio thread."""
        low = " ".join(text.casefold().split())
        if low == "wake up lya":
            self.wake()
            return
        if low in ("stop", "cancel", "close", "close panel"):
            self.close_panel()
            return
        if low in ("sleep", "go to sleep"):
            self.sleep()
            return
        if not self.orb.isVisible():
            self.orb.show()
        self.open_panel()
        self.set_state(task="listening")
        self.command(text)
    def start_voice(self, allow_cloud=False):
        """Start the voice listener. `allow_cloud` permits remote transcription."""
        if self.voice_thread and self.voice_thread.is_alive():
            return
        import threading
        self.voice_stop_event = threading.Event()
        self.panel.footnote.setText("VOICE LISTENER STARTING · CAMERA OFF")
        def _runner():
            try:
                from audio import voice
                voice.wake_loop(
                    on_wake=lambda text, quiet=False: self.voice_signals.wake_detected.emit(text, quiet),
                    clap_enabled=True,
                    stop_event=self.voice_stop_event,
                    offline_required=lambda: not allow_cloud or self.brain.private_mode,
                    cloud_provider=self.cloud_asr,
                    cloud_only=allow_cloud and self.cloud_asr == 'nvidia',
                    on_provider=lambda model, backup: self.voice_signals.status.emit(
                        'SPEECH: ' + model.upper() + (' · BACKUP' if backup else ' · PRIMARY')),
                    on_error=lambda kind: self.voice_signals.status.emit(
                        'VOICE INPUT ERROR (' + kind + ') · RETRYING'),
                    on_ready=lambda: self.voice_signals.status.emit(
                        "SAY LYA / LAYA / LEYA OR CLAP TWICE · COMMANDS REMOTE (" + self.cloud_asr.upper() + ")"
                        if allow_cloud and not self.brain.private_mode else
                        "SAY LYA / LAYA / LEYA OR CLAP TWICE · AUDIO STAYS ON DEVICE" +
                        (" · PRIVATE MODE: USE TEXT" if allow_cloud and self.cloud_asr == 'nvidia' else "")),
                    on_state=lambda phase: self.voice_signals.phase.emit(phase),
                    on_retry=lambda candidate, paused: self.voice_signals.retry.emit(candidate, paused)
                )
            except Exception as e:
                print(f"[voice] wake listener ended: {e}")
                self.voice_signals.status.emit(
                    "VOICE UNAVAILABLE · ONLINE HEARING FAILED · USE TEXT / RESTART VOICE"
                    if allow_cloud and self.cloud_asr == 'nvidia' else
                    "VOICE UNAVAILABLE · CHECK MICROPHONE / LOCAL MODEL · RESTART VOICE WAKE")
            else:
                self.voice_signals.status.emit("CAMERA & MICROPHONE OFF")
        self.voice_thread = threading.Thread(target=_runner, daemon=True, name="LYA-VoiceWake")
        self.voice_thread.start()

    def on_voice_status(self, text):
        self.panel.footnote.setText(text)
        self.orb.setToolTip(text)
        self.tray.setToolTip(text)
        if text.startswith('VOICE UNAVAILABLE'):
            self.orb.set_voice_phase('off')
            self.panel.show_answer('Voice listener stopped', text)
            self.open_panel()
        elif text == 'CAMERA & MICROPHONE OFF':
            self.orb.set_voice_phase('off')
        elif text.startswith('VOICE INPUT ERROR'):
            self.orb.set_voice_phase('off')

    def on_voice_phase(self, phase):
        self.orb.set_voice_phase('thinking' if phase == 'transcribing' else phase)

    def on_voice_retry(self, candidate='', paused=False):
        from brain.capabilities import volume_action
        action = volume_action(candidate)
        if self.cloud_voice and self.cloud_asr == 'nvidia' and self.brain.private_mode:
            message = "Private mode blocks online hearing. Please type your private question."
        elif paused:
            message = "Recognition is still uncertain. I'll wait for you to say Lya again. You can also use the text box."
        elif action:
            command = 'mute volume' if action == 'mute' else 'volume ' + action
            message = "I think you asked for a volume change. Please try saying " + command + "."
        else:
            message = "I'm not sure what I heard. Please try once more."
        self.orb.set_voice_phase('uncertain')
        body = message + "\n\nNo command was run."
        if candidate:
            body += "\nHeard (uncertain): " + candidate[:400]
        self.panel.show_answer('Waiting for Lya.' if paused else 'Words were uncertain.', body)
        self.open_panel()
        return message

    def stop_voice(self):
        """Signal voice wake listener to stop."""
        self._voice_restart += 1
        if self.voice_stop_event:
            self.voice_stop_event.set()
            if self.voice_thread and self.voice_thread.is_alive():
                self.panel.footnote.setText("VOICE LISTENER STOPPING · CAMERA OFF")

    def _voice_telemetry(self):
        """Return the audio.voice module holding the local listener, or None."""
        try:
            from audio import voice
            return voice
        except Exception as error:
            self.panel.footnote.setText("VOICE TELEMETRY UNAVAILABLE · " + type(error).__name__)
            return None

    def microphone_self_test(self):
        """Count what reaches the microphone; never opens a second microphone reader."""
        self.generation += 1
        self.set_state(task="listening")
        voice = self._voice_telemetry()
        if voice is None:
            self.panel.show_answer("Microphone self-test unavailable.",
                                  "The local voice module could not be loaded, so no microphone state is known.")
            self.open_panel()
            return
        health = voice.listener_health()
        if not health.get('listening'):
            self.panel.show_answer(
                "The voice listener is not running.",
                "This test measures the listener that is already open; it never starts a second microphone reader.\n\n"
                "The voice listener is not running. Turn Voice wake on from the crystal menu "
                "(or restart LYA) and run the test again.\n"
                "Listener state: " + str(health.get('state')) +
                " · device: " + str(health.get('device') or 'not opened yet'))
            self.open_panel()
            return
        voice.mic_test_start(MIC_TEST_SECONDS)
        self.panel.show_answer(
            "Listening for " + str(MIC_TEST_SECONDS) + " seconds…",
            "Speak normally now, then read the result here.\n\n"
            "LYA counts loudness only. Nothing is recorded, transcribed, stored or sent.\n"
            "Microphone: " + str(health.get('device') or 'default input'))
        self.open_panel()
        if self._mic_test_timer is None:
            self._mic_test_timer = QTimer(self)
            self._mic_test_timer.setSingleShot(True)
            self._mic_test_timer.timeout.connect(self.finish_microphone_self_test)
        self._mic_test_timer.start(int(MIC_TEST_SECONDS * 1000) + 400)

    def finish_microphone_self_test(self):
        """Show what the counted microphone window contained."""
        voice = self._voice_telemetry()
        report = voice.mic_test_report() if voice is not None else None
        if not report:
            return
        verdict = report.get('verdict')
        titles = {'hearing': "Sound reaches the microphone.",
                  'too-quiet': "Sound arrives, but very quietly.",
                  'silent': "The microphone is returning silence.",
                  'no-audio': "No audio blocks arrived.",
                  'no-listener': "The listener was not running."}
        self.set_state(task="success" if verdict == 'hearing' else
                       "error" if verdict in ('silent', 'no-audio', 'no-listener') else "approval")
        lines = [
            "This checks incoming sound only. Voice clarity and word recognition are separate checks.",
            "",
            "Microphone: " + str(report.get('device') or 'default input'),
            "Window: " + str(report.get('elapsed')) + "s of " + str(report.get('seconds')) + "s · " +
            str(report.get('blocks')) + " blocks · " +
            f"{(report.get('samples') or 0) / 16000:.1f}s of audio counted",
            "Peak: " + str(report.get('peak')) + " · mean RMS: " + str(report.get('rms_mean')) +
            " · loudest RMS: " + str(report.get('rms_max')),
            "Blocks crossing the " + str(report.get('threshold')) + " recorder gate: " +
            str(report.get('loud_blocks')) + " · clap pairs: " + str(report.get('claps')),
        ]
        if report.get('suppressed'):
            lines.append(str(report['suppressed']) +
                         " blocks arrived while LYA was speaking; those can never wake LYA.")
        lines.extend(["", str(report.get('detail') or '')])
        self.panel.show_answer(titles.get(verdict, "Microphone self-test"), "\n".join(lines))

    def _voice_health(self):
        """One truthful listener line for the status command."""
        voice = self._voice_telemetry()
        if voice is None:
            return "• Voice listener: telemetry unavailable (audio.voice did not load)"
        health = voice.listener_health()
        if not health.get('listening'):
            return ("• Voice listener: " + str(health.get('state')) +
                    " · no microphone open · say “can you hear me” after enabling Voice wake")
        gate = "crossing" if health.get('loud_blocks') else "below"
        return ("• Voice listener: " + str(health.get('state')) + " " + str(health.get('state_seconds')) +
                "s · " + str(health.get('device') or 'default input') +
                " · peak " + str(health.get('peak')) +
                " · loud blocks " + str(health.get('loud_blocks')) + " (" + gate + " the recorder gate)" +
                " · clap pairs " + str(health.get('claps')) +
                " · idle " + str(health.get('idle_seconds')) + "s")

    def quit(self):
        if hasattr(self, 'news'): self.news.shutdown()
        if getattr(self, 'routine_dialog', None) is not None: self.routine_dialog.close()
        if getattr(self, '_unregister_hotkey', None):
            try:
                self._unregister_hotkey()
            except Exception:
                pass
        self.brain_cancel.set()
        self.stop_voice()
        self.generation += 1
        self.pool.clear()
        self.orb.hide()
        self.panel.hide()
        self.tray.hide()
        self.app.quit()

    def set_state(self, person=None, task=None):
        self.orb.set_state(person, task)
        self.panel.color = self.orb.target_color
        self.panel.state_label.setText({'idle': 'CONVERSATION', 'files': 'DOCUMENTS',
                                       'success': 'REPLY', 'approval': 'YOUR APPROVAL',
                                       'error': 'NEEDS ATTENTION'}.get(self.orb.task, self.orb.task.upper()))
        self.panel.update()

    def show_files(self):
        self.generation += 1
        self.set_state(task="files")
        self.panel.show_documents()
        self.open_panel()

    def read_document(self, name):
        self.generation += 1
        self.set_state(task="thinking")
        self.panel.show_answer("Opening your document…", "Reading the selected project file locally.")
        self.pool.start(ReadDocument(self.generation, name, self.signals))

    def on_document(self, generation, name, text, ok):
        if generation != self.generation:
            return
        self.set_state(task="files" if ok else "error")
        self.panel.show_answer(name.replace("_", " ").removesuffix(".md"), text)

    def ask_brain(self, text):
        if self.brain_busy:
            self.panel.show_answer("A request is running.", "Close the panel to cancel it. The current network call, if any, may take up to its timeout to finish.")
            return
        import threading
        self.brain_cancel = threading.Event()
        self.brain_busy = True
        from audio import voice
        voice._THINKING.set()
        self.orb.set_voice_phase('thinking')
        self.panel.show_answer("Working on your request…", "Checking identity, permission and relevant context.")
        self.set_state(task="thinking")
        self.open_panel()
        self.pool.start(BrainJob(self.brain, text, self.brain_cancel, self.generation, self.brain_signals))

    def on_brain(self, generation, answer):
        self.brain_busy = False
        from audio import voice
        voice._THINKING.clear()
        if generation != self.generation or self.brain_cancel.is_set():
            return
        self.set_state(task="approval" if answer.route == "blocked" else "error" if answer.route == "error" else "idle")
        titles = {"demo": "Brain workflow · synthetic demo", "blocked": "One step is missing.", "council": "Council review", "recall": "Your active memories"}
        self.panel.show_answer(titles.get(answer.route, "LYA"), answer.text)
        route = getattr(self.brain.client, 'last_route', None)
        if answer.route == 'private-local':
            self.panel.footnote.setText('LOCAL ONLY · CLOUD BLOCKED')
        elif (isinstance(route, dict) and isinstance(route.get('route'), str)
                and type(route.get('attempts')) is int):
            self.panel.footnote.setText('CLOUD · ' + route['route'] + (' · BACKUP USED' if route['attempts'] > 1 else ''))

    def command(self, text):
        if hasattr(self, 'news'): self.news.interrupt()
        low = " ".join(text.casefold().split())
        if self.brain_busy and low not in ("stop", "cancel", "close", "close panel", "sleep", "quit", "exit"):
            self.panel.show_answer("A request is running.",
                                   "Wait for its answer or say stop to cancel it.")
            return
        self.generation += 1
        if low in ("stop", "cancel", "close", "close panel"):
            self.close_panel()
        elif low == "sleep":
            self.sleep()
        elif low in ("quit", "exit"):
            self.quit()
        elif low.strip(' .!?') in ('technology updates', 'tech updates', 'ai news', 'show technology updates',
                     'any news about technology updates', 'tell me any technology updates',
                     'tell me whether any news about technology updates', 'latest ai news'):
            self.show_technology_updates()
        elif low.strip(' .!?') in ('routine drafts', 'show routine drafts', 'plan a routine', 'new routine'):
            self.show_routine_drafts()
        elif low in ("show files", "show saved files", "files", "show project files"):
            self.show_files()
        elif low in ("reduce motion", "motion off", "motion on"):
            self.motion_action.setChecked(low != "motion on")
            self.panel.show_answer("Motion adjusted.", "Gentle motion is " + ("off." if self.orb.reduced_motion else "on."))
        elif low.startswith("person ") and low[7:] in PERSON_COLORS:
            self.set_state(person=low[7:], task="idle")
            self.panel.show_answer("A different light.", f"Previewing the {low[7:]} color. This changes appearance only; it does not identify anyone or grant access.")
        elif low.startswith("task ") and low[5:] in TASK_COLORS:
            self.set_state(task=low[5:])
            self.panel.show_answer("Task color preview.", f"Previewing {low[5:]}. This is a presentation state, not an action running in the background.")
        elif low == "colors":
            self.panel.show_answer("A color for each moment.", "Person palettes\nGuest · ice     Admin · amber\nFamily · violet     Friend · jade\n\nTask colors take priority\nListening · cyan   Thinking · violet\nFiles · blue   Success · green\nApproval · amber   Error · rose\n\nTry: person admin   or   task thinking\nUse task idle to return to the person color.")
        elif low in ("time", "what time is it", "date", "what date is it", "day"):
            self.panel.show_answer(time.strftime("%I:%M %p"), time.strftime("%A, %d %B %Y"))
        elif low in MIC_COMMANDS:
            self.microphone_self_test()
        elif low in ("status", "system status", "check"):
            ready_deps = []
            missing_deps = []
            for name, pkg in [("DPAPI (pywin32)", "win32crypt"), ("Cryptography", "cryptography"),
                              ("NumPy", "numpy"), ("OpenCV", "cv2"), ("Speech (sounddevice)", "sounddevice"),
                              ("Vosk Wake", "vosk")]:
                try:
                    __import__(pkg)
                    ready_deps.append(name)
                except ImportError:
                    missing_deps.append(name)
            status_text = (
                f"LYA Desktop Status\n"
                f"• Presentation: PySide6 Native Crystal (Active)\n"
                f"• Python: {sys.version.split()[0]} on {sys.platform}\n"
                f"• Foundations: {', '.join(ready_deps)}\n"
                f"• Vision/Voice (Next): {', '.join(missing_deps)}\n"
                f"• Policy Gate: Deny-by-default, Local Scoped\n"
                + self._voice_health()
            )
            self.panel.show_answer("System Readiness", status_text)
        elif low in ("help", "commands", "what can you do"):
            self.panel.show_answer("LYA Commands",
                "Available commands:\n" + self.brain.capability_help() +
                "\n\nDesktop controls:\n"
                "• technology updates — official-source catch-up and background check controls\n"
                "• routine drafts — review schedule, scope, limits and missing connections\n"
                "• status — check local dependency readiness\n"
                "• can you hear me — count what reaches the microphone (diagnostic, nothing recorded)\n"
                "• show files — preview the listed project documents\n"
                "• open chat / close chat / full screen\n"
                "• open camera / close camera (local preview)\n"
                "• open recovery / register admin (guided setup)\n"
                "• colors / person admin / task thinking (appearance only)\n"
                "• reduce motion / motion on / quit\n"
                "• brain demo (synthetic, no personal data)")
        else:
            self.ask_brain(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reduced-motion", action="store_true")
    parser.add_argument("--show-panel", action="store_true")
    parser.add_argument("--voice", action="store_true", help="Deprecated: the voice listener is on by default")
    parser.add_argument("--no-voice", action="store_true", help="Start without the microphone listener")
    parser.add_argument("--microphone", help="Exact input-device name; overrides Windows default for this session")
    parser.add_argument("--cloud-voice", action="store_true", help="Explicitly permit remote command transcription")
    parser.add_argument("--cloud-asr", choices=('groq', 'nvidia'), default='groq',
                        help="Remote recognizer; requires --cloud-voice")
    parser.add_argument("--command-asr", choices=('whisper', 'vosk'),
                        help="Local command recognizer; Whisper is an experimental opt-in")
    parser.add_argument("--system-dictation", action="store_true",
                        help="Prepare Windows Voice Access input with LYA's microphone off")
    parser.add_argument("--skip-setup", action="store_true", help="Do not open first-run owner setup")
    parser.add_argument("--original-art", action="store_true", help="Use the approved reference artwork (default)")
    parser.add_argument("--model-art", action="store_true", help="Try the experimental baked 3D artwork")
    args = parser.parse_args()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("LYA Desktop")
    instance_lock = QLockFile(str(Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.TempLocation)) / 'lya-desktop.lock'))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(0):
        # Attempt to wake the already running instance.
        try:
            from PySide6.QtNetwork import QLocalSocket
            sock = QLocalSocket()
            sock.connectToServer("lya-desktop-wake")
            if sock.waitForConnected(400):
                sock.write(b"wake\n")
                sock.waitForBytesWritten(400)
                sock.disconnectFromServer()
                return 0
        except Exception:
            pass
        try:
            if not instance_lock.isLocked():
                instance_lock.removeStaleLockFile()
                if not instance_lock.tryLock(0):
                    return 0
            else:
                return 0
        except Exception:
            return 0
    app.setQuitOnLastWindowClosed(False)
    from experience import OrbDesktop
    desktop = OrbDesktop(app, args.reduced_motion)
    desktop.orb.set_artwork(args.model_art and not args.original_art)
    wake_server = None
    try:
        from PySide6.QtNetwork import QLocalServer
        wake_server = QLocalServer(app)
        wake_server.removeServer("lya-desktop-wake")
        if wake_server.listen("lya-desktop-wake"):
            def on_wake():
                conn = wake_server.nextPendingConnection()
                if conn:
                    conn.readyRead.connect(lambda: None)
                desktop.wake()
            wake_server.newConnection.connect(on_wake)
    except Exception:
        pass
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            from PySide6.QtCore import QAbstractNativeEventFilter

            class WindowsHotkeyFilter(QAbstractNativeEventFilter):
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback
                def nativeEventFilter(self, eventType, message):
                    if eventType == b'windows_generic_MSG':
                        msg = wintypes.MSG.from_address(int(message))
                        if msg.message == 0x0312:
                            self.callback()
                    return False, 0

            hotkey_filter = WindowsHotkeyFilter(desktop.toggle_panel)
            app.installNativeEventFilter(hotkey_filter)
            hwnd = int(desktop.orb.winId())
            if ctypes.windll.user32.RegisterHotKey(hwnd, 101, 0x4006, 0x4C):
                desktop._unregister_hotkey = lambda: ctypes.windll.user32.UnregisterHotKey(hwnd, 101)
        except Exception:
            pass
    if args.microphone:
        os.environ['LYA_MICROPHONE'] = args.microphone
    if args.command_asr:
        os.environ['LYA_COMMAND_ASR'] = args.command_asr
    desktop.cloud_voice = args.cloud_voice
    desktop.cloud_asr = args.cloud_asr
    if not args.no_voice and not args.system_dictation:
        desktop.start_voice(allow_cloud=args.cloud_voice)
    if not args.skip_setup and desktop.needs_owner_setup():
        desktop.begin_owner_setup()   # First run: set up the owner before opening LYA.
    else:
        desktop.start_intro()
        if args.show_panel:
            desktop.open_panel()
    if args.system_dictation:
        desktop.prepare_system_dictation()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

