"""Synthetic UI frames only. Never launch a verifier or collect sensor data."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from desktop.registration import RegistrationDialog

app = QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
dialog = RegistrationDialog(reduced_motion=True)
dialog.show()
app.processEvents()
folder = Path(__file__).resolve().parent
for name, progress in (("01-center", 0), ("02-split", 0.4), ("03-screen", 1)):
    dialog.set_progress(progress)
    app.processEvents()
    assert dialog.grab().save(str(folder / (name + ".png")))
dialog.name.setText("Demo owner")
for name in ("04-device", "05-privacy", "06-review"):
    dialog.change_step(1)
    app.processEvents()
    assert dialog.grab().save(str(folder / (name + ".png")))
dialog.reject()
