"""Bounded local profile worker. Raw camera/audio remain in RAM and never enter ASR."""
import base64
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from security.owner_profiles import FACE_MODEL, VOICE_MODEL, CAPTURE_FAILURES, RETRY_FAILURES, checked_vector

SFACE = ROOT / 'models/biometric/sface-int8.onnx'
YUNET = ROOT / 'models/vision/yunet-2026may.onnx'
HASHES = {SFACE: '2b0e941e6f16cc048c20aee0c8e31f569118f65d702914540f7bfdc14048d78a',
          YUNET: 'ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0'}
VOICE_HASH = '39373b86598fa3da9fcddee6142382efe09777e8d37dc9c0561f41f0070f134e'


def emit(kind, **data):
    print(json.dumps(dict(kind=kind, **data), allow_nan=False), flush=True)


def face_tracking(faces):
    """Mirror detector coordinates into the preview; no depth or identity score."""
    count = min(2, len(faces)) if faces is not None else 0
    result = dict(faces=count, box=[], points=[])
    if count == 1:
        face = faces[0]
        clamp = lambda value: max(0., min(1., float(value)))
        left, right = clamp(1-(face[0]+face[2])/640), clamp(1-face[0]/640)
        top, bottom = clamp(face[1]/480), clamp((face[1]+face[3])/480)
        result['box'] = [left, top, max(0., right-left), max(0., bottom-top)]
        result['points'] = [[clamp(1-face[i]/640), clamp(face[i+1]/480)] for i in range(4, 14, 2)]
    return result


def guard(event, args):
    # Defense in depth; a Python guard cannot defeat malware controlling this Windows account.
    if event in ('socket.connect', 'socket.bind', 'socket.sendto', 'socket.getaddrinfo',
                 'urllib.Request', 'subprocess.Popen', 'os.system', 'os.posix_spawn'):
        raise PermissionError('Owner capture blocks networking and child commands.')
    if event == 'open':
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
            raise PermissionError('Owner capture cannot write files.')


def verify_assets():
    import importlib.util
    for path, expected in HASHES.items():
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Owner model missing or changed.')
    spec = importlib.util.find_spec('resemblyzer')
    weights = Path(spec.origin).parent / 'pretrained.pt' if spec else Path('missing')
    if not weights.is_file() or hashlib.sha256(weights.read_bytes()).hexdigest() != VOICE_HASH:
        raise RuntimeError('Owner voice model missing or changed.')
    return weights


