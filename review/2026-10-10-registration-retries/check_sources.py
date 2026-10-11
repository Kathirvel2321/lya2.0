"""Syntax, whitespace and normal-launcher imports; no app or sensors started."""
import ast
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'desktop')]
FILES=['desktop/owner_setup.py','desktop/owner_biometrics.py','desktop/owner_scan.py',
       'security/owner_capture.py','security/owner_profiles.py','test_owner_profiles.py',
       'review/2026-10-10-registration-retries/check_retries.py',
       'review/2026-10-10-registration-retries/check_sources.py']
for name in FILES:
    source=(ROOT/name).read_text(encoding='utf-8')
    ast.parse(source,filename=name)
    assert all(line==line.rstrip() for line in source.splitlines()),name
from experience import OrbDesktop
from desktop.owner_biometrics import OwnerCapture
report=dict(date='2026-10-10',syntax=True,whitespace=True,usual_launcher_import=True,files=FILES,
            real_owner_store=False,real_sensors=False,app_started=False)
Path(__file__).with_name('source-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
