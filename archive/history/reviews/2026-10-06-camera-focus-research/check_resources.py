"""Public-fixture worker benchmark; fake camera, no owner store/network or recordings."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='2', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
import ctypes
import json
import math
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from vision import scan
sys.addaudithook(scan.camera_worker_guard)
import cv2


class Memory(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
        (name, ctypes.c_size_t) for name in ('peak_working', 'working', 'peak_paged', 'paged',
                                            'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]


def working_memory():
    value = Memory()
    value.cb = ctypes.sizeof(value)
    kernel = ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    reader = ctypes.WinDLL('psapi').GetProcessMemoryInfo
    reader.argtypes = [ctypes.c_void_p, ctypes.POINTER(Memory), ctypes.c_ulong]
    if not reader(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise ctypes.WinError()
    return {'working_mib': round(value.working / 1024**2, 2),
            'peak_working_mib': round(value.peak_working / 1024**2, 2)}


def main():
    frame = cv2.imread(str(ROOT / 'review/2026-10-05-camera-objects/public-hand-fixture.png'))
    assert frame is not None
    scale = min(1280/frame.shape[1], 720/frame.shape[0])
    frame = cv2.resize(frame, (round(frame.shape[1]*scale), round(frame.shape[0]*scale)))
    before = working_memory()
    loaded = time.perf_counter()
    engine = scan.VisionEngine()
    load_ms = (time.perf_counter()-loaded)*1000
    analyze = engine.analyze
    durations = []
    def measured(image):
        began = time.perf_counter()
        result = analyze(image)
        durations.append((time.perf_counter()-began)*1000)
        return result
    engine.analyze = measured
    class Camera:
        released = False
        def isOpened(self): return True
        def set(self, *args): return True
        def read(self): return True, frame
        def release(self): self.released = True
    camera = Camera()
    frames = checked = max_packet = 0
    cpu, wall = time.process_time(), time.perf_counter()
    with patch.object(scan, 'VisionEngine', return_value=engine):
        for packet in scan.live_frames(lambda *args: camera, max_seconds=10, authorized=lambda: True):
            frames += 1
            checked += 'checked_image' in packet
            max_packet = max(max_packet, len(json.dumps(packet)))
    elapsed, cpu_seconds = time.perf_counter()-wall, time.process_time()-cpu
    assert camera.released and len(durations) <= math.ceil(elapsed*2)+1
    result = {'scope': '10s worker-only simulation with upstream public hand image and fake camera; no real sensor or GUI/voice load.',
              'elapsed_seconds': round(elapsed, 3), 'preview_frames': frames,
              'analysis_jobs': len(durations), 'checked_image_packets': checked,
              'model_load_ms': round(load_ms, 2), 'analysis_median_ms': round(statistics.median(durations), 2),
              'analysis_max_ms': round(max(durations), 2),
              'cpu_percent_of_one_logical_core': round(cpu_seconds/elapsed*100, 2),
              'cpu_percent_of_logical_machine_capacity': round(cpu_seconds/elapsed*100/(os.cpu_count() or 1), 2),
              'before_models': before, 'after_run': working_memory(),
              'max_serialized_packet_bytes': max_packet, 'camera_released': camera.released,
              'limits': 'Not an end-to-end LYA, battery, thermal, prolonged-runtime or owner-room performance measurement.'}
    Path(__file__).with_name('resource-check.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
