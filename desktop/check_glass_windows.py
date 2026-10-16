"""Native Windows border smoke check using only a synthetic Qt window."""
import ctypes
import os
import sys
from ctypes import wintypes as w

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtTest import QTest
from task_border import TaskBorder, WindowsTarget


def main():
    if sys.platform != 'win32':
        raise SystemExit('This check needs Windows.')
    application = QApplication.instance() or QApplication([])
    window = QWidget()
    window.setGeometry(80, 80, 600, 400)
    window.show()
    window.raise_()
    window.activateWindow()
    QTest.qWait(150)
    target = WindowsTarget(int(window.winId()), os.getpid())
    target.u.SetForegroundWindow.argtypes = [w.HWND]
    target.u.SetForegroundWindow.restype = w.BOOL
    target.u.SetForegroundWindow(int(window.winId()))
    for _ in range(10):
        if target.u.GetForegroundWindow() == int(window.winId()):
            break
        QTest.qWait(50)
    border = TaskBorder(reduced=True)
    try:
        rect = target.geometry()
        print('Synthetic native target:', dict(visible=bool(target.u.IsWindowVisible(target.hwnd)),
              foreground=target.u.GetForegroundWindow() == target.hwnd,
              screens=[s.name() for s in application.screens()], bounds=str(rect)))
        assert rect is not None and not rect.isEmpty(), 'Could not establish synthetic foreground target'
        border.begin(1, target, 'Synthetic task')
        application.processEvents()
        assert all(edge.isVisible() for edge in border.edges)
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.GetForegroundWindow.restype = w.HWND
        get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
        get_style.argtypes = [w.HWND, ctypes.c_int]
        get_style.restype = ctypes.c_ssize_t
        for surface in [*border.edges, border.label]:
            style = get_style(int(surface.winId()), -20)
            assert style & 0x20, 'Input transparent native style missing'
            assert style & 0x8000000, 'No-activate native style missing'
        assert user32.GetForegroundWindow() == window.winId(), 'Border stole focus'
        moved = window.geometry().translated(30, 20)
        window.setGeometry(moved)
        QTest.qWait(80)
        border.refresh()
        assert border.last_rect == target.geometry()
        invalid = WindowsTarget(int(window.winId()), os.getpid()+1)
        assert invalid.geometry() is None, 'Mismatched PID was accepted'
        window.showMinimized()
        QTest.qWait(80)
        border.refresh()
        assert all(not edge.isVisible() for edge in border.edges)
        border.stop()
        assert not border.motion.isActive() and not border.tracking.isActive()
        print('Windows target bounds, PID pin, movement, minimize, click-through styles, focus and idle stop: PASS')
    finally:
        border.close()
        window.close()


if __name__ == '__main__':
    main()
