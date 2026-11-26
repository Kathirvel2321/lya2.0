"""Bounded recognition processing for consented phone samples."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv-owner/Scripts/python.exe'
FRAME_BYTES = 640 * 480 * 4
VOICE_BYTES = 5 * 16000 * 2
UPLOAD_BYTES = 3 * (FRAME_BYTES + VOICE_BYTES)


def available():
    from security.owner_capture import HASHES
    return PYTHON.is_file() and all(path.is_file() for path in HASHES)


def process(raw, deadline):
    remaining = deadline - time.monotonic()
    if len(raw) != UPLOAD_BYTES or remaining <= 0 or not available():
        raise ValueError('Phone recognition processing is unavailable.')
    environment = {key:os.environ[key] for key in ('SystemRoot', 'WINDIR', 'PATH', 'TEMP', 'TMP')
                   if key in os.environ}
    environment.update(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2',
                       NUMBA_DISABLE_JIT='1', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([str(PYTHON), '-B', '-s', str(Path(__file__).resolve())], input=raw,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment,
                            cwd=ROOT, timeout=min(60, remaining), check=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if len(result.stdout) > 32000:
        raise ValueError('Invalid profile result.')
    return json.loads(result.stdout)


def run():
    sys.path.insert(0, str(ROOT))
    import cv2
    import numpy as np
    import webrtcvad
    from security.owner_capture import Capture, guard
    from security.owner_profiles import FACE_MODEL, VOICE_MODEL, checked_vector

    capture = Capture()
    vad = webrtcvad.Vad(2)
    sys.addaudithook(guard)
    raw = sys.stdin.buffer.read(UPLOAD_BYTES + 1)
    if len(raw) != UPLOAD_BYTES:
        raise ValueError('Invalid sample length.')
    faces, voices, first_turn = [], [], 0.0
    for index in range(3):
        rgba = np.frombuffer(raw, np.uint8, count=FRAME_BYTES, offset=index * FRAME_BYTES).reshape(480, 640, 4)
        frame = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        _, detected = capture.detector.detect(frame)
        if detected is None or len(detected) != 1:
            raise ValueError('One face must be visible.')
        face = detected[0]
        x, y, w, h = face[:4]
        if not (w >= 90 and h >= 110 and x >= 5 and y >= 5 and x + w <= 635 and y + h <= 475):
            raise ValueError('Keep the whole face in view.')
        eyes = abs(float(face[4] - face[6]))
        turn = (float(face[8]) - float((face[4] + face[6]) / 2)) / max(eyes, 1)
        if (index == 0 and abs(turn) >= .22) or (index > 0 and abs(turn) <= .12) or (index == 2 and turn * first_turn >= 0):
            raise ValueError('Follow the requested face directions.')
        if index == 1:
            first_turn = turn
        crop = cv2.cvtColor(frame[int(y):int(y+h), int(x):int(x+w)], cv2.COLOR_BGR2GRAY)
        if not 35 <= crop.mean() <= 225 or cv2.Laplacian(crop, cv2.CV_64F).var() < 30:
            raise ValueError('Face lighting or sharpness was insufficient.')
        vector = capture.face.feature(capture.face.alignCrop(frame, face)).reshape(-1)
        vector /= max(float(np.linalg.norm(vector)), 1e-9)
        faces.append(checked_vector(vector.tolist(), FACE_MODEL))
        frame.fill(0)

        pcm = memoryview(raw)[3 * FRAME_BYTES + index * VOICE_BYTES:3 * FRAME_BYTES + (index + 1) * VOICE_BYTES]
        voiced = []
        for offset in range(0, VOICE_BYTES, 640):
            part = pcm[offset:offset + 640].tobytes()
            if vad.is_speech(part, 16000):
                voiced.append(part)
        if len(voiced) < 100:
            raise ValueError('Speak naturally for at least two seconds.')
        levels = np.frombuffer(b''.join(voiced), '<i2').astype(np.float32) / 32768
        if float(np.mean(levels**2))**.5 < .002 or float(np.mean(np.abs(levels) >= .99)) > .01:
            raise ValueError('Voice recording was too quiet or clipped.')
        wav = np.frombuffer(pcm, '<i2').astype(np.float32) / 32768
        speech = capture.preprocess(wav)
        if len(speech) < 32000 or not np.isfinite(speech).all():
            raise ValueError('Not enough clear speech remained.')
        voices.append(checked_vector(capture.voice.embed_utterance(speech).tolist(), VOICE_MODEL))
        wav.fill(0)
        speech.fill(0)
        levels.fill(0)
    print(json.dumps({'face':faces, 'voice':voices}, allow_nan=False))


if __name__ == '__main__':
    try:
        run()
    except Exception:
        raise SystemExit(1) from None
