"""Bounded local hand landmarks and cautious image-plane object selection."""
import hashlib
import math
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1] / 'models/vision'
HASHES = {
    'palm_detection_mediapipe_2023feb.onnx': '78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c',
    'handpose_estimation_mediapipe_2023feb.onnx': 'db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c',
}


class HandTracker:
    def __init__(self):
        for name, digest in HASHES.items():
            path = MODEL_DIR / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise RuntimeError('Local hand model missing or changed.')
        from vision.vendor.opencv_hands.mp_palmdet import MPPalmDet
        from vision.vendor.opencv_hands.mp_handpose import MPHandPose
        self.palms = MPPalmDet(str(MODEL_DIR / 'palm_detection_mediapipe_2023feb.onnx'), scoreThreshold=.7, topK=8)
        self.pose = MPHandPose(str(MODEL_DIR / 'handpose_estimation_mediapipe_2023feb.onnx'), confThreshold=.8)

    def analyze(self, frame):
        import numpy as np
        hands = []
        palms = self.palms.infer(frame)
        for palm in sorted(palms, key=lambda item: float(item[-1]), reverse=True)[:2]:
            result = self.pose.infer(frame, palm)
            if result is None:
                continue
            points = result[4:67].reshape(21, 3)[:, :2]
            if not np.isfinite(points).all() or not math.isfinite(float(result[-1])):
                continue
            hands.append({'points': points.tolist(), 'confidence': round(float(result[-1]), 2)})
        return hands


def pointing_rays(hands):
    """Accept an extended index and at least two curled fingers, not an open palm."""
    rays = []
    for hand in hands:
        if hand.get('confidence', 0) < .8:
            continue
        points = hand.get('points', [])
        if len(points) != 21 or any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in points):
            continue
        def distance(a, b):
            return math.dist(points[a], points[b])
        scale = distance(0, 9)
        if scale < 12:
            continue
        ax, ay = points[6][0] - points[5][0], points[6][1] - points[5][1]
        bx, by = points[8][0] - points[6][0], points[8][1] - points[6][1]
        norm_a, norm_b = math.hypot(ax, ay), math.hypot(bx, by)
        curled = sum(distance(tip, 0) < distance(pip, 0) * 1.12 for pip, tip in ((10, 12), (14, 16), (18, 20)))
        if (norm_a < scale * .15 or norm_b < scale * .35 or
                (ax * bx + ay * by) / (norm_a * norm_b) < .85 or curled < 2):
            continue
        rays.append((points[8], (bx / norm_b, by / norm_b)))
    return rays


def ray_box_distance(origin, direction, box, margin=0):
    enter, leave = 0.0, float('inf')
    for axis in (0, 1):
        low, high = box[axis] - margin, box[axis + 2] + margin
        if abs(direction[axis]) < 1e-8:
            if not low <= origin[axis] <= high:
                return None
            continue
        a, b = (low - origin[axis]) / direction[axis], (high - origin[axis]) / direction[axis]
        enter, leave = max(enter, min(a, b)), min(leave, max(a, b))
        if enter > leave:
            return None
    return enter if leave >= 0 else None


def referenced_object(scene, kind):
    """Return only an unambiguous detected candidate; never infer physical distance."""
    # ponytail: 2D ray/box selection; calibrated depth is needed for 3D pointing.
    objects = [item for item in scene.get('objects', [])
               if item['label'] != 'person' and item.get('confidence', 0) >= .55]
    hands = scene.get('hands', [])
    width, height = scene['width'], scene['height']
    diagonal = math.hypot(width, height)
    rays = pointing_rays(hands)
    if kind == 'pointing' or (kind == 'this' and rays):
        if scene.get('hand_status') == 'unavailable':
            return None, 'Pointing analysis is unavailable. Hold one object in the center of the camera view instead.'
        if not rays:
            return None, 'I cannot see a clear pointing finger. Keep your index finger extended and your hand and object visible.'
        candidates = []
        for item in objects:
            box = item['box']
            # A backdrop containing the entire pointing hand is not a clear target.
            if any(all(box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
                       for p in hand['points']) for hand in hands if len(hand.get('points', [])) == 21):
                continue
            hits = [ray_box_distance(origin, direction, box, diagonal * .015) for origin, direction in rays]
            if any(hit is not None and hit <= diagonal * .8 for hit in hits):
                candidates.append(item)
        if len(candidates) == 1:
            return candidates[0], ''
        if candidates:
            return None, 'Several objects line up with your finger. Move your finger closer to one object or hold that object in the center.'
        return None, 'I see your pointing gesture, but cannot confidently identify an object along it. Move the object closer or try a clearer angle.'
    if kind == 'holding':
        if not hands:
            return None, 'I cannot see your hand clearly. Show your hand and one object together, or bring the object to the center.'
        candidates = []
        for item in objects:
            x1, y1, x2, y2 = item['box']
            if any(any(x1 - diagonal * .025 <= p[0] <= x2 + diagonal * .025 and
                       y1 - diagonal * .025 <= p[1] <= y2 + diagonal * .025
                       for p in hand.get('points', [])) for hand in hands):
                candidates.append(item)
    else:
        candidates = [item for item in objects if
                      abs((item['box'][0] + item['box'][2]) / 2 / width - .5) < .25 and
                      abs((item['box'][1] + item['box'][3]) / 2 / height - .5) < .25]
    if len(candidates) == 1:
        return candidates[0], ''
    if candidates:
        return None, 'I see several possible objects. Hold one in the center or point clearly at the one you mean.'
    return None, 'I cannot confidently identify that object. Hold it in the center with good light; some small objects are not supported by my current detector.'
