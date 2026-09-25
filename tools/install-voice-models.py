"""Restore pinned public voice assets. Run explicitly; never called by speech playback."""
import hashlib
import json
from pathlib import Path
import requests

root = Path(__file__).resolve().parents[1] / 'models' / 'voice'
for item in json.loads((root / 'manifest.json').read_text(encoding='utf-8')):
    name = item['file']
    if Path(name).name != name:
        raise ValueError('Invalid asset name')
    target = root / name
    def matches(path):
        return path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    if matches(target):
        print(name, 'verified')
        continue
    partial = target.with_name(name + '.part')
    count = 0
    with requests.get(item['url'], stream=True, timeout=(20,60)) as response:
        response.raise_for_status()
        with partial.open('wb') as output:
            for chunk in response.iter_content(1024 * 1024):
                count += len(chunk)
                if count > item['bytes']:
                    raise ValueError('Asset larger than pinned size')
                output.write(chunk)
    if count != item['bytes'] or not matches(partial):
        raise ValueError('Asset verification failed')
    partial.replace(target)
    print(name, 'installed and verified')
