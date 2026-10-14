"""Run existing launcher tests with fake config and workspace-only temp paths."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
with tempfile.TemporaryDirectory(dir=HERE,prefix='.launcher-') as directory:
    assert Path(directory).resolve().is_relative_to(ROOT)
    with patch.object(tempfile,'tempdir',directory), patch('cloud.probe_models.load_values',return_value={}):
        import test_nvidia_launcher
        suite = unittest.defaultTestLoader.loadTestsFromModule(test_nvidia_launcher)
        with (HERE/'launcher-validation.txt').open('w',encoding='utf-8') as stream:
            result = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
print('Isolated launcher tests:',result.testsRun,'success:',result.wasSuccessful())
raise SystemExit(0 if result.wasSuccessful() else 1)
