# LYA crystal desktop milestone

Camera references (2026-10-05): local common-object analysis now accepts
`what object is this?`, `what am I holding?`, and `what am I pointing at?`.
Bare `what is this?` / `what's this?` uses an already-active camera only.
Reopen LYA to load changes, say `open camera`, hold a bottle/cup in the center,
then ask the bare question. For pointing, keep the extended index finger and
target visible in the same image. Multiple/unclear targets request clarification.
Say `close camera` or close the preview to release it; sessions remain bounded.
Camera analysis stays local with no saved image/video or cloud image call.
The detector supports common categories, not every object (pens unsupported).
Pointing selects along a 2D image direction, not physical distance or a 3D target.
Implemented and isolated/public-fixture tested; owner live accuracy pending.
Voice/hearing, interface appearance, credential and startup behavior were preserved.
See [camera review](../review/2026-10-05-camera-objects/README.md).

Camera routing follow-up (2026-10-05): natural direct commands such as
`please open the camera` and `open the camera and see me` now reach the local
camera handler instead of the general brain action route. `Can you see me?`
uses current person/face-presence detections, without claiming identity.
`Please close the camera` uses the same local close control. Negations,
how/why mentions and camera-settings requests do not activate it.
Reopen LYA to load this follow-up. Live owner retry remains pending.

Optional saved NVIDIA key (2026-10-05): open Windows **Credential Manager >
Windows Credentials > Add a generic credential**. Use `LYA/NVIDIA_API_KEY` as
the Internet/network address, `LYA` as the user name, and paste the NVIDIA API
key in the password field. LYA now reads this entry when no session environment
key is supplied; a missing/unreadable entry retains the existing key prompt.
Manage or remove the saved key in Credential Manager. Do not put it in project
files or the project brain. No owner credential was read/saved during development.
The owner's new preserve-working-features rule is in `AGENTS.md`; no further
voice, hearing, wake, interface or startup change is authorized by this update.
See [key storage and owner rule](../review/2026-10-05-key-storage/README.md).

Normal launch now uses a native masked NVIDIA key dialog (2026-10-05). Open
`LYA.lnk` in the project folder for a direct windowed launch; `launch-lya.cmd`
and `launch-lya.ps1` also use `pythonw` with `--gui`. A `.cmd` shell may briefly
flash before exiting; the shortcut does not need that shell. The existing owned
sign-in shortcut has been migrated to the same native prompt. Keys remain
session-only. Cancel exits before the desktop/listener starts. The console
launcher command below is retained for manual diagnostics.
See [native launch review](../review/2026-10-05-native-launch/README.md).

Current conversation and design status (2026-10-05): the normal launcher now uses
NVIDIA Parakeet questions with a bounded NVIDIA-hosted Whisper backup and hidden
session-only key entry. The owner reports a successful integrated conversation;
Whisper has qualified accuracy acceptance. Offline owner hearing remains failed.
Online questions follow the owner's ongoing online-mode choice. Private mode
blocks online hearing and asks for text; enable it before confidential speech.

During the existing 45-second conversation window, saying Lya inside a question
preserves the complete sentence. A standalone address while awake no longer
replays the greeting. A turn that starts awake remains a conversation turn even
if capture/decoding exceeds that idle window. Explicit stop/sleep still ends it.

The native panel now has faceted graphite surfaces, visible reply titles,
paragraph and speaker styling, and readable placement beside the crystal when
space above is limited. Listening uses diamond microdots, thinking uses crossing
paths, and speaking uses a wave. State labels follow actual voice events. The
existing crystal artwork, speaking voice and reduced-motion controls are retained.
Restart LYA through `launch-lya.cmd` to load these changes. The new routing and
design have isolated validation and synthetic previews; live owner acceptance
is still pending. See [conversation/design review](../review/2026-10-05-conversation-design/README.md).
The older dated milestones below describe their status at that time.

