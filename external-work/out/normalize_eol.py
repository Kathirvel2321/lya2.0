"""One-off maintenance: normalise CRLF to LF so text edits apply predictably."""
import sys
from pathlib import Path

for name in sys.argv[1:]:
    path = Path(name)
    if not path.exists():
        print('missing', name)
        continue
    data = path.read_bytes()
    if b'\r\n' in data:
        path.write_bytes(data.replace(b'\r\n', b'\n'))
        print('normalised', path.name)
    else:
        print('unchanged ', path.name)
