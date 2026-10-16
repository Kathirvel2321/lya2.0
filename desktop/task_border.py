"""Task-scoped, input-transparent borders. Never infer a task from window focus.

Four narrow native strips avoid repainting an app-sized transparent surface.
Windows discovery is bounded to a launch receipt's PID; no screenshots or titles.
"""
import ctypes
import sys
import time
import weakref

from PySide6.QtCore import QObject, QTimer, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from glass_style import ACTIVITY, MOVING

FLAGS = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput |
         Qt.WindowType.WindowDoesNotAcceptFocus)


def logical_rect(bounds, monitor, screen):
    """DWM physical pixels -> Qt logical pixels, preserving monitor origin."""
    x, y, right, bottom = bounds
    mx, my = monitor
    dpr = screen.devicePixelRatio()
    origin = screen.geometry().topLeft()
    return QRect(origin.x() + round((x - mx) / dpr), origin.y() + round((y - my) / dpr),
                 round((right - x) / dpr), round((bottom - y) / dpr))


def monitor_screen(screens, device, bounds):
    """Qt may expose a monitor's friendly name instead of its Win32 device name."""
    named = [s for s in screens if s.name().casefold() == device.casefold()]
    if len(named) == 1:
        return named[0]
    left, top, right, bottom = bounds
    # Windows Qt keeps native monitor origins and scales the screen's size.
    matches = [s for s in screens if abs(s.geometry().left() - left) <= 1
               and abs(s.geometry().top() - top) <= 1
               and abs(s.geometry().width()*s.devicePixelRatio() - (right-left)) <= 2
               and abs(s.geometry().height()*s.devicePixelRatio() - (bottom-top)) <= 2]
    return matches[0] if len(matches) == 1 else None


class QtTarget:
    """An explicitly supplied app-owned window, used by document UI and tests."""
    def __init__(self, widget):
        self.widget = weakref.ref(widget)

    def geometry(self):
        try:
            w = self.widget()
            if w is None:
                return None
            if not w.isVisible() or w.isMinimized():
                return QRect()
            return w.frameGeometry() if w.isWindow() else QRect(w.mapToGlobal(w.rect().topLeft()), w.size())
        except RuntimeError:
            return None


class WindowsTarget:
    """Pinned HWND/PID. Revalidate ownership, visibility and foreground on each read."""
    def __init__(self, hwnd, pid):
        if sys.platform != 'win32':
            raise OSError('Native app borders require Windows')
        from ctypes import wintypes as w
        self.hwnd, self.pid = int(hwnd), int(pid)
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.d = ctypes.WinDLL('dwmapi', use_last_error=True)
        self.u.GetForegroundWindow.restype = w.HWND
        self.u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.u.GetWindowThreadProcessId.restype = w.DWORD
        for name in ('IsWindow', 'IsWindowVisible', 'IsIconic'):
            getattr(self.u, name).argtypes = [w.HWND]
            getattr(self.u, name).restype = w.BOOL
        self.u.MonitorFromWindow.argtypes = [w.HWND, w.DWORD]
        self.u.MonitorFromWindow.restype = w.HMONITOR
        self.u.GetMonitorInfoW.argtypes = [w.HMONITOR, ctypes.c_void_p]
        self.u.GetMonitorInfoW.restype = w.BOOL
        self.d.DwmGetWindowAttribute.argtypes = [w.HWND, w.DWORD, ctypes.c_void_p, w.DWORD]
        self.d.DwmGetWindowAttribute.restype = ctypes.c_long

    def geometry(self):
        from ctypes import wintypes as w
        pid = w.DWORD()
        if not self.u.IsWindow(self.hwnd):
            return None
        self.u.GetWindowThreadProcessId(self.hwnd, ctypes.byref(pid))
        if pid.value != self.pid:
            return None
        if (not self.u.IsWindowVisible(self.hwnd) or self.u.IsIconic(self.hwnd)
                or self.u.GetForegroundWindow() != self.hwnd):
            return QRect()  # Never draw over an unrelated foreground window.
        cloaked = w.DWORD()
        if self.d.DwmGetWindowAttribute(self.hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0 and cloaked.value:
            return QRect()
        rect = w.RECT()
        if self.d.DwmGetWindowAttribute(self.hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
            return QRect()  # No guessed bounds when native information is unavailable.
        class Info(ctypes.Structure):
            _fields_ = [('cbSize', w.DWORD), ('rcMonitor', w.RECT), ('rcWork', w.RECT),
                        ('dwFlags', w.DWORD), ('szDevice', w.WCHAR * 32)]
        info = Info()
        info.cbSize = ctypes.sizeof(info)
        monitor = self.u.MonitorFromWindow(self.hwnd, 2)
        if not self.u.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return QRect()
        screen = monitor_screen(QApplication.screens(), info.szDevice,
                                (info.rcMonitor.left, info.rcMonitor.top, info.rcMonitor.right, info.rcMonitor.bottom))
        if screen is None:
            return QRect()
        return logical_rect((rect.left, rect.top, rect.right, rect.bottom),
                            (info.rcMonitor.left, info.rcMonitor.top), screen)

    @classmethod
    def for_process(cls, pid):
        if sys.platform != 'win32' or type(pid) is not int or pid <= 0:
            return None
        from ctypes import wintypes as w
        u = ctypes.WinDLL('user32', use_last_error=True)
        u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        u.GetWindowThreadProcessId.restype = w.DWORD
        u.IsWindowVisible.argtypes = [w.HWND]
        u.IsWindowVisible.restype = w.BOOL
        callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        u.EnumWindows.argtypes = [callback_type, w.LPARAM]
        u.EnumWindows.restype = w.BOOL
        found = []
        def visit(hwnd, _):
            owner = w.DWORD()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and u.IsWindowVisible(hwnd):
                found.append(int(hwnd))
                return False
            return True
        callback = callback_type(visit)
        u.EnumWindows(callback, 0)
        return cls(found[0], pid) if found else None


class Edge(QWidget):
    def __init__(self, side):
        super().__init__(None, FLAGS)
        self.side, self.color, self.phase = side, QColor('#78dce9'), None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(self.color, 1.2))
        if self.side in ('top', 'bottom'):
            w = self.width()
            y, end = (2, 12) if self.side == 'top' else (9, 0)
            path = QPainterPath()
            path.moveTo(2, end)
            path.quadTo(2, y, 12, y)
            path.lineTo(w - 12, y)
            path.quadTo(w - 3, y, w - 3, end)
            p.drawPath(path)
        else:
            p.drawLine(2, 0, 2, self.height())
        if self.side == 'top' and self.phase is not None:
            x = 12 + self.phase * max(0, self.width() - 24)
            p.setPen(QPen(QColor('#e3fbff'), 1.8))
            p.drawLine(round(x - 5), 2, round(x + 5), 2)
        p.end()


class StatusTag(QLabel):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setPen(QPen(QColor('#497183'), 1))
        p.setBrush(QColor(12, 31, 49, 248))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 10, 10)
        p.setPen(QColor('#dceef5'))
        p.setFont(self.font())
        p.drawText(self.rect().adjusted(12, 7, -12, -7), Qt.AlignmentFlag.AlignVCenter, self.text())
        p.end()


