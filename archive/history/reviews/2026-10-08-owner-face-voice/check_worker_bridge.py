"""Real owner worker startup/lease tests; no capture command or owner store access."""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen'


def check(drop_lease):
    from PySide6.QtCore import QProcess
    from PySide6.QtTest import QTest
    from desktop.owner_biometrics import OwnerCapture
    from security.policy import Session
    worker=OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()+100))
    state=dict(ready=False,failed=False,stopped=False)
    def ready():
        state['ready']=True
        if drop_lease:
            worker.lease.stop()
        else:
            worker.stop()
    worker.ready.connect(ready)
    worker.failed.connect(lambda:state.__setitem__('failed',True))
    worker.stopped.connect(lambda:state.__setitem__('stopped',True))
    started=time.monotonic()
    with patch.dict(os.environ,{'NVIDIA_API_KEY':'synthetic-secret','LYA_DATA_DIR':'synthetic-private-path'}):
        worker.start()
    environment=worker.process.processEnvironment()
    assert not environment.contains('NVIDIA_API_KEY') and not environment.contains('LYA_DATA_DIR')
    while time.monotonic()-started<60 and not state['stopped']:
        QTest.qWait(50)
    try:
        assert state['ready'] and state['stopped'],state
        assert state['failed'] is drop_lease,state
        assert worker.process.state()==QProcess.ProcessState.NotRunning
        assert not any(worker.samples.values()) and worker.pending is None
        return dict(**state,seconds=round(time.monotonic()-started,3),capture_requested=False,provider_environment_excluded=True)
    finally:
        worker.stop()
        worker.process.waitForFinished(1000)


if __name__=='__main__':
    from PySide6.QtWidgets import QApplication
    app=QApplication([])
    app.setQuitOnLastWindowClosed(False)
    data=dict(date='2026-10-09',normal_cancel=check(False),parent_lease_loss=check(True),real_sensors=False,owner_store=False)
    (Path(__file__).parent/'worker-bridge.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))