Current voice implementation (2026-10-04): microphone wake is enabled at launch;
command audio stays local unless `--cloud-voice` is explicitly passed. An installed
Whisper English model can be selected experimentally; the owner recording did
not pass its accuracy check, so it is not the default. Vosk still handles wake
and spoken interruption. This is implementation status, not owner
acceptance of recognition, noise handling or latency. Older milestones below are
historical.

Uncertain speech now gets one clarification, then returns to waiting for Lya
after a second uncertain turn. The answer card shows the uncertain candidate
without dispatching it or adding it to chat history; quiet mode keeps retries
silent. A possible volume request receives a short-command suggestion.
Recognized requests such as `lower the volume`, `volume up` and
`can you make my volume low in this device` now use the local volume handler
after the existing verified-session gate. Guest/color-only sessions cannot
change volume. The handler sends one relative volume key step; mute uses the
existing hardware toggle. It does not set an absolute percentage or read back
the actual device level. No hearing accuracy or real volume outcome has been
accepted from these isolated checks. Restart LYA to load source changes.
See [retry/volume repair](../review/2026-10-04-volume-retry/README.md).

The orb/tray menu has **Microphone** and **Command recognition (local)** choices.
Selections last for this process only. Switching microphones waits for the old
reader to close; selecting an unavailable input fails instead of using another
microphone. Questions permit 2.5-second internal quiet gaps and up to 120 seconds;
reaching the limit rejects the unfinished question.

Free local model setup, from the project root:

```powershell
.\.venv-ui\Scripts\python.exe -m pip install -r audio\requirements-local-asr.txt
.\.venv-ui\Scripts\python.exe tools\setup_local_asr.py --engine whisper
.\.venv-ui\Scripts\python.exe desktop\app.py --command-asr whisper --skip-setup
```

