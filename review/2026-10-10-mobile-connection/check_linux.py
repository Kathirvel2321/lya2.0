"""Synthetic connection checks in the staged Linux venv; no provider or real identity."""
import ast
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

source=(ROOT/'test_mobile.py').read_text(encoding='utf-8')
tree=ast.parse(source)
native=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeMobileChecks')
lines=source.splitlines()
script='\n'.join(lines[:native.lineno-1]).replace('from test_passkeys import SyntheticPasskeys','')
script+='\nresult=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(MobileChecks))\n'
script+="print(json.dumps(dict(tests=result.testsRun,success=result.wasSuccessful(),errors=len(result.errors),failures=len(result.failures),provider_call=False,real_owner_data=False)))\n"
remote="""import json,subprocess,sys
script=json.load(sys.stdin)['script']
prefix="import sys;sys.path.insert(0,'/opt/lya-connect');"
p=subprocess.run(['sudo','-n','-u','lya-connect','/opt/lya-connect/venv/bin/python','-I','-c',prefix+script],capture_output=True,timeout=35)
if p.returncode:raise RuntimeError('Synthetic Linux checks failed')
result=json.loads(p.stdout);assert result['success'];print(json.dumps(result))
"""
report=operator(remote,{'script':script},timeout=50)
Path(__file__).with_name('linux-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
