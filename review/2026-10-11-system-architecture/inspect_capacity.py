"""Read resource counters only; no profile, provider, configuration or store output."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.setup_mobile_connection import operator

PROGRAM = r'''
import json, os, pathlib, platform, shutil, subprocess
memory = {}
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
    key, value = line.split(':', 1)
    if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
        memory[key] = int(value.split()[0]) * 1024
disk = shutil.disk_usage('/var/lib')
result = subprocess.run(['systemctl','show','lya-connect.service',
    '-p','MemoryCurrent','-p','MemoryMax','-p','TasksCurrent','-p','TasksMax',
    '-p','ActiveState'], capture_output=True, text=True, check=True, timeout=5)
service = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
print(json.dumps(dict(architecture=platform.machine(), logical_cpus=os.cpu_count(),
    memory_bytes=memory, disk_bytes=dict(total=disk.total, used=disk.used, free=disk.free),
    mobile_service=service, read_only=True, billing_and_tenancy_not_inspected=True)))
'''

if __name__ == '__main__':
    result = operator(PROGRAM, timeout=25)
    assert result['read_only'] and result['disk_bytes']['total'] > 0
    assert set(result['memory_bytes']) == {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}
    output = Path(__file__).with_name('capacity-observed.json')
    output.write_text(json.dumps({'date': '2026-10-11', 'oracle': result}, indent=2) + '\n')
    print(json.dumps(result, indent=2))
