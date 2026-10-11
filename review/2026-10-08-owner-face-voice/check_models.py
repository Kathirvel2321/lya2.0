"""Real CPU models, public OpenCV image and existing synthetic LYA greeting only."""
import ctypes
import json
import os
from pathlib import Path
import sys
import time
import wave

os.environ['NUMBA_DISABLE_JIT'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    import cv2
    import numpy as np
    from scipy.signal import resample_poly
    from security import owner_capture as worker
    from security.owner_profiles import matches, FACE_MODEL, VOICE_MODEL
    from audio import voice
    frame = cv2.resize(cv2.imread(str(Path(__file__).parent/'public-opencv-fixture.jpg')), (640,480))
    with wave.open(str(ROOT/'desktop/assets/wake-greeting.wav'),'rb') as source:
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32)/32768
        samples = samples.reshape(-1,source.getnchannels()).mean(axis=1)
        samples = resample_poly(samples,16000,source.getframerate()).astype(np.float32)
    audio = np.resize(samples,320000)
    started, cpu = time.monotonic(), time.process_time()
    from unittest.mock import patch
    with patch.object(voice, '_input_device', return_value=17):
        capture = worker.Capture()
    load_seconds = time.monotonic()-started
    events = {}
    worker.emit = lambda kind, **_: events.__setitem__(kind, events.get(kind,0)+1)
    class Camera:
        released = False
        def isOpened(self): return True
        def set(self,*_): return True
        def read(self): return True,frame.copy()
        def release(self): self.released=True
    class Stream:
        offset = 0
        closed = False
        device = None
        def __init__(self, **kwargs): self.device=kwargs.get('device')
        def __enter__(self): return self
        def __exit__(self,*_): self.closed=True
        def read(self,n):
            result=audio[self.offset:self.offset+n].copy().reshape(-1,1)
            self.offset+=n
            return result,False
    camera, stream = Camera(), Stream()
    sys.addaudithook(worker.guard)
    face = capture.face_sample(0,lambda:True,camera_factory=lambda:camera)
    def make_stream(**kwargs):
        assert kwargs['device']==17
        return stream
    with patch.object(voice, '_input_device', return_value=17):
        speech = capture.voice_sample(lambda:True,stream_factory=make_stream)
    public_face_consistent = matches(face,[face],FACE_MODEL)
    synthetic_voice_consistent = matches(speech,[speech],VOICE_MODEL)
    class Memory(ctypes.Structure):
        _fields_ = [('cb',ctypes.c_uint32),('PageFaultCount',ctypes.c_uint32)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
            'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    usage=Memory()
    usage.cb=ctypes.sizeof(usage)
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    psapi=ctypes.WinDLL('psapi')
    psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(usage),usage.cb):
        raise OSError('Synthetic resource check unavailable.')
    wall=time.monotonic()-started
    print(json.dumps(dict(date='2026-10-09',models_ready=True,face_dimension=len(face),voice_dimension=len(speech),
        public_face_consistent=public_face_consistent,synthetic_voice_consistent=synthetic_voice_consistent,
        camera_released=camera.released,microphone_closed=stream.closed,events=events,
        load_seconds=round(load_seconds,3),total_seconds=round(wall,3),
        cpu_percent_one_core=round(100*(time.process_time()-cpu)/wall,3),
        working_mib=round(usage.WorkingSetSize/1048576,2),peak_mib=round(usage.PeakWorkingSetSize/1048576,2),
        raw_owner_data=False,real_sensors=False,network_during_capture=False,
        note='Model/worker fixture check only; self-consistency is not accuracy, liveness or live owner qualification.'),indent=2))


if __name__=='__main__':
    main()
