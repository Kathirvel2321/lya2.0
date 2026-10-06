# Camera focus and scene tour research — 2026-10-06

Current follow-up: camera highlights, checked-frame scene tour and verified-owner
access are implemented and isolated-tested. See [implementation and measured
resources](implementation.md). Live owner verification/recognition remains pending.
The research record below describes the earlier proposal; concept.png is an
illustration, while the implementation report links actual widgets using fake fixtures.

## Recommendation

Build a grounded camera highlight and scene tour using the existing OpenCV,
local object/hand models and Qt painter. First make the marked object and the
spoken answer agree, then validate broader recognition separately. A stylish
box helps the owner see the assistant's selected evidence; it cannot improve
the detector's recognition accuracy by itself.

| Owner request | Proposed visible behavior | Proposed answer |
| --- | --- | --- |
| “Find my bottle” / “Look at the cup” | A bright corner frame and label mark the selected detected object. Two matching bottles receive separate numbered candidates rather than silently selecting one. | Name the selected item and its image-relative position. |
| “What is this?” / “What am I pointing at?” | Use the existing centered-object/hand-ray selection. Show the chosen box before speaking; ambiguous targets receive numbered candidates. | Identify the chosen candidate, or ask “left bottle or right bottle?” |
| “What all can you see?” / “Scan everything in front of me” | Build one ordered inventory from the current checked view. Number distinct instances and highlight them one by one as they are described. | “One: a phone on the left. Two: a bottle in the middle. Three: a cup on the right.” These are example detections, not claims about the owner's room. |
| “Stop” / a new question / close camera | Cancel the tour before stopping playback; discard its pending highlights and replies. | No later queued item continues speaking. |

Inventory means supported objects detected within the lens's field of view,
not every physical object in the room. A fixed laptop camera cannot pan itself.
“Look around” can mean analyzing the current view; a wider view requires the
owner to move the camera or objects.

## Established by current source inspection

- `vision/scan.py` produces original-image bounding boxes, labels, scores and
  hand landmarks. It keeps at most **12 detections**; the detector's configured
  vocabulary contains **80 categories**. Pen/pencil are absent. Current scene
  summaries in `vision/answers.py` include only the first **five** labels.
- `vision/hands.py:referenced_object` already returns the selected object and
  its box. `answer_scene` converts that to text, while
  `VisionDialog.answer_ready` exposes only `(request_id, text)`. The UI does not
  receive a structured selected target or an ordered scene inventory.
- `desktop/camera_eyes.py:VisionCanvas.paintEvent` draws the video pixmap only.
  It does not paint object boxes. The existing aspect-fit rectangle should be
  reused for overlays so resize, letterboxing and image coordinates agree.
- Preview is bounded at 15fps, inference at 2 analyses/second, one worker and
  no inference backlog. A packet combines the current video with the most
  recently completed analysis. Those boxes may belong to an earlier frame:
  painting them directly over moving live objects would misrepresent alignment.
- Question answers reject analysis older than two seconds. That freshness guard
  is useful but is not per-frame geometric alignment or object tracking.
- “What do you see?” is routed locally. The owner's new “what all can you see?”
  wording needs the same shared visual-question route; no general LLM guess.
- `SetupSpeech` already exposes captions, completion and unavailable events.
  Completion also fires during cancellation/errors: a tour must check its own
  generation, cancellation and error state before advancing. Ordinary speech
  behavior does not need replacement.

Read-only installed-runtime checks: OpenCV **5.0.0**; native Qt rectangle/SVG
painting available; sparse optical flow available; `TrackerCSRT_create` and
`TrackerKCF_create` absent. Therefore a plan assuming those tracker constructors
would fail in this environment. No sensor was opened to obtain these facts.

## Research findings and choices