The setup downloads public model files and verifies publisher LFS checksums.
Recognition requires all model/tokenizer files and never downloads them at runtime.
`--skip-setup` bypasses the first-run setup screen; it grants no authentication.
Use `--no-voice` to start without microphone collection, `--microphone "Exact input name"`
to select an input for this session, or `--command-asr vosk` for the legacy command
recognizer. `--system-dictation --skip-setup` prepares the chat composer with
LYA's microphone off. Enable Windows **Voice Access**, choose **English–India**
and its input microphone, dictate into the composer, then say **press Enter**.
This is an independent dictation fallback, not an embedded Voice Access API;
its owner recognition and spoken-key-command accuracy remain untested. Windows
Voice Access needs a one-time language download and works offline afterward.
[Microsoft setup](https://support.microsoft.com/en-us/accessibility/windows/voice-access/set-up-voice-access).
Local speech input does not alter the configured text-brain route or
authorize private actions. See the latest dated project-brain voice entry for the
actual acceptance status before enabling a candidate recognizer.

Latest (2026-09-17): fixed circle clipping; ordinary answer-only cards; explicit
chat open/close/full-screen/restore; independent project-file windows; one baked
360-degree greeting rotation and persistent-crystal command. See
[controls and limits](qa/2026-09-17-window-controls/README.md).
Chat history is rendered once; each new question appears immediately and only
the newest LYA reply receives the typewriter animation.
After a compact answer finishes, simply start typing: the answer card changes to
the one-line input and preserves the first typed character. Enter also opens it.
Descriptions below preserve earlier milestones.

## Current launch experience (2026-09-17)

Run `launch-lya.cmd`: the owner's baked crystal appears at the bottom center with a guest
greeting, then gently crossfades into a glowing circle over 1.1 seconds. Click it for a one-line glass input.
Answers open in a small card; type `open chat` for the expanded conversation view,
or `show files` for approved project documents. Escape/stop closes the result.
The transcript is temporary display history and clears when the panel closes.
Cards grow above the circle with a 450 ms transition. Ordinary answers have no
branding header or title and reveal short answers gently, while longer replies finish within about 1.2 seconds. Reduced motion
shows the whole answer immediately. Idle rendering and completed text timers stop.

The new launch defaults to the requested baked model artwork; `--original-art`
selects the earlier image. `--reduced-motion` skips movement and text reveal.
`--show-panel` remains accepted for launcher compatibility; launch now starts with
the greeting rather than a large chat panel. No recognition or voice is activated.
See [interaction and performance evidence](qa/2026-09-16-compact/README.md).
Older milestone descriptions below describe the base panel before this change.

The user's custom black-chrome crystal is now a small native Windows widget, with
an attached translucent result panel. This is the first implementation of the new
desktop presentation layer. It does not import the legacy runtime.

## Start it

Double-click `launch-lya.cmd`, or run this from the project root in PowerShell.
It opens the panel and works without changing PowerShell's execution policy:

```powershell
.\launch-lya.cmd
```

The existing PowerShell launcher is also available if scripts are permitted:

```powershell
.\launch-lya.ps1
```

Or run directly to see any startup errors:

```powershell
.\.venv-ui\Scripts\python.exe desktop\app.py
```

Optional: `--show-panel` opens the card at launch; `--reduced-motion` disables the
crystal's gentle movement and color-transition animations. The PowerShell launcher
accepts `-ShowPanel` and `-ReduceMotion` and uses `pythonw.exe` to avoid a console.

The `.cmd` launcher always opens the panel; use `--reduced-motion` with it to
disable animations. It starts the installed Python executable directly, never
changes execution policy, and does not enable microphone/camera collection.

The isolated environment is already installed on this workspace with Python
3.12.14 and PySide6 Essentials 6.11.2. To create a new environment on another
machine with Python 3.12 installed:

```powershell
py -3.12 -m venv .venv-ui
.\.venv-ui\Scripts\python.exe -m pip install -r desktop\requirements.txt
```

## Use it

- Click the crystal or press Enter/Space while it has focus to open the panel.
- Drag the crystal. The result panel follows and stays inside the current monitor's
  available work area, avoiding the taskbar. It opens to the left or right when
  possible and shifts upward in tight spaces.
- Type `show files`, or click Project files. These are actual saved LYA project
  documents, not a connected private vault. Double-click a row or press Enter to
  read it. Nothing is executed, edited or uploaded.
- `time` shows the local time. `help` lists the implemented commands.
- Right-click the crystal or use the tray menu to preview colors and change motion
  or opacity. Cosmetic person choices do not identify anyone or grant permissions.
- Escape/`stop` closes the card and rejects stale read results. Ctrl+M toggles
  reduced motion. Ctrl+Q quits. The tray menu can also wake, sleep, recenter or quit.

Person palettes: guest ice, admin amber, family violet, friend jade. Task accents
take priority: listening cyan, thinking violet, files blue, success green,
approval amber, error rose. `task idle` returns to the selected person palette.
The crystal keeps its original cyan/amber fissures with a restrained color wash
and changing aura, rather than replacing the user's artwork with a generic circle.

## Design and implementation

- Two compact native Qt windows; no browser, web server, full-screen overlay or
  background desktop screenshot sampling.
- Original artwork copied unchanged to `assets/crystal-original.png`. A native
  painter clip follows its silhouette; the original gray background is not shown.
  This is a 2D artwork animation, not a reconstructed rotatable 3D model.
- Cached tinted pixmaps, 420ms color interpolation and a low-amplitude timed drift.
  Decorative drift runs at 30Hz for at most three seconds per interaction; Qt
  drives color transitions separately. Idle, hidden and reduced-motion orbs stop
  the drift timer; hidden/reduced-motion color changes are immediate.
- Card opens with a 260ms movement from the crystal's direction and a 210ms fade.
  Only geometry/opacity animate; document contents do not reflow during the reveal.
- Dark translucent glass, opaque text, subtle shadow, inner highlight and outline
  provide contrast against light or dark wallpapers. An opaque option is available.
  This is a tinted glass treatment, not OS-level acrylic/background blur.
- Document reading runs in a single worker. A generation id prevents completion
  callbacks from reopening a dismissed result. Reads are allowlisted to four
  project documents and limited to 64,000 characters; links never open externally.

Qt references used: [translucent QWidget windows](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html)
and [property animations](https://doc.qt.io/qt-6/qpropertyanimation.html).

## Check it

```powershell
.\.venv-ui\Scripts\python.exe -B desktop\check_ui.py
```

The checks exercise alpha/native-window setup, monitor bounds (including negative
coordinates), keyboard use, cosmetic-role isolation, read allowlisting, stale-result
cancellation and animation lifecycle. They render actual widgets over synthetic
light and dark backgrounds in `qa/` and save a short timing sample in
`qa/measurement.json`. Screenshots are UI test fixtures, not captures of the user's
desktop. Short paint timings are not guarantees of frame rate, battery use or
long-duration stability under model/camera workloads.

## Brain workflow milestone (2026-09-13)

Type `brain demo` for a labelled synthetic demonstration, `brain status` for
readiness, `brain help` for memory commands, or `who am i` for session identity.
Requests run on a background worker; closing the panel suppresses late results.
See [the brain guide](../LYA_BRAIN_WORKFLOW.md) for lifetimes, graph and council.

The desktop starts as a guest. `register admin` / `sign in` opens a local
Windows verification flow that can create or reopen a device-only admin
profile in the encrypted runtime store. This machine's Application Control
policy currently blocks the locally built verifier, so no live admin has been
registered here. Phone approval is still not connected; personal memory and
other owner-tier operations remain locked even after device-only sign-in.
General model responses require a selected, reachable local model; none was
reachable during this check. Cosmetic role selection never grants access.

Voice has an optional bridge with readiness/error indicators. The desktop requires
a local Vosk model before recording, with no transcription cloud fallback. That
model is missing in the checked environment; live wake/recognition is unverified.
The separate legacy voice module also contains online speech services, which are
not evidence that offline voice works. No sensor or online speech test was run
in the isolated brain acceptance pack.

## Artwork attempt provenance

The original is the owner's `ChatGPT Image Sep 12, 2026, 06_46_46 PM.png`. A built-in
ImageGen background-extraction attempt produced a baked checkerboard rather than
alpha, so that generated output is not used by the app. No replacement raster or
CLI image API was installed. The original source is displayed through the native
silhouette clip instead.

Prompt used: “Use case: background-extraction. Edit target: the attached user's
custom LYA crystal. Create a production desktop sprite by removing ONLY the flat
gray background. Preserve the original single floating jagged black chrome crystal,
exact tall diamond silhouette, facets, glass reflections, and cyan and amber
illuminated fissures. Do not redesign it, do not add rings or text. Genuine
transparent alpha background (not a checkerboard painted into image), clean finely
antialiased edges, no backdrop, no cast shadow beyond the crystal, no floor. Center
the full uncut crystal with a little transparent padding. Return PNG with
transparency. This image will be a small floating native desktop assistant.”


## Owner's 3D crystal (2026-09-15)

The earlier orb remains the default: short measurements showed higher process CPU
with the new artwork. To try it, right-click the orb and select **Use 3D model
artwork (baked, experimental)**, or launch:

```powershell
.\launch-lya.cmd --model-art
```

Close the existing LYA instance before restarting. Uncheck the menu item to return
to the earlier artwork. Menu selection lasts for this session. For the earlier
artwork with decorative motion disabled:

```powershell
.\launch-lya.cmd --original-art --reduced-motion
```

The supplied model is preserved unchanged at `assets/obsidian-crystal.glb`.
`bake_crystal.py` rendered its actual geometry once into `assets/obsidian-baked.png`
(288 x 408 with alpha). This is a static view with approximate materials, not live
3D rotation or physically accurate glass refraction. Runtime uses the existing
cached QPainter color transitions and never parses the GLB or loads the baking
renderer. Role colors remain cosmetic; they do not authenticate anyone.

Missing, invalid or oversized baked images fall back to the original. While the
model artwork is selected, an average paint duration above 8ms over the last 30
paint calls switches to the original and enables reduced motion. This measures
paint work, not battery consumption or all sources of lag. Idle redraw checks
passed, but zero battery impact and physical display FPS are not established.

See [measurements and synthetic previews](qa/2026-09-15-orb/README.md).

## Memory recovery interface (2026-09-20)

Restart the compact LYA desktop, then type `open recovery` or `backup notes`.
`restore notes` opens its Restore tab. These commands open a native window; they
do not send recovery keys to the model, enroll anyone or unlock a guest session.

With a trusted verified owner session and approval adapter connected:

1. Load available notes and tick the notes to include.
2. Generate a separate recovery key. Reveal it only when needed, store it in a
   separate password manager/offline location, then re-enter it and acknowledge custody.
3. Choose a new `.lya-notes` file and confirm the destination. Existing files are
   never replaced; only encrypted content is written. No key file is created.
4. To restore, choose the archive, enter its key and click **Check archive**.
   Review the unexpired/expired counts and destination status, then explicitly
   confirm restore. The destination owner profile must have no existing notes.

Enrollment/session binding is still deferred, so the real desktop currently
shows the locked screen. Do not set a fake admin session to unlock it. The full
file-to-fresh-key restore journey passes with synthetic profiles in
`test_recovery_ui.py`; run `check-storage-recovery.cmd` from the project root.

File/encryption work runs on a worker thread. Cancel is cooperative; a commit
already completed cannot be undone by cancellation. Closing requests cancellation
and clears displayed secrets. Keys/labels/previews are also cleared on detected
session change/expiry. Nothing syncs to cloud. See
`review/2026-09-20-recovery-interface/README.md` for limits and synthetic screenshots.

## Conversational registration guide (2026-09-21)

Restart LYA, then type `register admin` or `admin setup`. The ordinary command
panel closes. An intact centered crystal accompanies one prompt at a time.
The short intro stops afterward; reduced-motion mode skips it.

Windows' installed SAPI voice speaks fixed prompts locally. Use Voice on/off to
mute and Replay to repeat a prompt. Changing stages or closing setup stops speech.
This is spoken guidance, not microphone listening or wake-word activation.

On Device, use PIN settings, Check device, and Verify with Windows. Hello Face
hardware is not required to try PIN. The Windows prompt handles the PIN; never
type it into LYA's name field.

Face/voice preferences remain drafts and are discarded on close. No real
enrollment or owner session is created. See the synthetic previews, checks, and
playback limitations in `review/2026-09-21-conversational-registration/README.md`.
Earlier registration previews are retained as historical evidence.

## Local female speech (updated 2026-09-23)

Spoken replies use `external-work/alya_voice` with separate native English and
Tamil Piper voices. English no longer goes through the Tamil acoustic model;
the speaker changes when the language changes. Commands: `voice on`, `voice off`, `stop speaking`,
`voice natural`, `voice economy`, `voice language auto|en|ta`, and styles
`everyday`, `joyful`, `storyteller`, `hacker`, `hype`, `whisper`, or `night`.

The worker stays warm for 45 seconds during conversation, then exits. Completed
answers start rendering immediately and finish their text reveal in roughly
1.2 seconds, independently of speech startup. The voice can follow after the
answer appears; phrase-timed captions remain available in the speech transport
but do not hold the desktop answer back. Remote speech and desktop speech audit
logging are off. Microphone
listening, naturalness acceptance, barge-in and production battery validation
remain pending. See `review/2026-09-23-english-voice/README.md`.



## Local camera eyes (2026-09-23)

Type `open vision`, `look around`, or `scan room` to open the camera-off lens window. Click **Scan once** for one local object-and-face-presence scan. The camera closes after the scan; closing the window or an eight-second timeout stops the worker. Frames stay in memory and are cleared on close. This does not identify a person, create an owner session, save a visitor photo or authorize any action. One owner-authorized live scan completed in about 2 seconds; visual accuracy and battery performance remain unreviewed. See `review/2026-09-23-vision/README.md`.


## Live local camera (2026-09-23)

Type `open camera`, `look around`, or `scan room` to start a bounded live view. `open vision` opens the same window with camera off. Use Stop live view or close the window to end capture. The worker also ends after 90 seconds. Preview targets up to six frames/s and local object/face analysis at most two/s; actual startup depends on the webcam. Ask about a person or one of the detector's supported objects. LYA gives approximate on-screen position, never identity or permission. Small items such as pens are not in this model and will be reported as unsupported. No camera frame is saved or sent online. See `review/2026-09-23-vision/README.md` for measured checks and remaining limits.

Visual questions typed in LYA's main command line, such as `can you see my pen?`, route to the Vision window and wait for a current analyzed frame. The lightweight model currently cannot detect pens and will say so. Microphone transcription is still pending.

## Optional NVIDIA hearing (2026-10-05)

Current update: owner selected online-only hearing after fresh local comparison
failed. `launch-lya.cmd` and the existing project sign-in shortcut now use the
NVIDIA session launcher with hidden key entry. Default Parakeet TDT has one Whisper
backup on selected model/service errors; CTC 1.1B is a selectable spare. Private
mode blocks speech recognition and requests text instead of a local guess. Full
backup accuracy and integrated reply acceptance are pending. See
`review/2026-10-05-hearing-plan/online-backups.md`; the earlier optional status below
is historical.

An ordinary speech-to-text check with hosted Parakeet passed by owner confirmation.
The optional desktop connection uses `--cloud-voice --cloud-asr nvidia`; selecting
the recognizer alone does not enable remote audio. The session launcher is:

```powershell
.\.venv-asr\Scripts\python.exe tools/start_nvidia_lya.py --allow-nvidia-questions
```

It asks for the API key locally without saving it. Close existing LYA first. Wake
and stop remain local; complete questions go to NVIDIA while private mode is off.
Enable private mode through text **before** confidential speech. Local private
recognition remains unaccepted. Current speaking voice and security gates remain
unchanged. Ongoing cloud use needs explicit permission; the first permission only
covered a diagnostic question. See `review/2026-10-05-hearing-plan/nvidia-connection.md`
for validation and the untested integrated reply/noise/interruption gates.

## Camera-only preview (2026-09-24)

The Vision window now contains the live picture and a small Start/Stop strip. Type visual questions into LYA's normal input, including `what do you see?`; answers appear in her normal panel and use her configured speech when enabled. `open camera` starts the preview, while `open vision` opens it with the camera off. `close camera` stops and clears the preview. The camera worker still ends automatically after 90 seconds.

LYA requests 1280×720 capture and up to 15 preview frames/s, while recognition runs on a smaller copy at most twice per second. A real laptop camera and Qt check each measured about 15 preview frames/s after startup. Camera resolution and speed depend on the device and lighting. No image is saved or uploaded. Pen recognition, identity matching, anti-spoofing, and battery-life validation remain open; Windows Hello PIN remains the authority for protected actions. Measurements and a synthetic window preview are in `review/2026-09-23-vision/README.md`.

## LYA initialization and admin registration (2026-09-25)

Launch LYA with `launch-lya.cmd`, then type `register admin`. When no admin
exists, that command opens the six-act owner walkthrough. It greets you as
**boss**, explains each step aloud when local speech is available, shows a live
camera preview only after `Start camera`, and opens the microphone only after
`Record sample`. Both sensors stop when you leave their act. Voice clips are
reduced to measurements in memory; no face or voice template is stored.

The camera step checks face presence, and the microphone step checks recording
quality. Neither verifies identity. Admin creation requires a fresh Windows
checkpoint for the same display name plus the explicit profile checkbox; the
result is a **device-only** admin in the encrypted local store. Existing admins
still use the prior sign-in screen. `activate-lya.cmd` opens the walkthrough on
its own; use `register admin` inside LYA for an immediate desktop session.

Connection labels mean a component was found, not that its live hardware or
Windows proof passed. Follow-up testing outside the restricted tool session
confirmed LYA's camera worker can receive frames, its microphone worker can
capture audio, and the local speech worker completes. The locally built Hello
helper remains blocked by Windows Application Control, so admin creation cannot
complete yet. Do not disable Application Control to force the helper through.
See the dated report and synthetic previews in
`review/2026-09-25-admin-activation-refresh/README.md`; the earlier prototype
is recorded in `review/2026-09-25-jarvis-activation/README.md`.
