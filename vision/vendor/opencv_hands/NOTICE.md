# OpenCV Zoo hand adapters

Source: OpenCV Zoo, revision `47534e27c9851bb1128ccc0102f1145e27f23f98`.
All files in the upstream palm/hand model directories are Apache-2.0; the
upstream license is preserved in `LICENSE`.

- `mp_palmdet.py`: derived from `models/palm_detection_mediapipe/mp_palmdet.py`.
  LYA replaces the literal 2016-anchor table with equivalent generated centers,
  checked against the complete upstream table. Its NMS input uses width/height
  boxes as required by OpenCV, retaining original corner coordinates for results.
- `mp_handpose.py`: from `models/handpose_estimation_mediapipe/mp_handpose.py`,
  with an attribution header only.

LYA uses the full-precision ONNX models: upstream warns of significant accuracy
loss in the ordinary INT8 hand model. The model hashes, sizes and revision are
in `archive/history/reviews/2026-10-05-camera-objects/hand-models.json`. No upstream demo code that
opens a camera or downloads files is invoked by these adapters.

Sources:
https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/palm_detection_mediapipe
https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/handpose_estimation_mediapipe
