"""Read-only biometric runtime check. It never opens a camera or microphone."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "biometric"
MODELS = {
    "yunet": MODEL_DIR / "face_detection_yunet.onnx",
    "sface": MODEL_DIR / "face_recognition_sface.onnx",
    "speaker": MODEL_DIR / "speaker_embedding.onnx",
}


def probe():
    modules = {
        name: importlib.util.find_spec(name) is not None
        for name in ("cv2", "numpy", "sounddevice", "sherpa_onnx")
    }
    result = {
        "python": sys.version.split()[0],
        "modules": modules,
        "models": {name: path.is_file() for name, path in MODELS.items()},
        "opens_sensors": False,
    }
    if modules["cv2"]:
        import cv2
        result["opencv"] = cv2.__version__
        result["face_apis"] = {
            "FaceDetectorYN": hasattr(cv2, "FaceDetectorYN"),
            "FaceRecognizerSF": hasattr(cv2, "FaceRecognizerSF"),
        }
    result["ready"] = (
        modules["cv2"] and modules["numpy"] and modules["sounddevice"]
        and modules["sherpa_onnx"] and all(result["models"].values())
        and all(result.get("face_apis", {}).values())
    )
    return result


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))

