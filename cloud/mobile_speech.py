"""Fixed Linux speech worker: bounded RAM audio, Ubuntu-only credential file."""
import base64
import json
import os
from pathlib import Path
import stat
import sys
import threading

CONFIG=Path('/home/ubuntu/lya/speech.json')
MAX_PACKET=5200000


def credential():
    # Refuse a linked, foreign-owned or group/world-readable credential.
    fd=os.open(CONFIG,os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
            raise PermissionError('Unsafe speech configuration.')
        raw=stream.read(8193)
    if len(raw)>8192:raise ValueError('Invalid speech configuration.')
    data=json.loads(raw)
    if type(data) is not dict or set(data)!={'nvidia_api_key'}:raise ValueError('Invalid speech configuration.')
    key=data['nvidia_api_key']
    if type(key) is not str or not 16<=len(key.strip())<=4096:raise ValueError('Speech credential unavailable.')
    return key.strip()


def main():
    raw=sys.stdin.buffer.readline(MAX_PACKET+1)
    if len(raw)>MAX_PACKET or not raw.endswith(b'\n'):raise ValueError('Invalid speech request.')
    packet=json.loads(raw)
    if type(packet) is not dict or set(packet)!={'audio'}:raise ValueError('Invalid speech request.')
    audio=base64.b64decode(packet['audio'],validate=True)
    if not 44<len(audio)<=120*32000+44:raise ValueError('Invalid audio size.')
    from audio.nvidia_asr import pcm_audio,transcribe
    pcm_audio(audio)
    key=credential()
    cancelled=threading.Event()
    def watch():
        os.read(sys.stdin.fileno(),1)
        cancelled.set()
    threading.Thread(target=watch,daemon=True).start()
    text=transcribe(audio,api_key=key,remote_allowed=True,cancelled=cancelled)
    if cancelled.is_set():raise InterruptedError()
    if type(text) is not str or not 1<=len(text.strip())<=4000:raise ValueError('No clear transcript.')
    print(json.dumps({'text':text.strip()}),flush=True)


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Phone speech unavailable; private details withheld.')
