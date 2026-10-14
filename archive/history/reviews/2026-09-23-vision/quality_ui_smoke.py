import time
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication
from desktop.camera_eyes import VisionDialog
app = QApplication([])
dialog = VisionDialog()
dialog.show()
dialog.toggle_live()
start = time.monotonic()
arrivals = []
last = 0
while time.monotonic() - start < 8:
    app.processEvents()
    if dialog.last_seen != last:
        last = dialog.last_seen
        arrivals.append(last)
    time.sleep(.005)
assert len(arrivals) > 10, 'Too few preview frames reached Qt'
print({'qt_preview_fps': round((len(arrivals)-1)/(arrivals[-1]-arrivals[0]), 2),
       'first_frame_s': round(arrivals[0]-start, 2),
       'resolution': (dialog.last_result['width'], dialog.last_result['height']),
       'window_size': (dialog.width(), dialog.height())})
dialog.stop_camera()
assert dialog.process.state() == QProcess.ProcessState.NotRunning
assert dialog.last_result is None
print('stop released worker and cleared preview')
dialog.close()
