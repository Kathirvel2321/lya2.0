"""Native screenshots with a public image and fake storage; never opens sensors."""
import base64
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path[:0] = [str(ROOT), str(ROOT/'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    import cv2
    from cryptography.fernet import Fernet
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from desktop.familiarity import VisitorReview
    from desktop.owner_biometrics import OwnerCapture
    from desktop.owner_setup import OwnerSetupDialog
    from security import vault
    from security.owner_capture import YUNET, face_tracking
    from security.policy import Session
    from security.visitors import Visitors
    from storage import store
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    # The offscreen Windows plugin does not enumerate the installed system fonts.
    assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf') >= 0
    cv2.setNumThreads(2)
    with tempfile.TemporaryDirectory(prefix='lya-visitor-preview-') as temp:
        base = Path(temp)
        key = Fernet(Fernet.generate_key())
        with patch.object(vault, '_F', key), patch.object(vault, '_get_fernet', return_value=key), \
             patch.object(store, 'get_data_dir', return_value=base/'defaults'), \
             patch.dict(os.environ, {'LYA_DATA_DIR': str(base/'defaults')}), \
             patch('desktop.setup_speech.SetupSpeech.say'):
            frame = cv2.resize(cv2.imread(str(ROOT/'review/2026-10-08-owner-face-voice/public-opencv-fixture.jpg')), (640,480))
            detector = cv2.FaceDetectorYN.create(str(YUNET), '', (640,480), .85, .3, 5000)
            _, faces = detector.detect(frame)
            tracking = face_tracking(faces)
            assert tracking['faces'] == 1 and len(tracking['points']) == 5
            ok, jpg = cv2.imencode('.jpg', cv2.resize(cv2.flip(frame,1),(320,240)), [cv2.IMWRITE_JPEG_QUALITY,65])
            assert ok
            dialog = OwnerSetupDialog(db_path=base/'preview.enc')
            dialog.show()
            app.processEvents()
            dialog.stage = 'face'
            dialog.awaiting_guidance = True
            dialog.next.setEnabled(False)
            dialog.repeat.setEnabled(False)
            dialog.show_face_stage(True)
            worker = OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()+60))
            worker.pending = ('face',0)
            worker.preview.connect(dialog.show_preview)
            worker.tracking.connect(dialog.show_tracking)
            worker.handle_packet(dict(kind='preview', image=base64.b64encode(jpg).decode('ascii'), tracking=tracking))
            dialog.scan.set_capture(1,False)
            dialog.scan.phase = .5
            for name,width,height in (('face-scan-wide',1280,760),('face-scan-narrow',720,620),('face-scan-minimum',320,280)):
                dialog.resize(width,height)
                app.processEvents()
                assert dialog.grab().save(str(OUT/(name+'.png')))
            worker.stop()
            dialog.reject()
            visitors = Visitors()
            visitors.counts = dict(requests=7,limited_apps=2,blocked=1)
            review = VisitorReview(SimpleNamespace(brain=SimpleNamespace(visitors=visitors)))
            review.resize(500,270)
            review.show()
            app.processEvents()
            assert review.grab().save(str(OUT/'visitor-review.png'))
            review.reject()
    print('Four native previews saved; public fixture, fake counts, no real sensors or owner data.')


if __name__ == '__main__':
    main()
