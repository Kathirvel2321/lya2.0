# LYA local vision models

These files stay local and are excluded from Git. They are loaded only for an explicit one-shot scan. No camera opens during normal launch.

| File | Upstream | SHA-256 | Role |
|---|---|---|---|
| `nanodet-int8.onnx` | [OpenCV Zoo NanoDet INT8](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_nanodet) | `8dd32b85f2d273e9047f1d6b59e0b2fd008b1076338107bb547ac28942cdf90b` | COCO object labels |
| `yunet-2026may.onnx` | [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | `ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0` | Face presence only |

The downloaded sizes on this workspace are 1,031,424 and 229,738 bytes. The adapter checks both hashes before opening a camera. OpenCV Zoo documents Apache-2.0 for NanoDet and MIT for YuNet; review each upstream directory license before redistribution. These models do not identify a person. SFace/enrolled templates are a separate, deferred feature.

To restore a missing model, download its upstream Git LFS media payload, verify the SHA-256 above, and place it under this directory with the exact filename. A 132-byte Git LFS pointer is not a usable model.
