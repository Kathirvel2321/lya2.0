# Voice retry and volume routing repair — 2026-10-04

Implemented and isolated-tested. Owner speech accuracy, real speaker-volume
outcome and the live conversational acceptance gate remain unverified.

The reported repeated full-question apology had a concrete source: every
`RecognitionUncertain` turn immediately triggered another spoken apology, with
no limit. The confidence guard also prevented uncertain words from reaching the
brain. Separately, the native brain did not connect volume commands even though
the legacy device handler and trusted-volume policy already existed.

Changes:

- `audio/voice.py`: one clarification after an uncertain turn; a second uncertain
  turn returns to local name/clap wake detection. Successful transcription or a
  fresh wake resets the count. Stopping during a slow rejected decode discards
  the late retry. Confidence checks stay in place.
- `desktop/app.py`, `desktop/experience.py`: pass the transient uncertain
  candidate to the answer card. It is not dispatched, written to logs or added
  to chat history. Suggest `volume up`/`volume down` for a possible recognized
  volume request. Distinguish the pause notification and keep quiet-mode retries
  silent. Existing output voice is preserved.
- `brain/capabilities.py`, `brain/workflow.py`: whole-request matching for clear
  relative volume instructions, including polite natural phrasing. Reuse the
  local handler only after the existing verified, active identity and trusted
  role checks. No phone approval is added for this existing trusted action.
  Quoted mentions, negation, ambiguous directions and compound commands do not
  match the actuator route. Guest/color-only sessions remain locked.
- `skills/device.py`: unavailable native control now reports failure rather than
  claiming a volume change.
- Checks in `test_voice.py`, `test_brain_workflow.py`, `test_skills.py` and
  `desktop/check_experience.py`; usage updated in `desktop/README.md`.

Validation:

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_voice test_brain_workflow test_skills.DeviceSkillsTests.test_volume_actions test_skills.DeviceSkillsTests.test_volume_unavailable_fails_without_claiming_a_change
.\.venv-ui\Scripts\python.exe tools/check_local_voice_ui.py
```

The first suite passed 85 checks with one intentional online skip. The offscreen
desktop suite passed all 55 checks. Two updated brain checks were rerun and
passed; these are already counted in the first suite. The desktop test initially
asserted before its fake speaker completed the spoken caption; it now explicitly
completes that simulated playback before checking the final text. These checks
use synthetic identities, disposable encryption, temporary storage and mocked
microphone/speaker/model/volume calls. `git diff --check` passed.

Limits and next step:

- This repairs retry behavior and command routing. It does not improve the
  acoustic model, establish a defective headset, or judge the owner's English.
- Volume up/down send one multimedia-key step. Muting uses the legacy hardware
  toggle; no current volume/mute state is read back. Absolute percentages and
  microphone gain are outside this change.
- No real audio was captured, uploaded or replayed; no actual volume was
  adjusted, cloud plan enabled, model/device setting changed, private key read,
  identity enrolled, desktop restarted or Windows Voice Access closed.
- Source changes require a LYA restart. A live check must distinguish recognized
  words, retry/pause behavior, verified-session permission and actual device
  effect. Faithful full-question recognition remains the next acceptance stage.
  The earlier external-transcription choice remains unanswered. Enrollment and
  weather stay deferred.
