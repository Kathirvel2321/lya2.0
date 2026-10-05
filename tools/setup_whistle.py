"""Explicit pinned public-asset setup; never imports the runtime or opens audio."""
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio.local_whistle import MODEL, HASHES, verify_assets

ASSETS = {
    'client.whl': ('https://files.pythonhosted.org/packages/8e/7c/90891805111f2506ce7af54f98b99f92e0ff2d6f48053309b468f85e3180/cactus_needle-3.1.0-py3-none-any.whl',
                   HASHES['client.whl'], 106372),
    'engine.whl': ('https://huggingface.co/Cactus-Compute/needle3/resolve/c7c415a3d1b3d929014bc6e866d51ebb971f7089/python/cactus_needle-3.1.0-py3-none-win_amd64.whl',
                   '4f5fc86abfc50d551cdb237a34b501f36d82d4b6f5911ee7bec4e9532d44dd95', 683889),
    'whistle.cact': ('https://huggingface.co/Cactus-Compute/whistle/resolve/b358ddadd89b7a713b5aa131f23032d3cca1b251/whistle.cact',
                    HASHES['whistle.cact'], 16919407),
}


def fetch(name, url, digest, size):
    path = MODEL / name
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
        return path
    print('Downloading public asset: ' + name, flush=True)
    with urllib.request.urlopen(url, timeout=30) as response:
        blob = response.read(size + 1)
    if len(blob) != size or hashlib.sha256(blob).hexdigest() != digest:
        raise RuntimeError('Publisher checksum/size verification failed: ' + name)
    partial = path.with_suffix(path.suffix + '.part')
    partial.write_bytes(blob)
    partial.replace(path)
    return path


def main():
    MODEL.mkdir(parents=True, exist_ok=True)
    evidence = []
    for name, (url, digest, size) in ASSETS.items():
        path = fetch(name, url, digest, size)
        evidence.append({'file': name, 'url': url, 'sha256': digest, 'bytes': size})
        if name == 'engine.whl':
            with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
                library = archive.read('needle/libneedle3.dll')
            if hashlib.sha256(library).hexdigest() != HASHES['libneedle3.dll']:
                raise RuntimeError('Extracted runtime integrity check failed.')
            (MODEL / 'libneedle3.dll').write_bytes(library)
    verify_assets()
    license_url = 'https://huggingface.co/Cactus-Compute/whistle/resolve/b358ddadd89b7a713b5aa131f23032d3cca1b251/LICENSE'
    with urllib.request.urlopen(license_url, timeout=30) as response:
        license_text = response.read(11359)
    git_blob = b'blob ' + str(len(license_text)).encode() + b'\0' + license_text
    if len(license_text) != 11358 or hashlib.sha1(git_blob).hexdigest() != 'd645695673349e3947e8e5ae42332d0ac3164cd7':
        raise RuntimeError('Publisher license integrity check failed.')
    (MODEL / 'LICENSE').write_bytes(license_text)
    (MODEL / 'source.json').write_text(json.dumps({'version': '3.1.0', 'assets': evidence,
                                                 'runtime_sha256': HASHES['libneedle3.dll'],
                                                 'license_url': license_url}, indent=2), encoding='utf-8')
    print('Whistle pilot assets verified. No runtime loaded or desktop settings changed.', flush=True)


if __name__ == '__main__':
    main()
