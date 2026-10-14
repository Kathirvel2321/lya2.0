# LYA local vision models

These files stay local and are excluded from Git. They are loaded only for an explicit camera scan/live view or visual question. No camera opens during normal launch.

| File | Upstream | SHA-256 | Role |
|---|---|---|---|
| `nanodet-int8.onnx` | [OpenCV Zoo NanoDet INT8](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_nanodet) | `8dd32b85f2d273e9047f1d6b59e0b2fd008b1076338107bb547ac28942cdf90b` | COCO object labels |
| `yunet-2026may.onnx` | [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | `ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0` | Face presence only |

The downloaded sizes on this workspace are 1,031,424 and 229,738 bytes. The adapter checks both hashes before opening a camera. OpenCV Zoo documents Apache-2.0 for NanoDet and MIT for YuNet; review each upstream directory license before redistribution. These models do not identify a person. SFace/enrolled templates are a separate, deferred feature.

To restore a missing model, download its upstream Git LFS media payload, verify the SHA-256 above, and place it under this directory with the exact filename. A 132-byte Git LFS pointer is not a usable model.

## Optional local hands (2026-10-05)

The hand adapters use full-precision OpenCV Zoo models pinned to revision
`47534e27c9851bb1128ccc0102f1145e27f23f98`, under Apache-2.0. Missing/changed hand
weights disable hand references while preserving existing object analysis.
There is no automatic runtime download. Landmarks describe image positions,
not identity. The source/license is in `vision/vendor/opencv_hands`.

| File | Bytes | SHA-256 |
|---|---:|---|
| `palm_detection_mediapipe_2023feb.onnx` | 3,905,734 | `78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c` |
| `handpose_estimation_mediapipe_2023feb.onnx` | 4,099,621 | `db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c` |

See [camera implementation/checks](../../archive/history/reviews/2026-10-05-camera-objects/README.md)
and its pinned-source manifest for restore URLs and limitations.
