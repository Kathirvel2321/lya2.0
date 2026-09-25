"""Render synthetic native recovery screens; no real profile, keys or screenshot capture."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from test_recovery_ui import RecoveryInterfaceChecks, APP
from PySide6.QtGui import QFontDatabase
from security.policy import Session

QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
out = Path(__file__).resolve().parent
case = RecoveryInterfaceChecks()
case.setUp()
try:
    case.dialog.load_notes()
    case.settle()
    APP.processEvents()
    assert case.dialog.grab().save(str(out / "backup-synthetic.png"))
    case.dialog.tabs.setCurrentIndex(1)
    APP.processEvents()
    assert case.dialog.grab().save(str(out / "restore-synthetic.png"))
    case.current = Session()
    case.dialog.update_controls()
    case.dialog.tabs.setCurrentIndex(0)
    APP.processEvents()
    assert case.dialog.grab().save(str(out / "locked-screen.png"))
finally:
    case.tearDown()
    case.doCleanups()
