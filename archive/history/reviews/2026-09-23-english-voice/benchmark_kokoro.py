"""One bounded public Kokoro check using already installed model files only."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        import win32api
        import win32process
        import kokoro_onnx
        import numpy as np
        import wave
        sys.path.insert(0, str(ROOT))
        from audio.synthesis import KokoroSession, session
        win32process.SetPriorityClass(win32api.GetCurrentProcess(),
                                      win32process.BELOW_NORMAL_PRIORITY_CLASS)
        started = time.perf_counter()
        model = ROOT / 'models' / 'voice' / 'kokoro-v1.0.int8.onnx'
        voices = ROOT / 'models' / 'voice' / 'voices-v1.0.bin'
        engine = kokoro_onnx.Kokoro.from_session(KokoroSession(session(model)), str(voices))
        samples, rate = engine.create('Hi, I am LYA. I am here with you.',
                                      voice='af_heart', speed=0.97)
        target = OUT / 'kokoro-heart.wav'
        data = (np.clip(samples, -1, 1) * 32767).astype('<i2')
        with wave.open(str(target), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(data.tobytes())
        memory = win32process.GetProcessMemoryInfo(win32api.GetCurrentProcess())
        print(json.dumps({'wall_s': round(time.perf_counter() - started, 2),
                          'audio_s': round(len(samples) / rate, 2),
                          'peak_mb': round(memory['PeakWorkingSetSize'] / 1048576),
                          'file': str(target)}))
        return
    try:
        result = subprocess.run([sys.executable, str(__file__), '--child'],
                                cwd=ROOT, capture_output=True, text=True,
                                timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        print(result.stdout or result.stderr or f'exit {result.returncode}')
        raise SystemExit(result.returncode)
    except subprocess.TimeoutExpired:
        print('TIMEOUT: Kokoro could not render within 20 seconds')
        raise SystemExit(2)


if __name__ == '__main__':
    main()
