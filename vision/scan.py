"""Local camera perception. No identity, recording, or network path."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODEL_DIR = ROOT / 'models' / 'vision'
NANODET = MODEL_DIR / 'nanodet-int8.onnx'
YUNET = MODEL_DIR / 'yunet-2026may.onnx'
HASHES = {
    NANODET: '8dd32b85f2d273e9047f1d6b59e0b2fd008b1076338107bb547ac28942cdf90b',
    YUNET: 'ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0',
}
CLASSES = ('person bicycle car motorcycle airplane bus train truck boat traffic_light fire_hydrant stop_sign '
           'parking_meter bench bird cat dog horse sheep cow elephant bear zebra giraffe backpack umbrella '
           'handbag tie suitcase frisbee skis snowboard sports_ball kite baseball_bat baseball_glove '
           'skateboard surfboard tennis_racket bottle wine_glass cup fork knife spoon bowl banana apple '
           'sandwich orange broccoli carrot hot_dog pizza donut cake chair couch potted_plant bed '
           'dining_table toilet tv laptop mouse remote keyboard cell_phone microwave oven toaster sink '
           'refrigerator book clock vase scissors teddy_bear hair_drier toothbrush').split()


def models_ready():
    return all(path.is_file() and path.stat().st_size > 100_000 for path in HASHES)


def verify_models():
    for path, expected in HASHES.items():
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Vision model missing or changed: {path.name}')


def detect_objects(frame, net):
    import cv2
    import numpy as np
    height, width = frame.shape[:2]
    scale = min(416 / width, 416 / height)
    new_width, new_height = round(width * scale), round(height * scale)
    left, top = (416 - new_width) // 2, (416 - new_height) // 2
    canvas = np.zeros((416, 416, 3), dtype=np.uint8)
    canvas[top:top + new_height, left:left + new_width] = cv2.resize(
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (new_width, new_height))
    image = (canvas.astype(np.float32) - (103.53, 116.28, 123.675)) / (57.375, 57.12, 58.395)
    net.setInput(cv2.dnn.blobFromImage(image.astype(np.float32)))
    outputs = net.forward(net.getUnconnectedOutLayersNames())
    # OpenCV 5 returns all class heads before the three box heads.
    candidates, boxes = [], []
    for stride, cls, box in zip((8, 16, 32), outputs[:3], outputs[3:]):
        cls, box = cls[0], box[0]
        for index in np.flatnonzero(cls.max(axis=1) >= 0.45):
            label = int(cls[index].argmax())
            confidence = float(cls[index, label])
            y, x = divmod(int(index), 416 // stride)
            center_x, center_y = (x + 0.5) * stride, (y + 0.5) * stride
            logits = box[index].reshape(4, 8)
            weights = np.exp(logits - logits.max(axis=1, keepdims=True))
            distance = (weights / weights.sum(axis=1, keepdims=True) * np.arange(8)).sum(axis=1) * stride
            x1 = max(0, (center_x - distance[0] - left) / scale)
            y1 = max(0, (center_y - distance[1] - top) / scale)
            x2 = min(width, (center_x + distance[2] - left) / scale)
            y2 = min(height, (center_y + distance[3] - top) / scale)
            if x2 <= x1 or y2 <= y1:
                continue
            boxes.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
            candidates.append((label, confidence))
    if not boxes:
        return []
    keep = cv2.dnn.NMSBoxes(boxes, [item[1] for item in candidates], 0.45, 0.6)
    return [{'label': CLASSES[candidates[i][0]].replace('_', ' '),
             'confidence': round(candidates[i][1], 2),
             'box': [boxes[i][0], boxes[i][1], boxes[i][0] + boxes[i][2], boxes[i][1] + boxes[i][3]]}
            for i in keep[:12]]


class VisionEngine:
    """Load tiny local networks once for a bounded live camera session."""

    def __init__(self, width=640, height=480):
        import cv2
        cv2.setNumThreads(2)
        verify_models()
        self.face = cv2.FaceDetectorYN.create(str(YUNET), '', (width, height))
        self.objects = cv2.dnn.readNet(str(NANODET))
        from vision.hands import HandTracker
        try:
            self.hands = HandTracker()
        except (RuntimeError, cv2.error):
            self.hands = None  # Optional hand analysis must not break the existing camera.

    def analyze(self, frame):
        import cv2
        original_height, original_width = frame.shape[:2]
        hand_frame = frame
        if original_width > 960:
            hand_frame = cv2.resize(frame, (960, round(original_height * 960 / original_width)), interpolation=cv2.INTER_AREA)
        if original_width > 640:
            frame = cv2.resize(frame, (640, round(original_height * 640 / original_width)), interpolation=cv2.INTER_AREA)
        height, width = frame.shape[:2]
        self.face.setInputSize((width, height))
        faces = self.face.detect(frame)[1]
        face_boxes = [] if faces is None else [list(map(int, (f[0], f[1], f[0] + f[2], f[1] + f[3])))
                                                for f in faces[:12]]
        objects = detect_objects(frame, self.objects)
        hands, hand_status = [], 'unavailable'
        if self.hands is not None:
            try:
                hands, hand_status = self.hands.analyze(hand_frame), 'ready'
            except (cv2.error, ValueError, OverflowError):
                hand_status = 'unavailable'
        sx, sy = original_width / width, original_height / height
        def original_box(box):
            return [round(box[0]*sx), round(box[1]*sy), round(box[2]*sx), round(box[3]*sy)]
        for item in objects:
            item['box'] = original_box(item['box'])
        for hand in hands:
            hand['points'] = [[round(x * original_width / hand_frame.shape[1], 1),
                               round(y * original_height / hand_frame.shape[0], 1)] for x, y in hand['points']]
        return {'faces': [original_box(box) for box in face_boxes], 'objects': objects,
                'hands': hands, 'hand_status': hand_status, 'identity': 'unknown'}


def encode_frame(frame):
    import cv2
    height, width = frame.shape[:2]
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError('Camera frame could not be rendered')
    return {'image': base64.b64encode(encoded).decode('ascii'), 'width': width, 'height': height}


def scan_frame(frame):
    return {**encode_frame(frame), **VisionEngine(*frame.shape[1::-1]).analyze(frame)}


def live_frames(camera_factory=None, max_seconds=90, max_frames=None):
    """Preview at <=15 fps; analyze a small copy at <=2 fps with no backlog."""
    import cv2
    verify_models()
    backend = cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY
    camera = (camera_factory or cv2.VideoCapture)(0, backend)
    pool = None
    try:
        if not camera.isOpened():
            raise RuntimeError('Camera unavailable')
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        camera.set(cv2.CAP_PROP_FPS, 15)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        engine = VisionEngine()
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='lya-vision')
        pending = None
        start = time.monotonic()
        next_frame = start
        next_inference = start
        analysis = {'faces': [], 'objects': [], 'identity': 'unknown', 'ready': False, 'analyzed_at': 0.0}
        count = 0
        while time.monotonic() - start < max_seconds:
            if time.monotonic() < next_frame:
                time.sleep(min(0.02, next_frame - time.monotonic()))
                continue
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError('Camera stopped delivering frames')
            now = time.monotonic()
            if pending is not None and pending.done():
                analysis = {**pending.result(), 'ready': True, 'analyzed_at': submitted_at}
                pending = None
            if pending is None and now >= next_inference:
                submitted_at = now
                pending = pool.submit(engine.analyze, frame.copy())
                next_inference = now + 0.5
            yield {**encode_frame(frame), **analysis}
            count += 1
            if max_frames is not None and count >= max_frames:
                break
            next_frame = max(next_frame + 1 / 15, time.monotonic())
    finally:
        if pool is not None:
            pool.shutdown(wait=True)
        camera.release()


def capture_once(camera_factory=None):
    import cv2
    verify_models()  # Fail before activating a camera if weights are unavailable.
    backend = cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY
    camera = (camera_factory or cv2.VideoCapture)(0, backend)
    try:
        if not camera.isOpened():
            raise RuntimeError('Camera unavailable')
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        frame = None
        for _ in range(3):
            ok, latest = camera.read()
            if ok:
                frame = latest
        if frame is None:
            raise RuntimeError('No camera frame received')
        return scan_frame(frame)
    finally:
        camera.release()


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--camera-once']:
            print(json.dumps(capture_once()))
        elif sys.argv[1:] == ['--camera-live']:
            for result in live_frames():
                print(json.dumps(result), flush=True)
        else:
            raise RuntimeError('Explicit camera action required')
    except Exception as exc:
        print(json.dumps({'error': str(exc)}))
        raise SystemExit(1)


