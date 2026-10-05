"""Download and verify public local ASR weights; never reads microphone audio."""
import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path

os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_XET'] = '1'
ROOT = Path(__file__).resolve().parents[1]
REPO = 'csukuangfj/sherpa-onnx-streaming-zipformer-en-2023-06-26'
FILES = ('encoder-epoch-99-avg-1-chunk-16-left-128.int8.onnx',
         'decoder-epoch-99-avg-1-chunk-16-left-128.onnx',
         'joiner-epoch-99-avg-1-chunk-16-left-128.int8.onnx', 'tokens.txt')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('whisper', 'streaming'), default='whisper')
    args = parser.parse_args()
    repo = 'Systran/faster-whisper-small.en' if args.engine == 'whisper' else REPO
    files = ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt') if args.engine == 'whisper' else FILES
    from huggingface_hub import hf_hub_download
    with urllib.request.urlopen('https://huggingface.co/api/models/' + repo + '?blobs=true', timeout=30) as response:
        metadata = json.load(response)
    revision = metadata['sha']
    target = ROOT / 'models/speech' / ('whisper-small-en' if args.engine == 'whisper' else 'zipformer-en')
    target.mkdir(parents=True, exist_ok=True)
    evidence = []
    for name in files:
        print('Downloading public model file: ' + name, flush=True)
        path = Path(hf_hub_download(repo, name, revision=revision, local_dir=str(target), token=False))
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        sibling = next(item for item in metadata['siblings'] if item['rfilename'] == name)
        expected = sibling.get('lfs', {}).get('sha256')
        if expected and digest != expected:
            raise RuntimeError('Model integrity check failed: ' + name)
        evidence.append(dict(file=name, bytes=path.stat().st_size, sha256=digest,
                             publisher_lfs_hash_matched=bool(expected)))
    (target / 'source.json').write_text(json.dumps(dict(repo=repo, revision=revision, files=evidence), indent=2), encoding='utf-8')
    print('Local model ready: ' + str(target), flush=True)


if __name__ == '__main__':
    main()
