# LYA face-scan presentation — 2026-10-09

Implemented the owner's supplied visual reference within the existing native
face-enrollment stage. The wide layout uses a matte LYA frame, cyan hairlines,
muted amber scan arcs, camera corners, an enrollment rail, actual face markers,
sample counters and voice guidance. It fits the available monitor and switches
to a smaller camera layout on narrow windows. Only cancellation is offered
during automatic capture; ordinary registration controls return afterward.

The existing compact registration geometry is restored for voice enrollment,
review or failure. Other accepted interface, ordinary hearing, speech models,
startup, keys, phone authority and encrypted storage behavior are preserved.

## Real observations, decorative artwork

- Existing YuNet face box and five landmarks come from the same frame as the
  mirrored local preview. Normalized, bounded metadata is validated at the
  worker/UI boundary. Zero/multiple faces carry no box or landmarks.
- Camera state, observed face count, five available landmarks and captured
  views are real state. The three-view count is enrollment progress, not a
  security confidence percentage.
- The rotating arcs and ticks are artwork. There is no dense face mesh, depth
  sensor, certified liveness detection or spoof-resistance claim.
- Phone proof remains the owner authenticator. Face and voice profiles do not
  unlock owner access. Cancel, hide, expiry and failure retain the existing
  worker shutdown and discard behavior. Late previews are ignored after close.
- Frames/landmarks remain in RAM during actual enrollment; the existing worker
  sends a 320×240 preview at most twice per second. No new model or dependency
  was added, and no owner sensor was opened during development.

## Files and validation

Production: `desktop/owner_scan.py`, scoped integration in
`desktop/owner_setup.py`, preview tracking in `security/owner_capture.py` and
strict decoding in `desktop/owner_biometrics.py`. Regression cases/fixture
updates are in `test_owner_profiles.py`.

`check_scan.py` uses fake encryption keys, temporary owner stores, synthetic
signed phone proofs and the existing public OpenCV test image. It does not
enroll a real owner, open a camera/microphone, use a provider, restart LYA or
touch real keys/stores. See `validation.json` for final suite and short
widget-only resource results. All six changed Python files passed syntax and
whitespace checks; the usual launcher interpreter imported the dialog.

Native previews: `face-scan-wide.png`, `face-scan-narrow.png`,
`face-scan-minimum.png`, `face-guidance.png`, `voice-restored.png`. The image is
a public test fixture, not an owner capture. Actual model detector output was
passed through the validated UI bridge for these previews. Native screenshots
were visually inspected; no browser workaround was used.

The opaque scan surface avoids repainting its entire translucent parent on
each animation frame. Artwork is capped at ten updates/second and its timer
stops when hidden. A short earlier wide-widget sample fell from 20.458% to
5.334% of one CPU core after this adjustment. The final capture/control layout
sample measured 9.441%; short runs vary. These are synthetic widget-only
measurements, not sustained whole-app, live camera or battery qualification.
The preview keeps its existing small resolution and two-frame-per-second
limit; enlarging it does not add camera detail or a higher frame rate.

## Owner walkthrough (when ready)

1. Fully Quit LYA from the tray and reopen the usual launcher to load the edit.
2. Say “register admin” and complete the existing phone/passkey proof.
3. If profiles are missing, separately consent to local face/voice enrollment.
4. Ordinary online hearing stops. Follow the spoken front/side/opposite-side
   guidance. The large scan view opens only here; Escape or × cancels.
5. The camera closes, the compact display returns, and LYA guides three local
   voice samples. Review and say “save my profiles” only if ready to save.

Returning owners with saved profiles continue to sign in without repeated
enrollment. Real phone/owner speech/camera acceptance remains deferred; this
task did not start enrollment. Existing lost-phone recovery and webcam/voice
spoofing limitations remain unchanged.