class TaskBorder(QObject):
    """One task generation at a time. Hidden/minimized targets suspend motion."""
    def __init__(self, parent=None, reduced=False, clock=time.monotonic):
        super().__init__(parent)
        self.clock, self.reduced = clock, reduced
        self.edges = [Edge(side) for side in ('top', 'bottom', 'left', 'right')]
        self.label = StatusTag(None, FLAGS)
        self.label.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.label.setStyleSheet('QLabel { color: #dceef5; background: #102339; border: 1px solid #497183; border-radius: 10px; padding: 7px 12px; font: 12px "Segoe UI"; }')
        self.tracking = QTimer(self)
        self.tracking.setInterval(250)
        self.tracking.timeout.connect(self.refresh)
        self.motion = QTimer(self)
        self.motion.setInterval(80)
        self.motion.timeout.connect(self.advance)
        self.search = QTimer(self)
        self.search.setInterval(150)
        self.search.timeout.connect(self.find_launch)
        self.generation = None
        self.target = None
        self.deadline = None
        self.launch_pid = None
        self.state = 'idle'
        self.last_rect = QRect()
        self.phase = 0

    def begin(self, generation, target, label='Working in this app', state='working', duration=None):
        self.stop()
        if state not in ACTIVITY or target is None:
            return
        self.generation, self.target, self.state = generation, target, state
        self.label.setText(label[:100])
        self.label.adjustSize()
        self.deadline = self.clock() + duration if duration else None
        self.tracking.start()
        self.refresh()

    def opened(self, generation, pid):
        self.stop()
        if sys.platform != 'win32' or type(pid) is not int or pid <= 0:
            return
        self.generation, self.launch_pid = generation, pid
        self.deadline = self.clock() + 1.5
        self.search.start()
        self.find_launch()

    def find_launch(self):
        if self.clock() >= self.deadline:
            self.stop()
            return
        target = WindowsTarget.for_process(self.launch_pid)
        if target is not None:
            self.begin(self.generation, target, 'App opened', 'done', .6)

    def set_reduced(self, reduced):
        self.reduced = bool(reduced)
        self.refresh()

    def refresh(self):
        if self.target is None:
            return
        if self.deadline is not None and self.clock() >= self.deadline:
            self.stop()
            return
        rect = self.target.geometry()
        if rect is None:
            self.stop()
            return
        if rect.isEmpty():
            self.hide_surfaces()
            return
        color = QColor(ACTIVITY[self.state][0])
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        boxes = (QRect(x, y, w, 12), QRect(x, y + h - 12, w, 12),
                 QRect(x, y + 12, 5, max(1, h - 24)), QRect(x + w - 5, y + 12, 5, max(1, h - 24)))
        for edge, box in zip(self.edges, boxes):
            if edge.geometry() != box:
                edge.setGeometry(box)
            if edge.color != color:
                edge.color = color
                edge.update()
            edge.show()
        label_x = x + 12
        label_y = y + h - self.label.height() - 12
        self.label.move(label_x, max(y + 8, label_y))
        self.label.show()
        self.last_rect = rect
        if self.state in MOVING and not self.reduced:
            if not self.motion.isActive():
                self.motion.start()
        else:
            self.motion.stop()
            self.edges[0].phase = None
            self.edges[0].update()

    def advance(self):
        self.phase = (self.phase + .018) % 1
        top = self.edges[0]
        top.phase = self.phase
        top.update()  # Only a 12-pixel strip, never the app's content rectangle.

    def hide_surfaces(self):
        self.motion.stop()
        for edge in self.edges:
            edge.hide()
        self.label.hide()

    def stop(self):
        self.tracking.stop()
        self.motion.stop()
        self.search.stop()
        self.hide_surfaces()
        self.target = self.generation = self.deadline = self.launch_pid = None
        self.last_rect = QRect()

    def close(self):
        self.stop()
        for surface in [*self.edges, self.label]:
            surface.close()
            surface.deleteLater()
