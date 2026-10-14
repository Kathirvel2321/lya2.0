# Camera object references — 2026-10-05

Owner requested camera access, visible-object identification and hand pointing.
Existing LYA already had a bounded local camera preview, NanoDet common-object
labels and named-object questions. It lacked bare-object references and hand
direction selection. This task changes camera perception/routing only; the
accepted hearing/voice, UI appearance, key storage and startup are unchanged.

## Implementation

- `vision/answers.py`: narrow visual-reference phrases; an active camera is
  required for bare “what is this?” so ordinary document questions do not open it.
- `vision/hands.py`: optional verified local palm/21-point hand models, at most
  two pose jobs per analysis; clear extended-index gesture, forward 2D ray and
  detected-object intersection. Person/backdrop targets are excluded. Multiple
  matches ask for clarification. A centered single object is used without a
  clear point. A holding answer means a detected object near visible landmarks,
  not proof of physical contact. No identity or 3D distance inference.
- `vision/scan.py`: same single analysis worker and <=2 analyses/sec, same local
  <=15-fps preview/session bounds. Object/face input remains <=640px wide;
  hand input is bounded at 960px to retain useful crop detail. Hand failures
  preserve base object analysis. All coordinates return to original image space.
- `desktop/experience.py`: existing live-camera context supplied to common typed
  and spoken command routing; replies use the existing LYA panel and voice.
- `desktop/camera_eyes.py`: failed/oversized streams now answer pending questions
  instead of leaving them hanging. Existing fresh-analysis and close clearing
  behavior retained. No private image/audio collection, model API call, saved
  recording, owner credential access or running-session restart in agent checks.

## Models and source

Added 8,005,355 bytes of optional ignored ONNX weights, no dependency/framework.
Source pinned to OpenCV Zoo `47534e27c9851bb1128ccc0102f1145e27f23f98`.
Hashes/sizes in [hand-models.json](hand-models.json). Full precision chosen
because upstream warns ordinary INT8 hand weights can lose accuracy.

- [Official palm model/source](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/palm_detection_mediapipe)
- [Official 21-point hand model/source](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/handpose_estimation_mediapipe)

Reviewed Apache-2.0 adapter files/license retained in `vision/vendor/opencv_hands`.
Palm anchors generated in upstream order and compared with the full literal
table (allclose 1e-7); NMS receives OpenCV width/height boxes. Upstream hand
adapter otherwise retained. Git LFS model payloads can be restored from
`https://media.githubusercontent.com/media/opencv/opencv_zoo/REVISION/models/UPSTREAM/FILE`
using the manifest fields, then verifying size/hash. No runtime auto-download.

Agent Reach Jina Reader and official web sources used; Agent Reach CLI/doctor
was unavailable. No install or source instructions executed.

## Checks and actual limits

- `python -m unittest test_camera_dialog test_vision test_pointing`: **24 passed**,
  synthetic camera/landmarks, blank actual models; no physical camera/network.
- `python tools/check_local_voice_ui.py`: **62 passed**, offscreen UI, fake secrets,
  temporary stores, microphone/playback/model clients disabled. Covers spoken
  pointing route and active-camera bare references reaching the camera rather
  than the language-model dispatcher.
- `python review/2026-10-05-camera-objects/check_models.py`: combined actual
  networks found one hand/21 image points in an upstream public demo frame and
  rejected its open palm as a point. Eight 1280x720 blank frames returned no
  faces, objects or hands. Evidence: [local-model-check.json](local-model-check.json),
  [public-hand-check.json](public-hand-check.json), public-hand-fixture.png.
  First combined run missed the hand at 640px; bounded 960px hand input repaired
  that check without lowering confidence. Initial tiny gesture-chart fixture
  found no palms and was rejected as an unsuitable full-frame smoke fixture.
- Recorded combined public-frame analysis 178.1ms; blank median 155.9ms/max
  188.6ms in a short local run. These are not sustained CPU/memory/battery results
  or owner pointing accuracy. OpenCV 5 prints CPU target-selection warnings;
  inference succeeds. No GPU requirement added.
- Windowed `pythonw vision/scan.py` through QProcess returned the expected
  explicit-action-required error on stdout; no camera opened. Actual owner
  camera/hand/object acceptance and newly restarted production session remain
  pending. Synthetic geometry alone does not establish accurate live pointing.

Local NanoDet is a limited common-category detector: bottle/cup/phone may work;
pens and arbitrary objects are unsupported. Lighting, occlusion, a small hand,
overlapping boxes and multiple aligned objects can require clarification.
This is image-plane direction selection, not general scene reasoning, depth,
gaze tracking or guaranteed object recognition. Frames/landmarks are transient
local process/UI data; stopping/closing clears the current view.

## Owner live check

1. Close the old LYA session and reopen workspace `LYA.lnk` (owner-managed key).
2. Say `open camera`; confirm the current preview. Hold one bottle/cup in its
   center and ask `what is this?`.
3. Keep hand and object in view, extend index toward the object with other
   fingers curled, and ask `what am I pointing at?`. A clear side-on finger
   works better than pointing directly at the lens. Try a second object to
   check that the answer changes rather than naming the first detection.
4. Say `close camera`; verify preview closes and camera releases.

Owner said ready now; instructions supplied. Await exact behavior/answer report
before marking integrated live accuracy accepted. Enrollment/weather deferred.

## Follow-up: natural camera request reached the wrong route

Owner screenshot establishes a live routing failure: an expanded camera-open
request went to the general brain action route and returned not-connected.
This is not evidence that the lens or detector failed. Reproduced with failing
isolated checks before the fix. Earlier 86 passing checks covered exact commands
and references, not this natural camera-control phrasing.

`vision/answers.py` now shares a direct camera-control classifier across typed
and spoken callers in `desktop/experience.py`. Supports articles, polite forms,
turn-on/off, trailing punctuation/purpose and local see-me presence questions.
Negated commands, how/why/status mentions and settings/photo requests do not
activate the camera. Open-and-see-me routes to the existing fresh-view question
path and normal answer panel, not to the general model. It reports detected
person presence or inability to confirm; it does not identify the owner.

New checks in `test_pointing.py` and `desktop/check_experience.py` cover the
reported expanded phrasing, direct open/close, no general-model dispatch,
unchanged authentication, local presence answer and rejection cases.
No hearing/model/UI/startup change, private sensor activation, cloud request,
key access or running-session restart. Owner must reopen LYA and retry the
natural camera command. Current isolated results are recorded in the project
ledger; live object and pointing accuracy remain pending.
