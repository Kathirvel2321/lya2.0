"""One bounded local face observation. No profile storage, network or owner authority."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from security.owner_capture import HASHES, YUNET, SFACE, guard
from security.owner_profiles import FACE_MODEL, checked_vector


def snapshot(detector,encoder,valid,camera_factory=None,with_image=False):
    import cv2
    import numpy as np
    if not valid():
        raise RuntimeError('cancelled')
    camera = (camera_factory or (lambda:cv2.VideoCapture(0,cv2.CAP_DSHOW)))()
    frame = None
    try:
        if not camera.isOpened():
            raise RuntimeError('camera')
        camera.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
        # A few device warm-up frames make up one observation, never a monitoring loop.
        for _ in range(3):
            if not valid():
                raise RuntimeError('cancelled')
            ok,raw = camera.read()
            if not ok or raw is None or raw.ndim!=3 or raw.shape[2]!=3 or raw.size>1920*1080*3:
                raise RuntimeError('camera')
            if frame is not None:
                frame.fill(0)
            frame = cv2.resize(raw,(640,480))
            raw.fill(0)
        camera.release()
        if not valid():
            raise RuntimeError('cancelled')
        _,faces = detector.detect(frame)
        if faces is None or len(faces)!=1:
            return None
        face = faces[0]
        x,y,w,h = face[:4]
        crop = frame[max(0,int(y)):min(480,int(y+h)),max(0,int(x)):min(640,int(x+w))]
        if (w<90 or h<110 or not crop.size or x<5 or y<5 or x+w>635 or y+h>475
                or not 35<=crop.mean()<=225
                or cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()<30):
            return None
        vector = encoder.feature(encoder.alignCrop(frame,face)).reshape(-1)
        vector /= max(float(np.linalg.norm(vector)),1e-9)
        checked = checked_vector(vector.tolist(),FACE_MODEL) if valid() else None
        if checked is None or not with_image:
            return checked
        # Store only a bounded face crop, never the complete room frame.
        pad = 24
        left, top = max(0,int(x)-pad), max(0,int(y)-pad)
        right, bottom = min(640,int(x+w)+pad), min(480,int(y+h)+pad)
        crop = frame[top:bottom,left:right]
        crop = cv2.resize(crop,(min(320,crop.shape[1]),min(320,crop.shape[0])))
        ok, encoded = cv2.imencode('.jpg',crop,[cv2.IMWRITE_JPEG_QUALITY,70])
        photo = encoded.tobytes() if ok and encoded.size <= 160000 else None
        return dict(vector=checked, photo=photo)
    finally:
        camera.release()
        if frame is not None:
            frame.fill(0)


def main():
    expires = float(sys.argv[1])
    if not time.time()<expires<=time.time()+30:
        raise ValueError('deadline')
    lease = dict(until=time.monotonic()+8,connected=True,camera_until=float('inf'))
    def read():
        try:
            while sys.stdin.buffer.readline(8)==b'lease\n':
                lease['until']=time.monotonic()+3
        finally:
            lease['connected']=False
    threading.Thread(target=read,daemon=True).start()
    valid = lambda:(lease['connected'] and time.monotonic()<min(lease['until'],lease['camera_until']) and time.time()<expires)
    def watchdog():
        while valid():
            time.sleep(.1)
        os._exit(1)
    threading.Thread(target=watchdog,daemon=True).start()
    import cv2
    cv2.setNumThreads(2)
    for path,digest in HASHES.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('model')
    detector = cv2.FaceDetectorYN.create(str(YUNET),'',(640,480),.85)
    encoder = cv2.FaceRecognizerSF.create(str(SFACE),'')
    sys.addaudithook(guard)
    print(json.dumps(dict(kind='camera')),flush=True)
    lease['camera_until']=time.monotonic()+3
    observation = snapshot(detector,encoder,valid,with_image=True)
    if not valid():
        raise RuntimeError('cancelled')
    vector = observation.get('vector') if isinstance(observation,dict) else observation
    photo = observation.get('photo') if isinstance(observation,dict) else None
    print(json.dumps(dict(kind='result',vector=vector,
                          image=base64.b64encode(photo).decode('ascii') if photo else None),
                      allow_nan=False),flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception:
        raise SystemExit(1)
