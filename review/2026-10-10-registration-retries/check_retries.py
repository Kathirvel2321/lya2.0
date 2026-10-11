"""Fake keys, temporary encrypted stores and synthetic sensors only."""
import importlib.util
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('registration_retry_checks',OUT.parent/'2026-10-09-visitor-access/check_visitors.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.OUT=OUT

if __name__=='__main__':
    result=checks.main()
    report=OUT/'validation.json'
    data=json.loads(report.read_text(encoding='utf-8'))
    data['date']='2026-10-10'
    report.write_text(json.dumps(data,indent=2),encoding='utf-8')
    raise SystemExit(result)
