"""Public fixture through the new 640x480 native preview; no sensors or owner store."""
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen'


def main():
    import cv2
    from PySide6.QtGui import QFontDatabase,QImage
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from desktop.owner_scan import FaceScan
    from security.owner_capture import YUNET,face_tracking
    app=QApplication([])
    assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')>=0
    cv2.setNumThreads(2)
    frame=cv2.resize(cv2.imread(str(ROOT/'review/2026-10-08-owner-face-voice/public-opencv-fixture.jpg')),(640,480))
    detector=cv2.FaceDetectorYN.create(str(YUNET),'',(640,480),.85)
    _,faces=detector.detect(frame)
    assert faces is not None and len(faces)==1
    ok,jpg=cv2.imencode('.jpg',cv2.flip(frame,1),[cv2.IMWRITE_JPEG_QUALITY,65])
    assert ok and jpg.size<=100000
    image=QImage.fromData(jpg.tobytes(),'JPG')
    assert (image.width(),image.height())==(640,480)
    scan=FaceScan()
    scan.resize(1224,660)
    scan.image,scan.tracking=image,face_tracking(faces)
    scan.set_capture(1,False)
    scan.show()
    app.processEvents()
    cpu,started=time.process_time(),time.monotonic()
    for _ in range(30):
        scan.image=image
        scan.update()
        QTest.qWait(100)
    usage=round(100*(time.process_time()-cpu)/(time.monotonic()-started),3)
    assert scan.grab().save(str(OUT/'face-preview.png'))
    scan.hide()
    assert not scan.timer.isActive() and scan.image is None and scan.tracking is None
    result=dict(date='2026-10-09',public_fixture=True,preview_dimensions=[640,480],preview_max_fps=10,
                preview_jpeg_bytes=int(jpg.size),active_native_widget_cpu_percent_one_core=usage,
                hidden_timer_stopped=True,hidden_frame_cleared=True,real_sensors=False,real_owner_data=False,
                note='Three-second offscreen native widget only; not live camera, full LYA or sustained system load.')
    (OUT/'preview-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
