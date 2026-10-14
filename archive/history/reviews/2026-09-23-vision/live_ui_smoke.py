import time
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication
from desktop.camera_eyes import VisionDialog
app = QApplication([])
dialog = VisionDialog()
dialog.show()
dialog.toggle_live()
start = time.monotonic()
while time.monotonic() - start < 12 and dialog.last_result is None:
    app.processEvents()
    time.sleep(.05)
assert dialog.last_result is not None, 'No live frame reached the window'
assert dialog.last_result['identity'] == 'unknown'
dialog.stop_camera()
assert dialog.process.state() == QProcess.ProcessState.NotRunning
assert dialog.last_result is None
print('live Qt handoff and stop passed; first_frame_seconds', round(time.monotonic() - start, 2))
dialog.close()
