"""Existing face models and public fixture only; camera factory cannot open a device."""
import ctypes
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def main():
    import cv2
    import numpy as np
    from security.owner_capture import YUNET,SFACE,guard
    from security.familiar_capture import snapshot
    started,cpu=time.monotonic(),time.process_time()
    cv2.setNumThreads(2)
    frame=cv2.resize(cv2.imread(str(ROOT/'review/2026-10-08-owner-face-voice/public-opencv-fixture.jpg')),(640,480))
    detector=cv2.FaceDetectorYN.create(str(YUNET),'',(640,480),.85)
    encoder=cv2.FaceRecognizerSF.create(str(SFACE),'')
    class Camera:
        reads=0
        closed=False
        def isOpened(self):return True
        def set(self,*_):pass
        def read(self):
            self.reads+=1
            return True,frame.copy()
        def release(self):self.closed=True
    camera=Camera()
    sys.addaudithook(guard)
    result=snapshot(detector,encoder,lambda:True,camera_factory=lambda:camera)
    assert result is not None and len(result)==128 and camera.closed and camera.reads==3
    class Memory(ctypes.Structure):
        _fields_=[('cb',ctypes.c_uint32),('PageFaultCount',ctypes.c_uint32)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
             'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    usage=Memory()
    usage.cb=ctypes.sizeof(usage)
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    psapi=ctypes.WinDLL('psapi')
    psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32]
    assert psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(usage),usage.cb)
    wall=time.monotonic()-started
    print(json.dumps(dict(date='2026-10-09',public_fixture=True,face_dimension=len(result),
        fake_camera_reads=camera.reads,camera_released=camera.closed,seconds=round(wall,3),
        cpu_percent_one_core=round(100*(time.process_time()-cpu)/wall,3),
        peak_mib=round(usage.PeakWorkingSetSize/1048576,2),real_sensor=False,
        writes_or_network_during_capture=False,note='One public fixture through real face models; not live owner accuracy or full-app resource acceptance.'),indent=2))


if __name__=='__main__':main()
