"""Isolated registration-expiry regression suite; no real accounts or sensors."""
import importlib.util
from pathlib import Path

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('isolated_expiry_checks',OUT.parent/'2026-10-09-visitor-access/check_visitors.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.OUT=OUT

if __name__=='__main__':raise SystemExit(checks.main())