class Capture:
    def __init__(self):
        import cv2
        import numpy as np
        import torch
        from resemblyzer import VoiceEncoder, preprocess_wav
        from unittest.mock import patch
        weights = verify_assets()
        cv2.setNumThreads(2)
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        self.detector = cv2.FaceDetectorYN.create(str(YUNET), '', (640, 480), .85)
        self.face = cv2.FaceRecognizerSF.create(str(SFACE), '')
        self.pose_side = 0
        original_load = torch.load
        def safe_load(*args, **kwargs):
            return original_load(*args, **dict(kwargs, weights_only=True))
        with patch.object(torch, 'load', safe_load):
            self.voice = VoiceEncoder(device='cpu', verbose=False, weights_fpath=weights)
        self.preprocess = preprocess_wav
        # Warm lazy audio imports using synthetic data before prohibiting all disk writes.
        self.voice.embed_utterance(np.zeros(48000, dtype=np.float32))

    def face_sample(self, index, valid, camera_factory=None):
        import cv2
        import numpy as np
        if not valid():
            raise RuntimeError('expired')
        factory = camera_factory or (lambda: cv2.VideoCapture(0, cv2.CAP_DSHOW))
        camera = factory()
        try:
            if not camera.isOpened():
                raise RuntimeError('camera')
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 15)
            started, preview_at = time.monotonic(), 0
            vectors, reason, last_hint = [], 'face_missing', ''
            while valid() and time.monotonic() - started < 15:
                tick = time.monotonic()
                ok, frame = camera.read()
                if not ok or frame is None or frame.ndim != 3 or frame.shape[2] != 3 or frame.size > 1920*1080*3:
                    raise RuntimeError('camera')
                frame = cv2.resize(frame, (640, 480))
                _, faces = self.detector.detect(frame)
                if time.monotonic() >= preview_at:
                    ok, jpg = cv2.imencode('.jpg', cv2.flip(frame, 1),
                                           [cv2.IMWRITE_JPEG_QUALITY, 65])
                    if ok and jpg.size <= 100000:
                        emit('preview', image=base64.b64encode(jpg).decode('ascii'), tracking=face_tracking(faces))
                    preview_at = tick + .1
                if faces is not None and len(faces) == 1:
                    face = faces[0]
                    x, y, w, h = face[:4]
                    eyes = abs(float(face[4] - face[6]))
                    nose_offset = (float(face[8]) - float((face[4]+face[6])/2)) / max(eyes, 1)
                    pose = (abs(nose_offset) < .22 if index == 0 else
                            abs(nose_offset) > .12 and (index == 1 or nose_offset*self.pose_side < 0))
                    crop = frame[max(0,int(y)):min(480,int(y+h)), max(0,int(x)):min(640,int(x+w))]
                    reason = ('face_position' if not (w >= 90 and h >= 110 and crop.size and x >= 5 and y >= 5
                              and x+w <= 635 and y+h <= 475) else
                              'face_pose' if not pose else 'face_light' if not 35 <= crop.mean() <= 225 else
                              'face_blur' if cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < 30 else None)
                    if reason is None and time.monotonic()-started > 1.5:
                        vector = self.face.feature(self.face.alignCrop(frame, face)).reshape(-1)
                        vector = vector / max(float(np.linalg.norm(vector)), 1e-9)
                        vectors.append(vector)
                        if len(vectors) == 3:
                            if index == 1:
                                self.pose_side = nose_offset
                            result = np.mean(vectors, axis=0)
                            result /= max(float(np.linalg.norm(result)), 1e-9)
                            return checked_vector(result.tolist(), FACE_MODEL)
                    else:
                        vectors.clear()
                else:
                    vectors.clear()
                    reason = 'face_multiple' if faces is not None and len(faces)>1 else 'face_missing'
                if reason != last_hint:
                    emit('hint', code=reason or 'face_hold')
                    last_hint = reason
                time.sleep(max(0., .1-(time.monotonic()-tick)))
            raise RuntimeError(reason or 'face_quality')
        finally:
            camera.release()

    def voice_sample(self, valid, stream_factory=None):
        if not valid():
            raise RuntimeError('expired')
        import numpy as np
        import sounddevice as sd
        import webrtcvad
        # Prepare detection before acquiring the stream so imports cannot overrun its input buffer.
        vad = webrtcvad.Vad(2)
        factory = stream_factory or sd.InputStream
        from audio.voice import _input_device
        frames, wav = [], None
        try:
            try:
                device = _input_device(sd)
                source = factory(samplerate=16000, channels=1, dtype='float32', blocksize=1600, device=device)
            except Exception:
                raise RuntimeError('voice_device') from None
            voiced_blocks, last_voice, speech_energy, speech_clipped = 0, 0, 0., 0.
            with source as stream:
                for index in range(200):
                    if not valid():
                        raise RuntimeError('expired')
                    chunk, overflow = stream.read(1600)
                    if overflow:
                        raise RuntimeError('audio_overflow')
                    if chunk.shape != (1600, 1) or not np.isfinite(chunk).all():
                        raise RuntimeError('audio_quality')
                    block = chunk.copy().reshape(-1)
                    frames.append(block)
                    energy = float(np.mean(block**2))
                    emit('meter', level=min(1.0, energy**.5*12))
                    pcm = (np.clip(block, -1, 1)*32767).astype('<i2').tobytes()
                    if any(vad.is_speech(pcm[start:start+640], 16000) for start in range(0, 3200, 640)):
                        voiced_blocks += 1
                        speech_energy += energy
                        speech_clipped += float(np.mean(np.abs(block) >= .99))
                        last_voice = index
                    if index >= 49 and voiced_blocks >= 20 and index-last_voice >= 15:
                        break
            if voiced_blocks < 20:
                raise RuntimeError('voice_no_speech')
            # Waiting silence is not part of the speaker's loudness.
            if (speech_energy/voiced_blocks)**.5 < .002:
                raise RuntimeError('voice_quiet')
            if speech_clipped/voiced_blocks > .01:
                raise RuntimeError('voice_clipped')
            wav = np.concatenate(frames)
            speech = self.preprocess(wav)
            if len(speech) < 32000 or not np.isfinite(speech).all():
                raise RuntimeError('voice_short')
            return checked_vector(self.voice.embed_utterance(speech).tolist(), VOICE_MODEL)
        except sd.PortAudioError:
            raise RuntimeError('voice_device') from None
        finally:
            if wav is not None:
                wav.fill(0)
            for chunk in frames:
                chunk.fill(0)


