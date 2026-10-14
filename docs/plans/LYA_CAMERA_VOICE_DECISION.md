# LYA camera and voice stack decision

**Decision date:** 2026-09-21  
**Scope:** local recognition foundations only; no enrollment or sensor capture

## Selected stack

| Job | Selected component | Why it fits LYA |
|---|---|---|
| Face detection | OpenCV YuNet ONNX | Tiny CPU model, five landmarks, OpenCV API already installed |
| Face embedding | OpenCV SFace ONNX | Local CPU inference, compact model, permissive license, existing OpenCV API |
| Voice activity | sherpa-onnx with Silero VAD | Offline, ONNX Runtime, supports Windows and low thread counts |
| Speaker identity | sherpa-onnx speaker embeddings | Offline verification/identification without the full PyTorch stack |
| Speech to text | whisper.cpp | Already selected for T08; quantized local models and CPU support |
| Speech output | Existing pyttsx3 initially | Already installed and adequate until a measured TTS upgrade is needed |
| Protected actions | Windows Hello PIN | Real trusted checkpoint on this laptop; biometrics stay advisory |

YuNet and SFace are the camera choice. The installed OpenCV 5.0 runtime exposes
`FaceDetectorYN` and `FaceRecognizerSF`, so LYA needs model weights and a bounded
adapter rather than another face framework. OpenCV documents a roughly 337 KB
YuNet detector and 36.9 MB SFace recognizer. Its published CPU benchmarks show
both are practical even on Raspberry Pi class hardware.

sherpa-onnx is the voice platform choice because one offline runtime can provide
VAD, speaker embeddings, keyword spotting and optional speech functions on Windows.
The first speaker model is not approved until WeSpeaker ResNet34 and 3D-Speaker
CAM++ ONNX candidates are license-checked and benchmarked with English and Tamil
synthetic/owner-approved samples. Model thresholds must come from local evaluation,
not copied from a demo.

## Repositories reviewed

### `k2-fsa/OmniVoice`

High-quality multilingual voice-cloning TTS. It generates LYA's voice; it does not
identify the person speaking. Its documented setup uses PyTorch 2.8 and GPU-oriented
paths. It is too heavy for this 8 GB CPU laptop and cloning the owner's voice would
increase impersonation risk. **Do not install for registration.** Reconsider later
only as an optional TTS service on suitable hardware with explicit voice consent.

### `debpalash/VoiceStudio`

A full local voice-cloning, dubbing and transcription application. It is useful as
a separate creator tool, but it duplicates LYA's UI/runtime, carries AGPL-3.0 terms,
and does not solve speaker authentication. **Do not embed in LYA.**

### `alibaba/open-code-review`

An Apache-2.0 AI code-review CLI. It can later review diffs, but it has no camera or
voice role and can send repository content to a configured model endpoint. **Keep
outside the biometric runtime.**

### `David-Crty/databasement`

A self-hosted database backup web service. It is unrelated to recognition and would
add a server, credentials and network attack surface. LYA already has a narrower
encrypted selected-note recovery design. **Do not install for this task.**

## Security boundary

Face and voice may answer “who is probably here?” for greetings and profile choice.
They cannot unlock secrets, create administrators, approve purchases, change policy
or bypass Windows verification. An uncertain, missing or conflicting match is a
guest. Protected actions require Windows Hello PIN or the later trusted-device path.

- Camera and microphone are opened only after a visible user action.
- Capture is bounded and cancellable; device handles close on cancel, error and exit.
- Raw frames/audio are discarded after feature extraction and never sent to cloud.
- Encrypted normalized templates store model id, version and consent revision.
- Unknown people are not automatically enrolled or photographed for later review.
- Active head-turn and fresh spoken-code challenges reduce simple replay attacks,
  but are not equivalent to certified anti-spoofing.
- Template removal and profile deletion must work before real enrollment begins.

## Build order

1. Pin exact YuNet/SFace and speaker model artifacts, licenses, SHA-256 hashes and
   source URLs. Store ignored weights under `models/biometric/`.
2. Add CPU-only adapters behind the existing injected registration contract. Test
   with generated vectors and public/non-personal media only.
3. Build a visible capture controller with hard duration/frame limits, cancellation,
   single-face enforcement, microphone level guidance and guaranteed device release.
4. Benchmark latency, memory and idle CPU. Camera inference should sample slowly or
   run only on demand; no continuous full-frame inference is allowed.
5. Calibrate false accept/reject behavior with an owner-approved test session across
   light, pose, noise, English and Tamil. Do not copy example thresholds blindly.
6. Connect encrypted templates and guest fallback. Run deletion, mismatch, replay,
   multi-face, unplug and process-crash tests.
7. Only then ask the owner for explicit real face/voice enrollment consent.

## Current readiness

Read-only inspection found Python 3.12, OpenCV 5.0, NumPy and sounddevice available.
OpenCV exposes both selected face APIs. `sherpa_onnx`, InsightFace and Resemblyzer
are absent. Model weights have not been downloaded. No camera, microphone or private
template was accessed during this decision.

## Primary sources

- https://github.com/opencv/opencv_zoo
- https://docs.opencv.org/4.5.5/d0/dd4/tutorial_dnn_face.html
- https://github.com/k2-fsa/sherpa-onnx
- https://k2-fsa.github.io/sherpa/onnx/speaker-identification/index.html
- https://github.com/ggml-org/whisper.cpp
- https://github.com/k2-fsa/OmniVoice
- https://github.com/debpalash/VoiceStudio
- https://github.com/alibaba/open-code-review
- https://github.com/David-Crty/databasement

