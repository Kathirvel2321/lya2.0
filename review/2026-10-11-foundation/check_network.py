"""Check private TLS, unchanged page and unsigned rejection; no auth/provider calls."""
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
origin=json.loads((ROOT/'desktop/mobile.local.json').read_text())['origin']
assert re.fullmatch(r'https://[a-z0-9-]+\.[a-z0-9-]+\.ts\.net',origin)
with urllib.request.urlopen(origin+'/',timeout=12) as reply:
    page=reply.read().decode('utf-8')
    assert reply.status==200 and reply.headers['Cache-Control']=='no-store'
    assert "frame-ancestors 'none'" in reply.headers['Content-Security-Policy']
    assert re.sub(r'nonce="[^"]+"','nonce="__NONCE__"',page)==(ROOT/'cloud/mobile.html').read_text(encoding='utf-8')
request=urllib.request.Request(origin+'/session',b'{}',headers={'Origin':origin,'Content-Type':'application/json'})
try:
    urllib.request.urlopen(request,timeout=12)
    raise AssertionError('Unsigned session accepted')
except urllib.error.HTTPError as reply:
    assert reply.code==403
    assert re.fullmatch(r'request;dur=\d+\.\d{3}',reply.headers['Server-Timing'])
    assert reply.headers['Cache-Control']=='no-store'
result={'private_tls':True,'page_matches_source':True,'unsigned_session_rejected':True,
        'timing_through_private_proxy':True,'provider_called':False,'real_phone_tested':False}
Path(__file__).with_name('network.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
