import time
from vision.scan import live_frames
start = time.perf_counter()
for index, frame in enumerate(live_frames(max_seconds=8, max_frames=15), 1):
    print(index, round(time.perf_counter() - start, 2), flush=True)
