"""Local public-fixture/blank-frame check; never opens a camera or network."""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
from vision.scan import VisionEngine
from vision.hands import pointing_rays


def main():
    folder = Path(__file__).resolve().parent
    frame = cv2.imread(str(folder / 'public-hand-fixture.png'))
    assert frame is not None
    engine = VisionEngine()
    start = time.perf_counter()
    scene = engine.analyze(frame)
    fixture_ms = (time.perf_counter() - start) * 1000
    assert scene['hand_status'] == 'ready' and 1 <= len(scene['hands']) <= 2
    assert all(len(hand['points']) == 21 for hand in scene['hands'])
    assert not pointing_rays(scene['hands']), 'Public open palm must not be a pointing finger'
    elapsed = []
    blank = np.zeros((720, 1280, 3), dtype=np.uint8)
    for _ in range(8):
        start = time.perf_counter()
        result = engine.analyze(blank)
        elapsed.append((time.perf_counter() - start) * 1000)
        assert result['hand_status'] == 'ready'
        assert not result['hands'] and not result['objects'] and not result['faces']
    summary = {
        'public_fixture_hands': len(scene['hands']), 'landmarks_per_hand': 21,
        'public_open_palm_rejected_as_pointing': True,
        'public_combined_analysis_ms': round(fixture_ms, 1),
        'blank_combined_analysis_median_ms': round(statistics.median(elapsed), 1),
        'blank_combined_analysis_max_ms': round(max(elapsed), 1),
        'blank_runs': len(elapsed), 'private_camera_used': False,
        'limitations': 'Public open-hand and blank-frame checks, not owner pointing accuracy or a sustained resource benchmark.',
    }
    (folder / 'local-model-check.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