| Option | Evidence | Decision for the first implementation |
| --- | --- | --- |
| Keep local NanoDet + existing hand landmarks | OpenCV publishes the current small detector and an Apache-2.0 license. Its COCO evaluation reports weaker small-object results than large-object results. These benchmarks are not the owner's recognition rate. [OpenCV model documentation](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_nanodet) | Reuse for common supported objects and direct pointing. Do not promise arbitrary-object recognition. |
| Native Qt overlay | QPainter supports lines, paths, text and rounded rectangles; image scaling/transforms are already used by LYA. [Qt for Python documentation](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html) | Draw camera-only frames and labels with existing dependencies. No browser, game engine or new UI framework. |
| Hand landmarks | Google's task returns 21 hand landmarks; video tracking reduces repeated palm detection. Landmarks locate the hand, not the intended external object. [Google hand landmark guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) | Keep the existing OpenCV hand adapter. Preserve clarification for several objects along a pointing ray. Image-plane pointing does not establish 3D intention. |
| Add a standard tracker | OpenCV tracking requires a valid selected region and an initialization/update lifecycle. [OpenCV tracking tutorial](https://docs.opencv.org/4.x/d2/d0a/tutorial_introduction_to_tracker.html) | First align marks with the checked frame. Benchmark selected-region optical flow only if continuous live tracking is needed; CSRT/KCF are absent locally. Do not introduce a multi-object tracking framework just for this UI. |
| Replace with YOLOX | OpenCV supplies an Apache-2.0 ONNX detector and COCO-category evaluation. A category detector remains a limited vocabulary. [OpenCV YOLOX documentation](https://github.com/opencv/opencv_zoo/blob/main/models/object_detection_yolox/README.md) | No automatic replacement: its benefit for the owner's small objects/CPU budget is unmeasured, and it does not make unsupported categories universally recognizable. |
| Broader text-grounded recognition | Grounding DINO takes image plus text and returns phrase-associated boxes; Microsoft Florence-2 supports object detection, region captions and phrase grounding. [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO), [Microsoft Florence-2 model card](https://huggingface.co/microsoft/Florence-2-base) | Candidates for a separate on-demand pilot if common-category coverage is insufficient. They add a different inference stack; laptop latency/memory and model accuracy need qualification before adoption. A descriptive caption without verified boxes is insufficient for pointing. |

Florence-2-base is documented as 0.23B parameters and large as 0.77B. This
does not imply either is a lightweight real-time fit for this laptop. Their
Microsoft model card documents bounding-box output; actual LYA integration and
performance have not been tested.

The NVIDIA Florence build-page probe was inconclusive. The NVIDIA NIM object
detection documentation found in search describes **document page elements and
table structure**, not a general room-object detector. Do not substitute it
because its name says object detection. [NVIDIA API reference](https://docs.nvidia.com/nim/ingestion/object-detection/latest/api-reference.html)
No free, available hosted Florence endpoint or shared-key compatibility was
verified. An existing speech key does not establish a camera-model service.

Agent Reach's documented Jina Reader backend fetched the official OpenCV and
Google pages; web research checked official Qt/OpenCV/Microsoft/IDEA/NVIDIA
sources. `agent-reach`, `mcporter` and `gh` were unavailable on PATH, matching
the earlier project research evidence. CLI doctor/update checks could not run;
no tool installation, login, cookie access or account action was attempted.

## Proposed camera design

- Thin cyan corner brackets, a subtle outline and a small numbered label;
  restrained gold/cyan accents match the current crystal design.
- Other detected candidates are muted. The selected target gets a readable
  `02 · Bottle` tab. Labels, numbering and line styles communicate state as
  well as color. An uncertain candidate says `CHECK TARGET`; a lost one clears
  instead of leaving an apparently confirmed box behind.
- Use one brief focus transition when motion is allowed. Reduced-motion mode
  uses an immediate frame change. Avoid permanent sweeping/glowing animation
  and keep labels within the visible camera area.
- During identification and the first scene-tour release, show an explicitly
  labeled **checked frame**, paired with the analysis that generated its boxes.
  Keep the live camera session available and resume its existing preview after
  the tour. This prevents stale coordinates from being presented as current
  motion tracking. Live tracking is a separate, measurable follow-up if needed.
- The tour uses one checked view, not a separate recognition/model request per
  object. Distinct same-category objects receive different numbers. Order is
  left to right, then top to bottom, and the answer states that it covers the
  confidently detected items. If the 12-item cap is reached, disclose the
  bounded inventory rather than saying the entire scene was exhaustively seen.
- Speak one short item description at a time through the existing warm voice.
  Highlight it before playback and advance only after successful completion.
  In quiet mode show the numbered inventory without speaking. New requests,
  stop, camera close/expiry, worker failure and stale results cancel the tour.

See [concept.png](concept.png) / [editable vector concept](concept.svg).
The illustrated objects/labels are synthetic, not model output. The illustration
shows the selected item's emphasis; it is not an implemented screenshot.

## Ordered implementation plan and acceptance gates

1. Return a minimal structured visual result containing the existing answer,
   selected detection and ordered detected items. Reuse the same selection for
   text and marking; do not build a second selector inside the UI. Extend only
   the requested target/scene-tour phrases through the shared routing function.
2. Pair analyzed pixels with their result and paint native overlays in
   `desktop/camera_eyes.py`. Validate coordinate mapping at differing window
   sizes/aspect ratios. Show a checked-view indication rather than claiming
   stale detections track every live frame.
3. Add the bounded scene-tour queue in `desktop/experience.py`, using the
   existing speech events. Clear its generation/state **before** calling stop,
   because speech completion can be synchronous on cancellation. Keep ordinary
   non-camera answers, hearing and output voice unchanged.
4. Use synthetic frames/boxes/landmarks and fake playback to verify exact
   highlighted/spoken target agreement; duplicate objects, ambiguous pointing,
   unsupported pen, inventory cap, resized/letterboxed images, stale packets,
   stop/new-question/close/error and quiet/reduced-motion behavior. Verify no
   extra inference backlog or unintended sensor/network activation.
5. Then run an owner-ready live check with a bottle, cup and phone: correct
   target highlight before reply; distinct identical objects; scene-tour count
   and order; stop halfway; close clears the view. Only this gate can establish
   live owner recognition and usefulness. Runtime/memory during a sustained
   camera session remain unmeasured; preserve existing bounds first.
6. If supported-category recognition fails, qualify a separate broader model
   on public fixtures and measured laptop resources before proposing adoption.
   Cloud image testing requires its own explicit authorization; earlier online
   speech permission does not authorize camera-image uploads. Frames remain
   transient and local for the recommended first release.

At research completion, implementation had not started. No owner sensor/audio/image,
credentials, protected store or remote model request was accessed. No claim of
perfect pointing, universal recognition, continuous tracking or scene-tour
integration was claimed by that research step. The implemented follow-up is linked above;
enrollment/weather remain deferred.
