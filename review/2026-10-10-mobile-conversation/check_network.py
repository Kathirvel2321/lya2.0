"""Private HTTPS/headers only: no sign-in, audio or inference."""
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
origin=json.loads((ROOT/'desktop/mobile.local.json').read_text())['origin']
with urllib.request.urlopen(origin+'/',timeout=12) as r:
    html=r.read().decode('utf-8');headers=r.headers
    assert r.status==200
    # Each response has a fresh CSP nonce; it is intentionally different from source.
    assert re.sub(r'nonce="[^"]+"','nonce="__NONCE__"',html)==(ROOT/'cloud/mobile.html').read_text(encoding='utf-8')
    assert headers['Cache-Control']=='no-store'
    assert headers['Permissions-Policy']=='camera=(), microphone=(self)'
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
req=urllib.request.Request(origin+'/session',b'{}',headers={'Origin':origin,'Content-Type':'application/json'})
try:
    urllib.request.urlopen(req,timeout=12)
    raise AssertionError('Unsigned session accepted')
except urllib.error.HTTPError as e:assert e.code==403
result=dict(private_tls=True,live_page_matches_source=True,no_store=True,camera_disabled=True,
            microphone_requires_permission=True,unsigned_session_denied=True,real_phone=False)
Path(__file__).with_name('live-network.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
