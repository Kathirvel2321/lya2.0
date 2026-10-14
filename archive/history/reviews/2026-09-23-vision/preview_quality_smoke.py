"""Explicit hardware benchmark: no frames saved or scene content printed."""
import time
from vision.scan import live_frames
started = time.perf_counter()
cpu = time.process_time()
arrivals = []
size = None
for frame in live_frames(max_seconds=5, max_frames=50):
    arrivals.append(time.perf_counter())
    size = (frame['width'], frame['height'])
elapsed = time.perf_counter() - started
print({'resolution': size, 'frames': len(arrivals), 'first_frame_s': round(arrivals[0]-started, 2),
       'preview_fps': round((len(arrivals)-1)/(arrivals[-1]-arrivals[0]), 2),
       'cpu_seconds': round(time.process_time()-cpu, 2), 'total_seconds': round(elapsed, 2)})