def run(expires_at, start_step=0):
    if type(start_step) is not int or start_step not in (0,3,4,5):
        raise ValueError('start_step')
    commands = queue.Queue(maxsize=2)
    lease = dict(until=time.monotonic()+8, connected=True)
    def read():
        try:
            for line in iter(lambda: sys.stdin.buffer.readline(129), b''):
                if len(line) > 128:
                    break
                if line == b'lease\n':
                    lease['until'] = time.monotonic()+3
                else:
                    commands.put_nowait(json.loads(line))
        except Exception:
            pass
        finally:
            lease['connected'] = False
    threading.Thread(target=read, daemon=True).start()
    valid = lambda: lease['connected'] and time.monotonic() < lease['until'] and time.time() < expires_at
    def watchdog():
        while valid():
            time.sleep(.2)
        os._exit(1)  # A blocked native camera/mic read must not outlive its parent lease.
    threading.Thread(target=watchdog, daemon=True).start()
    capture = Capture()
    sys.addaudithook(guard)
    emit('ready')
    step, awaiting_accept = start_step, False
    while step < 6:
        while valid():
            try:
                request = commands.get(timeout=.2)
                break
            except queue.Empty:
                continue
        else:
            raise RuntimeError('expired')
        kind, index = ('face', step) if step < 3 else ('voice', step-3)
        if awaiting_accept and request == dict(accept=step) and type(request.get('accept')) is int:
            step += 1
            awaiting_accept = False
            continue
        if type(request) is not dict or type(request.get('index')) is not int or request != dict(kind=kind, index=index):
            raise RuntimeError('invalid_request')
        awaiting_accept = False
        try:
            vector = capture.face_sample(index, valid) if kind == 'face' else capture.voice_sample(valid)
        except RuntimeError as exc:
            if str(exc) not in RETRY_FAILURES or not valid():
                raise
            emit('retry', code=str(exc))
            continue
        if not valid():
            raise RuntimeError('expired')
        # Advance only after the parent validates consistency; a rejected sample can be retaken.
        awaiting_accept = True
        emit('sample', profile=kind, index=index, vector=vector)
    emit('done')


if __name__ == '__main__':
    try:
        deadline = float(sys.argv[1])
        start_step = int(sys.argv[2]) if len(sys.argv)>2 else 0
        if not time.time() < deadline <= time.time()+305:
            raise ValueError('deadline')
        run(deadline,start_step)
    except Exception as exc:
        code = str(exc) if str(exc) in CAPTURE_FAILURES else 'capture_failed'
        emit('error', code=code)  # Fixed categories only, never raw device errors or private material.
        raise SystemExit(1)
