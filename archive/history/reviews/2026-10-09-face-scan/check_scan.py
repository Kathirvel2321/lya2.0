"""Isolated fake-owner checks and public-fixture native preview; no sensor access."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path[:0] = [str(ROOT), str(ROOT/'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    from cryptography.fernet import Fernet
    import cv2
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from security import vault
    from security.owner_capture import YUNET, face_tracking
    from storage import store
    from desktop.owner_setup import OwnerSetupDialog
    from desktop.owner_biometrics import OwnerCapture
    from security.policy import Session
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    cv2.setNumThreads(2)
    with tempfile.TemporaryDirectory(prefix='lya-scan-check-') as temp:
        base = Path(temp)
        key = Fernet(Fernet.generate_key())
        with patch.object(vault, '_F', key), patch.object(vault, '_get_fernet', return_value=key), \
             patch.object(store, 'get_data_dir', return_value=base/'defaults'), \
             patch.dict(os.environ, {'LYA_DATA_DIR': str(base/'defaults')}):
            modules = ['test_owner_profiles', 'test_passkeys', 'test_approval',
                       'desktop.check_experience', 'test_legacy_retirement']
            result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            fixture = ROOT/'review/2026-10-08-owner-face-voice/public-opencv-fixture.jpg'
            frame = cv2.resize(cv2.imread(str(fixture)), (640,480))
            detector = cv2.FaceDetectorYN.create(str(YUNET), '', (640,480), .85, .3, 5000)
            _, faces = detector.detect(frame)
            tracking = face_tracking(faces)
            assert tracking['faces'] == 1
            ok, jpg = cv2.imencode('.jpg', cv2.resize(cv2.flip(frame,1),(320,240)), [cv2.IMWRITE_JPEG_QUALITY,65])
            assert ok
            import base64
            with patch('desktop.setup_speech.SetupSpeech.say'):
                dialog = OwnerSetupDialog(db_path=base/'preview.enc')
                dialog.show()
                app.processEvents()
                dialog.stage = 'face'
                dialog.awaiting_guidance = True
                dialog.next.setEnabled(False)
                dialog.repeat.setEnabled(False)
                dialog.show_face_stage(True)
                dialog.resize(1280,760)
                app.processEvents()
                dialog.grab().save(str(OUT/'face-guidance.png'))
                worker = OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()+60))
                worker.pending = ('face',0)
                worker.preview.connect(dialog.show_preview)
                worker.tracking.connect(dialog.show_tracking)
                worker.handle_packet(dict(kind='preview', image=base64.b64encode(jpg).decode('ascii'), tracking=tracking))
                dialog.scan.set_capture(1,False)
                dialog.scan.phase = .5
                app.processEvents()
                dialog.grab().save(str(OUT/'face-scan-wide.png'))
                cpu, started = time.process_time(), time.monotonic()
                for _ in range(60):
                    QTest.qWait(50)
                widget_cpu = round(100*(time.process_time()-cpu)/(time.monotonic()-started),3)
                dialog.resize(720,620)
                app.processEvents()
                dialog.grab().save(str(OUT/'face-scan-narrow.png'))
                dialog.resize(320,280)
                app.processEvents()
                dialog.grab().save(str(OUT/'face-scan-minimum.png'))
                worker.stop()
                dialog.stage = 'voice'
                dialog.show_face_stage(False)
                dialog.mark.mode, dialog.mark.active = 'microphone', True
                app.processEvents()
                dialog.grab().save(str(OUT/'voice-restored.png'))
                dialog.reject()
            summary = dict(date='2026-10-09',tests=result.testsRun,failures=len(result.failures),
                errors=len(result.errors),skipped=len(result.skipped),success=result.wasSuccessful(),
                modules=modules,public_fixture_detector_to_validated_native_preview=True,
                actual_landmarks=len(tracking['points']),preview_dimensions=[320,240],preview_max_fps=2,
                widget_max_fps=10,active_widget_cpu_percent_one_core=widget_cpu,
                real_owner_store=False,real_sensors=False,live_phone=False,provider_inference=False,
                note='Public fixture through existing detector/strict preview bridge, synthetic owner suites and widget only; not live enrollment or whole-app resource acceptance.')
            (OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print(json.dumps(summary,indent=2))
            return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
