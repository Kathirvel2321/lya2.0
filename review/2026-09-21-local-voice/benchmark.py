"""Synthetic, speaker-free local speech benchmark; never reads user text or records audio."""
import json, sys, time, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from audio.synthesis import Renderer
out=Path(__file__).resolve().parent
results=[]
for name,text in [('english','Hello, I am Lya. Your task is complete. Everything is ready for you.'),('tamil','வணக்கம். நான் லியா. உங்கள் வேலை முடிந்தது. உங்களுக்கு எப்படி உதவலாம்?')]:
    start=time.perf_counter(); cpu=time.process_time(); r=Renderer(); pieces=[]; first=None
    for samples,rate in r.audio(text):
        if first is None: first=time.perf_counter()-start
        pieces.append(samples)
    samples=np.concatenate(pieces)
    elapsed=time.perf_counter()-start
    assert np.isfinite(samples).all() and len(samples)>rate
    with wave.open(str(out/(name+'.wav')),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
        wav.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
    result=dict(cpu_seconds=round(time.process_time()-cpu,3), language=name,first_audio_seconds=round(first,3),synthesis_seconds=round(elapsed,3),audio_seconds=round(len(samples)/rate,3),rtf=round(elapsed/(len(samples)/rate),3))
    results.append(result);print(result,flush=True)
(out/'benchmark.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

# Process peak working set includes both sequential tests and Python imports.
import ctypes
from ctypes import wintypes
class Counters(ctypes.Structure):
    _fields_ = [('cb',wintypes.DWORD),('faults',wintypes.DWORD)] + [(name,ctypes.c_size_t) for name in ('peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
info=Counters(); info.cb=ctypes.sizeof(info)
ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(info),info.cb):
    (out/'memory.json').write_text(json.dumps({'benchmark_process_peak_working_set_mb':round(info.peak/1024**2,1)}),encoding='utf-8')
    print('Benchmark process peak MB:',round(info.peak/1024**2,1))
