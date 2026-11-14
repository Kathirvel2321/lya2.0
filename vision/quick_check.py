"""Fast pre-check before full face recognition.

The ideology: a first-glance pipeline. Cheap checks answer "is a face even
visible and usable?" in ~50ms. Only when one passes does the expensive
ArcFace embedding run (~200-400ms on CPU). If no usable face is present,
the caller drops straight to normal LLM conversation - no scanning, no
lockout noise, no artificial waiting.

Checks, cheapest first:
  1. brightness   - a covered/blacked-out camera yields near-zero mean
                    luminance; rejects tape/lid/shirt-over-lens instantly.
  2. blur         - variance of Laplacian: motion smear and defocus yield
                    embeddings that are junk; refuse before wasting ArcFace.
  3. face present - YuNet detection (already shipped in models/vision),
                    also returns 5 landmarks. A frontal-enough pose is
                    derivable from eye positions without another model.

Returns a verdict dict; `usable` is the single gate the recognizer obeys.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

YUNET = ROOT / "models" / "vision" / "yunet-2026may.onnx"

MIN_BRIGHTNESS = 40.0      # 0-255 mean luma; tape over the lens is ~5
MIN_SHARPNESS = 60.0       # Laplacian variance; motion blur sits under ~50
MIN_FACE_PIXELS = 3600     # ~60x60 - smaller faces embed unreliably
MAX_YAW_RATIO = 0.55       # |eye dx| / eye distance; 0.5 = 3/4 profile

_detector = None


def _yunet():
    global _detector
    if _detector is None:
        import cv2
        detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320),
                                             score_threshold=0.6)
        _detector = detector
    return _detector


def frame_stats(frame):
    """Brightness and sharpness of one BGR frame. Pure numpy, no model."""
    import cv2
    import numpy as np
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return {
        "brightness": float(gray.mean()),
        "sharpness": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
    }


def _pose_from_landmarks(landmarks):
    """Frontal-enough? Eye landmark order in YuNet: 0=right eye, 1=left eye."""
    (rx, ry), (lx, ly) = landmarks[0], landmarks[1]
    dx, dy = abs(lx - rx), abs(ly - ry)
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1:
        return 1.0
    return abs(dx) / dist


def analyze(frame):
    """One-stop verdict for a BGR frame. Never raises for image content;
    `usable=False` always carries a machine-readable reason."""
    import cv2
    import numpy as np
    stats = frame_stats(frame)
    if stats["brightness"] < MIN_BRIGHTNESS:
        return {"usable": False, "reason": "camera_covered_or_dark", **stats}
    if stats["sharpness"] < MIN_SHARPNESS:
        return {"usable": False, "reason": "too_blurry", **stats}

    h, w = frame.shape[:2]
    detector = _yunet()
    detector.setInputSize((w, h))
    _, faces = detector.detect(frame)
    if faces is None or not len(faces):
        return {"usable": False, "reason": "no_face_visible", **stats}
    best = max(faces, key=lambda f: f[2] * f[3])
    x, y, fw, fh = best[:4]
    if fw * fh < MIN_FACE_PIXELS:
        return {"usable": False, "reason": "face_too_small", **stats}
    yaw = _pose_from_landmarks(best[4:10].reshape(5, 2))
    if yaw > MAX_YAW_RATIO:
        return {"usable": False, "reason": "face_turned_away", **stats}
    return {"usable": True, "reason": "ok", "face_box": [int(x), int(y), int(fw), int(fh)],
            "yaw_ratio": round(float(yaw), 3), **stats}
