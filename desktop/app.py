"""LYA's native crystal and glass panel. Run launch-lya.ps1 from the project root.

This milestone implements presentation and read-only project-document previews.
Person/task previews are cosmetic. Default launch has a guest brain and no sensors.
"""
import argparse
import math
import sys
import time
from pathlib import Path

from PySide6.QtCore import (Qt, QPoint, QRect, QRectF, QSize, QTimer, Signal, Property,
                            QEasingCurve, QPropertyAnimation, QObject, QRunnable, QThreadPool)
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QImage, QImageReader, QKeySequence, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient,
                           QShortcut, QRegion)
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
        self.original = crystal_pixmap(HERE / "assets" / "crystal-original.png")
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
        if now >= self.motion_until:
            self.timer.stop()
            self.phase = 0.0
        self.update()

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
        if self.width() <= 88:
            p.setOpacity(0)  # Keep the docked crystal clear of unreadably small labels.
        p.setBrush(QColor(12, 20, 30, 235))
        p.setPen(QPen(QColor(180, 205, 220, 95), 1))
        p.drawRoundedRect(QRectF(13, 211, 158, 31), 15, 15)
        p.setPen(self.color)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        label = "LYA  ·  " + ("UI PREVIEW" if self.task == "idle" else self.task.upper())
        p.drawText(QRectF(15, 211, 154, 31), Qt.AlignmentFlag.AlignCenter, label)
        if morph:
            p.resetTransform()
            p.setOpacity(morph)
            side = min(self.width(), self.height())
            p.translate(self.width() / 2, self.height() / 2)
            halo = QRadialGradient(0, 0, side / 2)
            tint = QColor(self.color)
            tint.setAlpha(90)
            halo.setColorAt(0.35, tint)
            tint.setAlpha(0)
            halo.setColorAt(1, tint)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QRectF(-side/2, -side/2, side, side))
            p.setBrush(QColor(15, 28, 40, 245))
            p.setPen(QPen(self.color, 1.5))
            radius = side * 0.27
            p.drawEllipse(QRectF(-radius, -radius, radius*2, radius*2))
            p.setBrush(self.color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-3, -3, 6, 6))
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
            QWidget { color: #f1f5fa; font-family: 'Segoe UI'; font-size: 13px; }
            QLabel { background: transparent; }
            QPushButton { background: rgba(190,220,245,15); border: 1px solid rgba(210,232,250,35);
                border-radius: 10px; padding: 9px 13px; color: #dce9f3; }
            QPushButton:hover { background: rgba(140,210,240,35); border-color: #9bcddf; }
            QPushButton:focus, QLineEdit:focus, QListWidget:focus { border: 2px solid #9de4ee; }
            QLineEdit { background: rgba(5,12,22,150); border: 1px solid rgba(200,225,245,55);
                border-radius: 12px; padding: 12px; selection-background-color: #296a83; }
            QTextBrowser { background: transparent; border: none; color: #edf4f8;
                font-size: 15px; selection-background-color: #296a83; }
            QListWidget { background: transparent; border: none; outline: 0; }
            QListWidget::item { background: rgba(175,205,230,12); border: 1px solid rgba(200,225,245,24);
                border-radius: 12px; padding: 0; margin-bottom: 8px; }
            QListWidget::item:selected { background: #224153; border: 1px solid #90d7e5; }
            QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: #617382; border-radius: 3px; min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 26, 32, 27)
        outer.setSpacing(15)
        header = QHBoxLayout()
        brand = QLabel("L Y A")
        brand.setStyleSheet("font-size: 16px; font-weight: 600; letter-spacing: 4px;")
        header.addWidget(brand)
        header.addStretch()
        self.state_label = QLabel("INTERFACE PREVIEW")
        self.state_label.setStyleSheet("font-size: 10px; color: #aec6d5;")
        header.addWidget(self.state_label)
        close = QPushButton("×")
        close.setFixedSize(32, 32)
        close.setAccessibleName("Close result panel")
        close.setToolTip("Close panel · Escape")
        close.clicked.connect(self.dismissed)
        header.addWidget(close)
        outer.addLayout(header)
        self.eyebrow = QLabel("A LITTLE SPACE TO THINK")
        self.eyebrow.setStyleSheet("color: #91c9d6; font-size: 10px; letter-spacing: 2px;")
        outer.addWidget(self.eyebrow)
        self.title_label = QLabel("Right here with you.")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 25px; font-weight: 600; color: #f4f8fc;")
        outer.addWidget(self.title_label)
        self.stack = QStackedWidget()
        self.answer = QTextBrowser()
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
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Ask LYA · try “show files”")
        self.entry.setAccessibleName("Type a command to LYA")
        self.entry.setMaxLength(2000)
        self.entry.returnPressed.connect(self.send)
        composer.addWidget(self.entry, 1)
        send = QPushButton("↑")
        send.setAccessibleName("Send command")
        send.setFixedSize(42, 42)
        send.clicked.connect(self.send)
        composer.addWidget(send)
        outer.addLayout(composer)
        self.footnote = QLabel("LOCAL INTERFACE  ·  CAMERA & MICROPHONE OFF")
        self.footnote.setStyleSheet("font-size: 9px; color: #a6b7c5; letter-spacing: 1px;")
        outer.addWidget(self.footnote)
        self.show_answer("Right here with you.", "Your desktop stays yours.\n\nClick Project files to read the saved project plans, or type help.\n\nDrag the crystal to place me. Right-click it to preview person and task colors.")

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
        self.eyebrow.setText("A LITTLE SPACE TO THINK")

    def show_documents(self):
        self.title_label.setText("Your project, close by.")
        self.eyebrow.setText("PROJECT DOCUMENTS  /  READ ONLY")
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
        p.setPen(Qt.PenStyle.NoPen)
        # Cheap fixed shadow, no live backdrop capture or expensive blur.
        for spread in (8, 6, 4, 2):
            p.setBrush(QColor(0, 0, 0, 12))
            p.drawRoundedRect(body.adjusted(-spread, -spread + 3, spread, spread + 3), 26, 26)
        glass = QLinearGradient(body.topLeft(), body.bottomRight())
        glass.setColorAt(0, QColor(28, 41, 55, 255 if self.opaque else 220))
        glass.setColorAt(1, QColor(10, 19, 31, 255 if self.opaque else 232))
        p.setBrush(glass)
        p.setPen(QPen(QColor(212, 231, 245, 105), 1))
        p.drawRoundedRect(body, 22, 22)
        p.setPen(QPen(QColor(255, 255, 255, 33), 1))
        p.drawRoundedRect(body.adjusted(2, 2, -2, -2), 20, 20)
        c = QColor(self.color)
        c.setAlpha(160)
        p.setPen(QPen(c, 2))
        p.drawLine(35, 11, min(160, self.width() - 35), 11)
        p.end()


class ReadSignals(QObject):
    finished = Signal(int, str, str, bool)


class VoiceSignals(QObject):
    wake_detected = Signal(str, bool)
    status = Signal(str)


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
        self.voice_signals.status.connect(self.panel.footnote.setText)
        self.voice_thread = None
        self.voice_stop_event = None
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

    def make_menu(self):
        menu = QMenu()
        menu.addAction("Open LYA", self.wake)
        menu.addAction("Project files", self.show_files)
        menu.addAction("Sign in / register admin", lambda: self.command("register admin"))
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
        self.voice_action.toggled.connect(lambda checked: self.start_voice() if checked else self.stop_voice())
        menu.addAction(self.voice_action)
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
        self.orb.show()
        self.open_panel()

    def sleep(self):
        if not self.tray.isVisible():
            self.close_panel()  # Keep a recoverable orb if Windows has no tray.
            return
        self.close_panel()
        self.orb.hide()

    def on_voice(self, text, quiet=False):
        """Handle wake word and speech utterances forwarded from the audio thread."""
        low = " ".join(text.casefold().split())
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
    def start_voice(self):
        """Start offline voice wake listener in background daemon thread."""
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
                    stop_event=self.voice_stop_event,
                    offline_required=True,
                    on_ready=lambda: self.voice_signals.status.emit("LOCAL VOICE LISTENER RUNNING · CAMERA OFF")
                )
            except Exception as e:
                print(f"[voice] wake listener ended: {e}")
                self.voice_signals.status.emit("VOICE UNAVAILABLE · CHECK LOCAL MODEL / DEVICE")
            else:
                self.voice_signals.status.emit("CAMERA & MICROPHONE OFF")
        self.voice_thread = threading.Thread(target=_runner, daemon=True, name="LYA-VoiceWake")
        self.voice_thread.start()

    def stop_voice(self):
        """Signal voice wake listener to stop."""
        if self.voice_stop_event:
            self.voice_stop_event.set()
            if self.voice_thread and self.voice_thread.is_alive():
                self.panel.footnote.setText("VOICE LISTENER STOPPING · CAMERA OFF")

    def quit(self):
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
        self.panel.state_label.setText(f"{self.orb.person.upper()} PALETTE · {self.orb.task.upper()}")
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
        self.panel.show_answer("Working on your request…", "Checking identity, permission and relevant context.")
        self.set_state(task="thinking")
        self.open_panel()
        self.pool.start(BrainJob(self.brain, text, self.brain_cancel, self.generation, self.brain_signals))

    def on_brain(self, generation, answer):
        self.brain_busy = False
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
                f"• Policy Gate: Deny-by-default, Local Scoped"
            )
            self.panel.show_answer("System Readiness", status_text)
        elif low in ("help", "commands", "what can you do"):
            self.panel.show_answer("LYA Commands",
                "Available commands:\n" + self.brain.capability_help() +
                "\n\nDesktop controls:\n"
                "• status — check local dependency readiness\n"
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
    parser.add_argument("--voice", action="store_true", help="Start background offline voice wake listener")
    parser.add_argument("--original-art", action="store_true", help="Use the earlier crystal artwork")
    parser.add_argument("--model-art", action="store_true", help="Try the experimental baked 3D artwork")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("LYA Desktop")
    app.setQuitOnLastWindowClosed(False)
    from experience import OrbDesktop
    desktop = OrbDesktop(app, args.reduced_motion)
    desktop.orb.set_artwork(not args.original_art)
    desktop.start_intro()
    if args.voice:
        desktop.start_voice()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
