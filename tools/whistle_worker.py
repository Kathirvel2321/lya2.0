"""Speech-only child; WAV on stdin, one JSON candidate on stdout, no disk audio."""
import array
import io
import json
import os
from pathlib import Path
import sys
import wave


def main():
    # Parent attaches Windows memory/CPU limits before providing this input.
    data = sys.stdin.buffer.read(16000 * 2 * 30 + 65537)
    if not data or len(data) > 16000 * 2 * 30 + 65536:
        raise ValueError('Invalid input size')
    folder = Path(sys.argv[1]).resolve()
    os.environ.update(NEEDLE_TELEMETRY='0', DO_NOT_TRACK='1', HF_HUB_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', NEEDLE3_LIB_PATH=str(folder / 'libneedle3.dll'))
    def network_disabled(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'urllib.Request'):
            raise RuntimeError('Speech-worker Python networking is disabled.')
    sys.addaudithook(network_disabled)
    sys.path.insert(0, str(folder / 'client.whl'))
    import needle
    with wave.open(io.BytesIO(data), 'rb') as sound:
        if (sound.getframerate(), sound.getnchannels(), sound.getsampwidth()) != (16000, 1, 2):
            raise ValueError('Invalid audio format')
        pcm = array.array('h', sound.readframes(sound.getnframes()))
    samples = array.array('f', (sample / 32768.0 for sample in pcm))
    # Whistle only: no Needle agent, tool schema, expected answer or keyword bias.
    model = needle.Whistle(weights=str(folder / 'whistle.cact'))
    result = model.transcribe(samples, language='en', keywords=None, word_timestamps=True)
    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not expose private samples, paths or native error payloads in logs.
        sys.stdout.write(json.dumps({'error_kind': type(error).__name__,
                                    'os_code': getattr(error, 'winerror', None)}))
        sys.exit(1)
