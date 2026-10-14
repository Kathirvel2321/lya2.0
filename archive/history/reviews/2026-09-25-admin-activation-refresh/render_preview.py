"""Render a synthetic owner-setup preview without sensors or a real store."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from desktop.activation import ActivationDialog, Layer
from test_activation import FakeCamera, FakeMic


def main():
    app = QApplication.instance() or QApplication([])
    for font in ("segoeui.ttf", "segoeuib.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
    layers = [Layer(key, key.upper(), True, "synthetic") for key in
              ("core", "vault", "store", "optics", "camera", "mic", "tts", "hello")]
    with patch("desktop.activation.probe_layers", return_value=layers), \
         patch("desktop.activation._setup_speech", return_value=None):
        dialog = ActivationDialog(reduced_motion=True, camera=FakeCamera(), mic=FakeMic())
        dialog.show()
        app.processEvents()
        dialog.go(1)
        dialog.name.setText("Sample Owner")
        app.processEvents()
        target = Path(__file__).with_name("identity-synthetic.png")
        if not dialog.grab().save(str(target)):
            raise RuntimeError("Preview was not saved")
        dialog.go(1)
        dialog._toggle_camera()
        dialog._pump()
        app.processEvents()
        if not dialog.grab().save(str(target.with_name("optics-synthetic.png"))):
            raise RuntimeError("Optics preview was not saved")
        dialog.reject()


if __name__ == "__main__":
    main()
