"""Existing real worker cancellation checks; never sends a sensor capture request."""
import importlib.util
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('synthetic_worker_bridge',OUT.parent/'2026-10-08-owner-face-voice/check_worker_bridge.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

if __name__=='__main__':
    from PySide6.QtWidgets import QApplication
    app=QApplication([])
    app.setQuitOnLastWindowClosed(False)
    result=dict(date='2026-10-09',normal_cancel=checks.check(False),parent_lease_loss=checks.check(True),
                real_sensors=False,owner_store=False)
    (OUT/'worker-bridge.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
