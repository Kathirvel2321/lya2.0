"""Actual installed worker starts at the voice stage, then cancels; no capture request."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('resumed_worker_check',OUT.parent/'2026-10-08-owner-face-voice/check_worker_bridge.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

if __name__=='__main__':
    from PySide6.QtWidgets import QApplication
    from desktop.owner_biometrics import OwnerCapture
    app=QApplication([])
    app.setQuitOnLastWindowClosed(False)
    workers=[]
    def seeded(*args,**kwargs):
        worker=OwnerCapture(*args,**kwargs)
        worker.samples['face']=[[1.0]+[0.0]*127 for _ in range(3)]
        workers.append(worker)
        return worker
    with patch('desktop.owner_biometrics.OwnerCapture',side_effect=seeded):
        result=checks.check(False)
    assert workers[0].initial_step==3
    result.update(date='2026-10-09',initial_step=3,real_models_loaded=True,real_sensors=False,real_owner_store=False)
    (OUT/'resumed-worker.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
