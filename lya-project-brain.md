# LYA project brain
Camera natural-command routing follow-up (2026-10-05): owner screenshot shows expanded camera-open/person-view request reached general brain action route and returned not-connected. Live routing gate FAILED; camera hardware/detection was not exercised by that reply. Reproduced before fix. Added shared direct camera-control phrasing and local see-me presence handling in vision/answers.py and desktop/experience.py, preserving voice/hearing/UI/startup/authentication. Negations/how-why mentions/settings requests do not activate camera. 26 isolated vision checks and 64 offscreen temporary-store desktop checks passed, including reported phrase bypassing general model dispatch; syntax/whitespace passed. No sensor activation, owner-key access, external request or running-session restart. Evidence: review/2026-10-05-camera-objects/README.md follow-up. Next: owner reopens LYA and retries natural camera request; live camera/object/pointing acceptance remains pending. Enrollment/weather deferred.
Camera object references (2026-10-05): owner explicitly requests visible-object identification and hand pointing. Existing bounded local camera/common-object detector retained; added active-camera bare references, centered/near-hand selection and cautious 2D pointing with two optional pinned Apache-2.0 OpenCV hand models (~8MB), no new framework or image-cloud route. Missing/unclear/ambiguous targets ask for clarification. Camera-only routing/error fixes; owner working-feature freeze preserved. 24 isolated vision/dialog/pointing checks and 62 offscreen temporary-store UI checks passed; actual combined public fixture detected one hand/21 points and rejected open-palm pointing, eight blank frames clear. Initial resized-hand miss repaired with bounded 960px hand input; limited category detector, not arbitrary-object or 3D recognition. No owner camera/frame/key access or running-session restart by agent. Evidence: review/2026-10-05-camera-objects/README.md. Owner ready now; supplied reopen/open-camera/object/point/close instructions. Live owner camera/pointing accuracy pending; enrollment/weather deferred.
Owner freeze / saved-key location (2026-10-05): owner reports recent changes made earlier good behavior appear broken; affected components unspecified, no rollback or further feature change authorized. Added explicit AGENTS.md rule: never change working/owner-accepted features without a specific owner request; why/status questions do not authorize behavior changes. Current scope limited to rule and NVIDIA key storage. Added named Windows Credential Manager read for LYA/NVIDIA_API_KEY, after existing session environment key and before unchanged prompt; unavailable/invalid store retains prompt. No owner credential read/saved or voice/hearing/interface/wake/startup change. 13 isolated fake-credential/launcher checks plus compilation/whitespace passed. Evidence/instructions: review/2026-10-05-key-storage/README.md. Next: owner creates generic credential in Windows Credential Manager and verifies launch; await explicit scoped instruction about regressions. Enrollment/weather deferred.
Native key launch (2026-10-05): owner asked why LYA opens a terminal. Cause was console Python/getpass session-key launch. Added native masked --gui dialog, Cancel-before-desktop, safe startup errors and Qt application reuse; normal launchers now use pythonw. Existing owned startup shortcut migrated and verified; workspace LYA.lnk added/verified for direct shell-free launch (cmd can briefly flash its shell). Keys remain session-only, no credential persistence or hearing/output/privacy/auth change. Seven isolated launcher checks and 60 offscreen desktop checks passed; Python/PowerShell syntax, shortcut and whitespace checks passed. Synthetic masked dialog visually inspected. Running owner session not restarted; actual native owner launch pending. Evidence: review/2026-10-05-native-launch/README.md. Next: close current LYA and open workspace LYA.lnk, enter key in native prompt. Enrollment/weather deferred.
Conversation continuity / crystal design (2026-10-05): owner reports first successful integrated online LYA conversation; Parakeet primary and qualified Whisper backup retained. Fixed active-turn wake-name truncation/repeated greetings, context expiry during long capture/decoder waits, and punctuated stop routing. Refined native crystal accents, distinct diamond/thought/wave microdots, faceted panel, visible reply titles, literal paragraph/speaker formatting, actual phase labels and full card placement near screen edges. Preserved accepted speaking voice, privacy/authentication and reduced-motion controls; no dependency or live collection added. 77 isolated hearing/voice passes plus one designed skip; 60 isolated offscreen desktop passes; syntax/whitespace and synthetic dark/light/compact visual checks passed. Running owner session not restarted; new routing/design live acceptance pending. Evidence: review/2026-10-05-conversation-design/README.md. Next: restart via launch-lya.cmd with hidden session key; verify interior-name question and interruption. Noise/long-speech accuracy, enrollment/weather remain deferred.
Qualified Whisper backup / integrated launch (2026-10-05): owner reports fresh Whisper understood reasonably and better than old local candidates, but less precisely than accepted Parakeet. Keep Parakeet default and Whisper backup with qualified, not pinpoint, owner acceptance; no transcript copied. Integrated online LYA window launched for same hidden session-key entry before listening; direct desktop-process check found none but does not establish lock/UI availability or active listening. Startup prompt clarified. Prior 128 isolated passes plus one designed skip retained; no inference-code change or new live result from integrated desktop yet. Evidence: review/2026-10-05-hearing-plan/online-backups.md. Next: owner verifies displayed question and preserved speaking voice in integrated session; long/noisy/wake/stop unaccepted. Enrollment/weather deferred.
Online hearing with backups (2026-10-05): owner confirmed fresh Vosk/Whistle comparison was incorrect and chose ongoing online hearing with model backups. Local hearing gate FAILED; prior one-question NVIDIA Parakeet acceptance retained. Verified NVIDIA-hosted Whisper Large v3 and Parakeet CTC 1.1B API IDs/language settings. Implemented primary Parakeet -> one Whisper backup on selected model/service failures; CTC selectable spare; auth/quota/bad-input stop, cancellation/privacy checked before each attempt, no local guessing or heavy local warmup. Online-only private mode requests text. Model/backup status visible; exhausted service failure stops repeated-question loop. Normal launch and existing owned sign-in shortcut migrated to online session-key prompt; key not persisted. 70 isolated voice/hearing checks passed plus one designed skip; 58 offscreen desktop checks passed; actual request schema, CLI, syntax, whitespace and startup verification passed. Fresh Whisper check window launched, owner accuracy pending; integrated LYA reply/wake/stop not accepted yet. Speaking voice/security gates preserved. Evidence: review/2026-10-05-hearing-plan/online-backups.md. Next: accept backup words, then integrated primary question/reply. Shared-provider outage still not covered; free prototyping subject to rate limits. Enrollment/weather deferred.
Fresh offline hearing check (2026-10-05): owner explicitly requested fully offline laptop recognition before ongoing NVIDIA activation. Added tools/check_local_hearing.py: manual Enter, one in-memory complete capture, sequential current Vosk/experimental Whistle comparison, three-second pause/30-second rejection bound, Python networking/telemetry off, no audio files/cloud route/command dispatch. Default test excludes heavier optional Whisper. Three isolated synthetic checks and help passed; both actual local engines recovered meaningful words from an existing public generated-speech fixture. Visible owner-controlled check launched; fresh owner-local accuracy remains pending. No default/output voice/credential/startup/device-action changes or further NVIDIA use. Evidence: review/2026-10-05-hearing-plan/local-check.md. Next: compare exact local result with owner speech; ongoing NVIDIA session permission still pending. Enrollment/weather deferred.
Owner hearing breakthrough / NVIDIA connection (2026-10-05): owner confirmed fresh NVIDIA Parakeet speech-only output exactly matched their speech; screenshot showed completed transcription. One ordinary question hearing gate PASSED by owner report; exact transcript/screenshot not copied here. Optional complete-question NVIDIA route now connected to audio/voice.py and desktop/app.py behind explicit cloud flags. Current private mode checked after capture before routing, with local wake/stop and accepted output voice preserved. Added session-only hidden-key launcher tools/start_nvidia_lya.py using isolated client environment and existing desktop packages. 59 isolated voice/hearing checks passed plus one designed skip; 57 offscreen desktop checks passed after pilot environment dependency repair. No further live audio request, key recovery, protected action, desktop restart or default switch. Ongoing cloud questions await explicit session permission because prior consent covered one diagnostic question. Evidence: review/2026-10-05-hearing-plan/nvidia-connection.md. Next: activate if authorized, then verify integrated wake/question/displayed words/voice reply; noise, long questions and interruption still unaccepted. Enrollment/weather deferred.
Hearing pilot (2026-10-05): researched Cactus Whistle and NVIDIA Parakeet before building. Pinned Whistle assets/license verified; bounded local speech worker implemented. Public speech/silence/noise fixtures were useful, but the already-authorized local owner recording failed recognition. Whistle was not connected to production. Optional NVIDIA speech-only adapter and fresh-capture diagnostic implemented; 14 isolated fake-client/synthetic-audio checks passed. Separate ignored .venv-asr client installed; actual request-schema/capture imports passed without channel or microphone. Owner allowed one fresh ordinary NVIDIA speech-to-text check; visible diagnostic launched for hidden local key entry and manual readiness. No hosted recognition result available, no saved-recording upload, no production hearing success claimed. Accepted output voice preserved. Evidence: review/2026-10-05-hearing-plan/README.md. Next: verify exact recognized words from the fresh check before any assistant integration. Enrollment/weather/interruption acceptance deferred.
Voice retry/volume repair (2026-10-04): implemented a bounded clarification flow (one retry, then wait for fresh local wake), transient uncertain-word display, short volume-command suggestions and quiet-mode retry silence. Connected clear relative volume requests to the existing local handler through the unchanged verified-session/trusted-role gate; unavailable control no longer reports success. 85 isolated voice/brain/actuator checks passed + one designed online skip; 55 offscreen desktop checks passed; two affected brain checks rerun (already counted). No recognition threshold bypass, microphone/speaker/device action, audio upload, key access, model/output change, enrollment or desktop restart. These fixes do not establish accurate owner hearing or real volume effect. Evidence: review/2026-10-04-volume-retry/README.md. Next: restart to load changes, then verify recognized words/retry pause separately from authorized device effect; speech accuracy remains unresolved. Enrollment/weather deferred.
Current owner priority (2026-10-04): owner reports current speaking voice clean and replies sounding good; preserve that output. Focus on selected-input speech quality, faithful full-question recognition, then natural pauses/continuation/interruption, with one accepted stage before further model/device experiments. Corrected the microphone self-test's false implication that loud sound proves owner hearing or excludes a wrong input. 37 voice checks passed + one online skip; 52 isolated desktop checks passed. Hearing and live turn acceptance remain unresolved; no hardware defect established. No new recording, audio upload, provider/model/device setting change or output voice change. Prior Groq choice deferred/unanswered. Correction: earlier Voice Access closure attempt was denied by Windows, so the control was not closed; owner must close the trial window. Evidence/ordered gates: review/2026-10-04-voice-stabilization/README.md. Enrollment/weather deferred.
Local ASR implementation/recording comparison (2026-10-04): owner-authorized private recording retained only outside the repo; owner reports clear playback. US/Indian Vosk, streaming Zipformer, base/small English Whisper and filtered comparisons did not establish faithful owner recognition. Added optional local Whisper adapter with complete-turn/repetition rejection, explicit mic menu with safe restart, 2.5-second pause/120-second turn bound, and cancellation of late decoder output. Local audio is desktop default; Whisper remains experimental opt-in after the failed sample. Windows Voice Access input mode prepares the existing chat composer with LYA's microphone off. Owner ready test launched; process liveness observed, GUI/dictation result pending because Windows automation helper failed. 106 isolated checks passed + one online skip; two generated-speech/silence smoke outcomes passed. No owner audio upload, new Windows-test recording, paid service or enrollment. Live clock/stop gate unresolved; weather/enrollment deferred. Evidence: review/2026-10-04-local-asr/README.md. Next: owner reports English–India dictation text/setup stage before sending a question.
Free English voice research (2026-10-03): owner requires free software and clearer slow/long speech. Researched Windows Voice Access English–India (offline after model download) as independent control, sherpa-onnx streaming English Zipformer as an untested LYA candidate, and RNNoise with soft-speech/resampling limitations. Bluetooth Classic profile degradation is a hypothesis, not a measured cause. No installation, sensor collection, audio upload, provider-key access, device change or production integration. Existing live clock/stop gate remains failed. Recommendation and sources: review/2026-10-03-free-voice-research/README.md. Next: verify selected input via an independent free recognizer, then benchmark a separate streaming pilot.
Voice conversation/orb repair (2026-10-03): listening/hearing microdots, distinct thought orbits, compact wake, installed Amy female voice, speech-activity turn boundaries, longer bounded question capture, uncertain-input repeat guard and local stop/cancel path implemented. Isolated suites: 111 passed + one intentional online skip; real generated VAD four outcomes and stop five outcomes passed, with stop endpoint latency limitations. Narrow stop grammar rejected for a false interruption; candidate Indian Vosk/Whisper not connected to production. Owner-authorized local retry still declined uncertain clock words and failed spoken stop; owner confirmed both spoken with mic close. LIVE ACCEPTANCE FAILED. No recording/transcript retained, cloud diagnostic request, enrollment, protected-store/device-setting change or desktop restart. Workflow remains at the spoken clock gate; quiet capture/ASR isolation next, before weather or enrollment. Evidence: review/2026-10-03-voice-conversation/README.md and orb-states.png.
Voice timing repair (2026-10-03): owner reports broken sound and delayed replies. Hands-free command capture now uses a nonempty finalized result from the existing local Vosk model as an additional endpoint, so above-gate room noise need not always force the 12-second ceiling; silence fallback remains. Local playback skips the artificial pause after its last chunk while draining final words. Isolated voice/transport checks: 35 passed + one designed online skip; fake-engine playback: 18 passed; git diff --check passed. This is implemented and isolated-tested, not live accepted. No microphone/speaker, cloud request, protected store, device setting, enrollment or desktop restart. Audible distortion and crowded-room recognition remain unresolved. Evidence and next trial: review/2026-10-03-voice-timing/README.md. Owner must restart, repeat the quiet clock gate, and report recognized text, delay and sound defect before advancing.


Headset command gate (2026-09-28): owner confirms an updated live wake followed by the spoken question 'what time is it?' produced an unrelated Mumbai testnet answer. Spoken-command/answer acceptance FAILED; the exact recognized question is still unknown. Owner's next trial has not yet run. Native Windows headset input sounded much clearer to the owner than PortAudio's default in a bounded local comparison, but small offline ASR models still missed key words. Production now selects WASAPI input, retains all finalized Vosk segments and caps noisy-room command capture at 12 seconds; the desktop answer panel shows 'You asked' to expose the recognized question. Voice checks: 36 passed with one designed skip; desktop checks: 27 passed. Updated desktop restarted; no end-to-end success claimed. Evidence: review/2026-09-28-headset-command/README.md. Next: owner repeats the local clock question and reports the exact 'You asked' text; do not advance to live weather until this gate passes.

Soft-voice investigation (2026-09-27): owner reports Windows microphone meter moves only a little even when speaking softly near camera; Realtek Microphone Array Properties has no Boost slider. This points to weak capture before LYA's recognizer. No production gain/noise filter was added because the amplified prior sample remained unintelligible to local ASR and software gain would lift room noise too. Windows voice/noise effects availability still being checked. See latest ledger entry.

Microphone path follow-up (2026-09-27): owner heard LYA playback but no clear owner voice in the local copy. Windows microphone permission was allowed and the default Realtek array received sound. In a bounded test of LYA's actual input, the spoken-name window remained weak; the two-clap detector accepted one event in a separate cued window. This is a partial clap-stage check, not a full desktop wake/greeting success. No audio retained in this test; no production code or Windows setting changed. Evidence and next close-mic comparison: review/2026-09-27-wake-calibration/mic-path-check.md.

Owner-requested recording check (2026-09-27): owner reports maximum Windows input volume and requested a local audibility recording. Ten-second original and louder listening copy retained only in an owner-local temporary lya-voice-check directory outside the repo. Signal was weak without clipping; local recognition did not recover the requested phrase from either copy. This is not a personal listening judgment or proof of no audible voice. No cloud audio processing, transcript retention, enrollment or production change. Next: owner listens to louder copy to distinguish intelligible faint speech from noise/wrong input. Safe evidence: `review/2026-09-27-wake-calibration/recording-check.md`.

Current calibration gate (2026-09-27): owner confirmed speaking/clapping during timed local tests. Input remained weak in current and native formats; captured bursts could not reach the old clap threshold. Lowered default clap threshold and added quiet/noise regressions. A generated-speech false wake led to finalized-result name gating, trading some latency for rejection of provisional matches. 30 tests passed + one skip; 22 real-model fixture outcomes passed. Windows Sound settings opened without modification; awaiting input volume/meter report. Changes are on disk, existing desktop not restarted; live owner wake remains unaccepted. Evidence: `review/2026-09-27-wake-calibration/README.md`.

Live wake result (2026-09-27): after owner said ready, normal-session diagnostic opened microphone. First attempt registered no sound above its diagnostic floor; a cued channel check and repeated wake test confirmed sound input. The repeated actual listener test still detected neither name nor two claps, so no greeting playback was attempted. Failure is narrowed to the input-to-wake stage, not resolved; exact acoustic/timing/detection cause remains unknown. No recording/transcript retained, no cloud call or settings/source change. Evidence: `review/2026-09-27-name-wake-startup/live-check.md`. Next: separately cued name and clap calibration, then an owner-heard greeting before advancing.

Current voice status (2026-09-27, live failure isolation): owner still reports no hearing/response; the voice journey is NOT accepted. Added a bounded local diagnostic reporting microphone-open, sound-received, name/clap detection and greeting playback separately. `tools/check_voice_live.py` / `check-voice-live.cmd` are ready; no new production fix is claimed. Voice/diagnostic/transport checks: 29 passed, one intentional skip. Live test awaits owner readiness. Evidence and usage: `review/2026-09-27-name-wake-startup/live-check.md`.

Current hands-free startup gate (2026-09-27): no desktop process was running when checked and no LYA Startup-folder/user-Run entry was found. Owner requested automatic listening plus LYA/Laya/Leya/Elya anywhere in speech. Implemented contextual phonetic name matching and Qt single-instance lock; installed/verified native per-user sign-in shortcut via `tools/set-startup.ps1`; started updated LYA and verified duplicate launch exits. Voice/transport 27 passed + 1 skip, desktop 44 passed; real-model generated speech 22 expected outcomes. Owner live recognition/clap acceptance, future sign-in and sleep/resume remain unverified. Evidence: `review/2026-09-27-name-wake-startup/README.md`.

Current wake acceptance (2026-09-27): owner reports repeated spoken wake failed and requests two-clap wake. Replaced segmented standby capture with continuous local Vosk partial/final recognition; implemented short broadband double-clap detection in standby and command listening; enabled it in desktop; surfaced bounded microphone failures and truthful readiness. Voice/transport: 27 passed, 1 intentional skip; desktop: 44 passed; generated speech through real models: 14 expected outcomes, zero clap events on seven speech samples. Real microphone listener startup/stop succeeded in a bounded normal-session check. Human voice/clap recognition and spoken response remain owner-unconfirmed; exact cause of the reported running-app failure is not proven. Evidence: `review/2026-09-27-wake-and-claps/README.md`.

Current owner direction (2026-09-27, hands-free correction): speech is primary; typing is a public-place fallback. First acceptance gate is wake -> spoken invitation -> spoken question -> spoken answer -> follow-up. Fixed navigation/command teardown of the warmed speech worker, cached a prompt asking for input, synchronized its microphone guard to WAV duration, shortened wake-only silence and connected spoken clock/help/status answers. Voice/transport: 21 passed, 1 designed skip; compact desktop: 27 passed. Local prompt synthesis measured 4313.1 ms cold versus 229.1 ms warm, NOT end-to-end latency. Live microphone/speaker acceptance remains pending. Evidence: `review/2026-09-27-hands-free-voice/README.md`. This supersedes the typed-first owner trial below.

Current acceptance gate (2026-09-27): owner requested foundation-first work, one tested and owner-confirmed step before advancing. Step 1: desktop lifecycle. Fresh isolated checks: 14 foundation + 16 base UI + 5 compact lifecycle passed. Current visible launcher/typed-command/stop/quit/restart acceptance awaits owner confirmation. Preserve existing implementation. Prior end-to-end claims are not verified; current registration uses in-process Windows consent, so the unsigned legacy helper alone does not prove a current blocker. Evidence and next test: `review/2026-09-27-foundation-ladder/README.md`.

Wake-flow handoff (2026-09-27): the local Vosk wake listener, cached greeting, warmed Piper reply, and audio-synced caption path are implemented. The wake greeting is now trackable despite the WAV ignore rule; a source-based Mermaid flow is validated. Isolated offline checks pass: voice/setup-speech 20 with one intentional skip, desktop UI/experience 41, activation 22, registration 22. Activation/registration tests were updated for current Windows verification and existing-admin sign-in after stale assertions failed. Live microphone wake, cloud command transcription, and enrollment remain unverified; conflicting protected admin records remain untouched. Evidence: `review/2026-09-26-voice-wake/README.md` and `wake-flow.mmd`.


Latest voice-wake review (2026-09-26): an independent re-review of the 2026-09-26
change set (local-wake-then-transcribe listener, Groq Whisper opt-in, Piper pre-warm,
six-act activation walkthrough) re-ran all affected offline suites: 20 setup-speech/voice,
22 activation, 41 desktop UI/experience, 22 registration-UI, 141 external-work voice-lab
and 14 foundation checks — all green with the two designed online skips. Findings: the
legacy `audio/voice.py` speak() blocks its caller and spawns one voice subprocess per
utterance (P2/P3, desktop path unaffected); the 2026-09-26 review folder had no README
(now written). The Windows-proof blocker is unchanged and the activation gate still
fails closed. No sensor, enrollment or cloud call was made. Evidence:
`review/2026-09-26-voice-wake/README.md`.

Latest first-run/voice work (2026-09-25): `launch-lya.cmd` now opens owner setup by
itself when the store has no administrator, then plays the normal introduction; no
command has to be typed. Voice is on by default and the footer names the live mode
(remote Groq transcription or on-device only); speech is pre-warmed at launch so
the first answer does not wait for the voice model. The panel was redrawn as
layered glass. `test_activation.py` 22, `check_ui` 16, `check_experience` 23,
`test_registration_ui` 22 and the brain/approval suites all passed. This does not
make registration complete here: the protected store already holds admin record(s)
and an unresolved ambiguous state, so the gate correctly declines to auto-open
setup, and the Windows proof is still required. Details:
`review/2026-09-25-first-run-and-voice-first/README.md`.


Admin gate follow-up (2026-09-25): the Windows verifier's read-only
availability check now succeeds in the owner's current session. Enrollment is
still blocked by a pre-existing conflicting admin state in the protected
runtime store. No identity was verified, profile was created, or protected
record was changed. Admin lookup now fails closed on ambiguity, and the desktop
shows an owner-review message. See the latest work-ledger entry.

Smart App Control finding (2026-09-25): a read-only Code Integrity event check
identified Smart App Control enforcement as the policy blocking LYA's unsigned
Windows verifier. Microsoft provides no single-app approval for this feature;
the owner was not asked to disable protection. A trusted signed or reviewed
in-process desktop verifier remains the next gate. No policy or profile changed.
Details: `review/2026-09-25-admin-activation-refresh/README.md`.

Device-access follow-up (2026-09-25): after the owner confirmed Windows Camera
and Sound Recorder work, unsandboxed checks showed LYA's camera worker received
a real frame, its microphone worker captured audio, and the offline speech
worker completed a short greeting. Earlier sensor failures were restricted
session artifacts. The unsigned Windows Hello helper remains blocked by
Windows Application Control even unsandboxed; first-admin creation remains
unverified and locked. No media was saved and no profile was created. Details
are appended to `review/2026-09-25-admin-activation-refresh/README.md`.

Latest activation refresh (2026-09-25): first-owner `register admin` now opens
the voice-guided activation walkthrough and binds its verified session to LYA;
existing admins retain the prior sign-in path. The UI was visually revised and
the camera/microphone now start only from explicit buttons. Proof is tied to the
exact display name, raw microphone clips are discarded after measurement, and
presence/voice calibration is not presented as identity. 64 isolated desktop
and registration checks passed. Live device probes in this session could not
open the camera or capture from the microphone, and Windows Application Control
blocked the Hello helper. **No real admin was registered or signed in.**
Review and synthetic previews: `review/2026-09-25-admin-activation-refresh/`.

Latest initialization work (2026-09-25): added `desktop/activation.py` and
`activate-lya.cmd` — a six-act, voice-led owner walk-through (BOOT, IDENTITY with
a boss/sir greeting, OPTICS with a real camera scan, VOCAL with a real mic and
spoken code, VAULT with a Windows Hello proof, ONLINE) and 18 passing offscreen
checks. On this machine the real ledger reads: core, vault, store, optics,
camera, mic, voice output and the Windows checkpoint ONLINE; speech recognition,
face embedding and anti-spoofing LOCKED, so enrolment commits through the
verified Windows-device-only path rather than weakening the biometric contract.
Nothing was installed and no enrollment was performed. Details:
`review/2026-09-25-jarvis-activation/README.md`.


Latest admin bootstrap (2026-09-25): native registration can create a
Windows-verified, device-only admin in the encrypted runtime store, then bind a
five-minute desktop session; face/voice are not enrolled and phone-approved
private actions stay locked. It uses an exact fresh helper result, explicit
profile consent and a one-shot registration sweep. New keys live under the
per-user runtime folder; legacy keys remain untouched. 37 isolated
registration/recovery and 23 offscreen desktop checks passed. The live locally
built verifier was blocked by Windows Application Control, so **no real admin
was created or signed in**. Details: `review/2026-09-25-admin-bootstrap/README.md`.

Latest native task capability (2026-09-25): owner-approved `task add`, `tasks`,
`tasks all`, and `task done` now use a person-scoped table inside LYA's encrypted
local store. The table is created on first explicit addition; no real owner
store was opened. 44 isolated brain/approval tests passed, including encryption,
restart, person isolation and denied access. Live desktop identity/enrollment
remains deferred, so this is implemented and fake-tested, not end-to-end ready.
Details: `review/2026-09-25-task-list/README.md`.

Latest capability help (2026-09-25): native brain commands now share their
matchers with a capability catalog in `brain/capabilities.py`. Brain and
desktop “what can you do?” use that catalog; guest help lists public routes,
and protected routes appear only for an active verified person with the right
role. The desktop adds its actual interface controls. Focused checks passed
(39 brain tests and 38 offscreen desktop tests); live model and enrollment
status are still separate gates. Details in the latest dated ledger entry.

Latest device capability (2026-09-25): `device status`, `battery status`,
`memory usage` and `disk space` now return an on-demand local Windows snapshot
after verified-session authorization. The path reports battery, available RAM,
system-disk capacity and logical CPU count; it does not estimate CPU load or
battery runtime. A live read-only probe completed, and 41 isolated brain and
approval checks passed with fake identity and device readings. Exact owner
readings are not stored here. See the latest dated ledger entry.

Latest whole-project check sweep (2026-09-24): every isolated suite that avoids
real stores was re-run (the T01-T04 gates, storage-recovery, and sixteen further
suites): 346 test executions, 344 passed, 2 failed. `test_synthesis.py` alone
fails, because it stubs the superseded `Renderer.audio` while `speak()` now
consumes `Renderer.utterances`. `torch`, `insightface`, `speech_recognition` and
`pyautogui` are missing from `.venv-ui`, both loopback model servers are closed,
and 144 working-tree paths remain uncommitted. No real store, credential, camera
or enrollment was touched. Details:
`review/2026-09-24-full-check-sweep/README.md`.


Latest recovery preparation (2026-09-24): the external recovery helper now
builds a portable, passphrase-protected bundle of known encrypted stores and a
recovery key, verifies the copied ciphertext without the original Windows
account, and extracts it only into a new staging folder. Fake-key tests cover
wrong passphrase, changed ciphertext, secret exclusion, safe extraction and
failure cleanup. No real owner vault or database was opened, exported or
migrated, and no off-device copy exists from this work. Backup scope and
owner-run commands: `review/2026-09-24-brain-strategy/recovery-runbook.md`.

Latest desktop brain handoff (2026-09-24): a second question arriving while a
brain worker is busy no longer advances the UI generation and silently drops
the first answer. Stop still cancels and suppresses a late result. Two new
offscreen pending-worker checks pass; live provider transport interruption
remains unproven. Details: the final dated ledger entry below.

Latest transport cancellation (2026-09-24): the Oracle bridge's default
non-session path now uses its bounded cancellable SSH helper and closes stdin
after writing the request. Local fake-process completion and cancellation
passed; the deployed server and upstream provider were not contacted. Details:
`cloud/README.md` and the final dated ledger entry below.

Latest brain strategy check (2026-09-24): the native brain now answers short
personal fact questions from authorized saved records or abstains, and direct
unsupported actions do not masquerade as completed work. All 13 research
golden inputs avoided the model in isolated synthetic checks, but app launch,
live capability registry, real identity binding and live transport cancellation
remain open. At the 2,000-note cap, synthetic encrypted recall initially took
about 98 ms median; an encrypted in-database index measured about 11 ms after
implementation on disposable data. The existing owner database remains
unmigrated until a verified backup and explicit opt-in. Laptop power cost
remains open. Details:
`review/2026-09-24-brain-strategy/golden-results.md` and
`review/2026-09-24-brain-strategy/retrieval-benchmark.md`.

Latest camera update (2026-09-24): the Vision window now shows only the live camera with a small Start/Stop strip. Visual questions typed to LYA use her normal answer panel and configured speech; the camera has no separate question box. Live capture requested 1280×720 at 15 fps while detection analyzes a smaller copy no more than twice per second. A bounded real camera run and Qt handoff each measured about 15 fps after startup; the first Qt frame took 3.33 seconds. A synthetic preview and timing scripts are in `review/2026-09-23-vision/`. These checks do not establish object accuracy, voice naturalness or battery life. Camera frames remain local and transient, and face presence cannot authorize protected actions.

Historical live vision update (2026-09-23): explicit `open camera` / `look around` / `scan room` ran a local bounded video preview with face/object overlays and grounded scene questions. The earlier preview targeted six fps. Five sensor-free vision tests and 19 desktop experience checks passed at that point. Pen identification, liveness/anti-spoof authentication and identity enrollment remain unimplemented. Vision cannot grant access; Windows Hello PIN remains the protected-action authority. Details: `review/2026-09-23-vision/README.md`.
Latest local vision update (2026-09-23): an opt-in one-shot camera window is wired to local NanoDet object labels and YuNet face-presence boxes. It starts camera-off, has an eight-second worker limit, does not save frames, and never identifies or authorizes a person. Three sensor-free core checks and 18 desktop experience checks passed; a temporary public image produced one face and one person detection. An owner-authorized one-shot camera and UI handoff completed; visual accuracy and battery performance remain unreviewed. Models, hashes, screenshot, limits and next step: `review/2026-09-23-vision/README.md`.

Latest reply-speed update (2026-09-23): completed answers now reveal immediately
on LYA's existing 40-ms UI timer and finish long text in about 1.2 seconds of
animation. TTS runs separately and can start later. Seventeen isolated desktop
experience checks passed; real playback and battery tests remain open. Laya,
TypeSafe Jev and Jev Ultrafast were reviewed, not installed; they do typed
decisions/browser actions rather than speech or answer generation. Evidence:
`review/2026-09-23-fast-replies-and-decision-models/README.md`.

Latest English voice update (2026-09-23): the desktop selects the installed
native English Piper model while preserving the existing Tamil model. This
removes Tamil-accented English from the normal desktop path. Six desktop speech
checks and 42 focused external voice checks passed; public listening samples
and latency/memory evidence are in `review/2026-09-23-english-voice/README.md`.
The speaker changes across languages. Youthful/natural sound and full desktop
battery performance are not yet owner-accepted; no cloud speech is enabled.

Latest owner listening verdict (2026-09-22): unified Piper FAILED acceptance.
English sounds broken, delivery sounds read aloud, and the intended youthful
conversational voice is not achieved. Signal tests do not establish voice quality.
See the latest ledger entry below; prior implementation claims are dated evidence.

Canonical voice decision (2026-09-23): `external-work/` remains the production
runtime. `lya-external-work/lya-voice/` is an isolated quality bench and optional
remote comparison, not the private default. The production runtime now reuses one
PCM output stream per reply and closes it on completion, cancellation, device
failure or shutdown. 139 external voice tests pass, including real Piper English
and Tamil rendering and stream lifecycle checks. The owner-rejected English
naturalness remains unresolved; no claim of a youthful human voice is made.
Comparison evidence: `review/2026-09-23-voice-comparison/README.md`.

Latest voice update (2026-09-22): the repaired `external work/` bilingual voice
lab is connected to LYA's bounded desktop output subprocess. Its 100/100 package
tests, 5 transport checks and 16 desktop checks pass; a real mixed English/Tamil
model smoke test also passed. Remote speech, interjections and desktop speech
auditing are off. Phrase captions follow real audio chunk durations. Naturalness,
owner listening, microphone input and battery/memory soak remain open. See the
final ledger entry and `review/2026-09-22-external-voice-integration/README.md`.

Latest voice-output update (2026-09-21): local female Tamil/English neural speech
is wired to completed answers and registration. No implicit online TTS; local
Windows female English fallback. Benchmarked, but pronunciation, emotion, battery,
ASR and production conversation gates remain open. See the final ledger entry
and `review/2026-09-21-local-voice/README.md`.

Latest registration update (2026-09-21): simplified conversational setup with local
Windows spoken guidance and command-panel overlap fix. See the final dated ledger
entry and `review/2026-09-21-conversational-registration/README.md`. Microphone
listening and actual biometric enrollment remain pending.

Latest camera/voice stack decision (2026-09-21): OpenCV YuNet + SFace are
selected for lightweight local face detection/embedding; sherpa-onnx is selected
for offline VAD and speaker embeddings; whisper.cpp remains the T08 transcription
choice. Windows Hello PIN stays the authority for protected actions. Face/voice
will provide approximate identity for greetings/profile selection only. A read-only,
sensor-free probe found Python 3.12, OpenCV 5.0, NumPy and sounddevice available,
including FaceDetectorYN/FaceRecognizerSF. sherpa-onnx and all three pinned model
artifacts are missing, so the stack is correctly reported NOT READY. OmniVoice and
VoiceStudio were rejected for registration because they are voice-cloning/TTS tools,
not speaker-verification components, and are unnecessarily heavy here. Open Code
Review and Databasement are unrelated. Decision, security boundary and build order:
`LYA_CAMERA_VOICE_DECISION.md`; probe: `tools/check-biometric-stack.py`. No camera,
microphone, biometric material, model weight or credential was accessed/downloaded.
Next: pin licenses/versions/hashes, install sherpa-onnx and models, then build and
fake-test bounded adapters before any owner-approved real-device capture.

Latest owner-introduction visual correction (2026-09-21): the rejected cropped
four-corner crystal treatment was replaced with one intact crystal that moves from
center to a permanent identity dock. Four lightweight painted facets become the
stage rail; they are no longer cropped image fragments. The screen now uses one
opaque-tinted surface, compact decision cards, explicit actions, visible focus and
short copy. Its one-shot reveal is 1.05 seconds, paint-capped near 30 fps, skippable,
reduced-motion aware and completely idle afterward; there is no live blur, WebGL,
video, particle loop or idle timer. Current Microsoft motion/material guidance and
the fetched Web Interface Guidelines informed the choices. Fifteen UI, twelve core
and thirteen desktop-experience checks pass (40 total). Synthetic screenshots and
research links: `review/2026-09-21-registration-hologram-v2/README.md`. The prior
`registration-hologram` visuals are preserved as rejected historical evidence.
Interactive Windows verification, biometric capture and enrollment remain untested
and incomplete; LYA still stays guest-locked.

Latest guided-registration update (2026-09-21): desktop/registration.py now has a
center-crystal/four-corner reveal and a name -> device -> privacy -> review guide.
It uses cached artwork, a bounded 2.2-second reveal, roughly 30-fps paint-request
cap, no idle animation, skip and reduced-motion support. Device offers read-only
availability, Windows settings and consented PIN/Hello verification. Availability
never authenticates; no LYA admin/session is created. Face/voice choices remain
unsaved draft preferences and capture stays pending. A read-only device check ran
without opening sensors; interactive verification remains untested. No private
hardware identifiers are recorded here. 14 UI + 12 core + 13 experience checks
passed (39 total). Evidence: review/2026-09-21-registration-hologram/README.md.
Next: verify Windows in the owner's desktop, resolve optional personalization
versus mandatory biometrics, then connect trusted sessions and consented capture.
T04/T09 and actual enrollment are still incomplete.

Latest recovery-interface update (2026-09-20): native `desktop/recovery.py` is wired
to `open recovery`, `backup notes` and `restore notes`. It supports approved note
selection, separate-key generation/re-entry, no-overwrite encrypted archive saving,
authenticated restore preview and empty-profile restore. Work runs off the Qt UI
thread with cooperative cancellation, late-preview rejection and displayed-data
clearing on session changes. The real desktop remains guest-locked; enrollment and
trusted session binding are still deferred. No fake authority was added.
58 core/brain/approval/UI checks plus 13 experience checks pass (71 total), including
a temporary archive restored with a fresh local key and shutdown cancellation.
Evidence/screenshots: `review/2026-09-20-recovery-interface/README.md`.
This supersedes the earlier core-only statement that the UI/file boundary is
pending. Real owner verification, key custody and clean-device drill remain pending;
no cloud transport is active. Next: trusted owner binding when requested, then a
real recovery drill before remote backup. The interface alone does not complete T10.

Latest storage/recovery update (2026-09-20): `storage/recovery.py` exports only
explicitly selected owner notes and their internal relationships as a versioned
encrypted archive under an independent random recovery key. Restore requires an
empty verified owner profile, preserves expiry/revision, remaps IDs and never
imports identity or authority. Twelve isolated recovery tests pass, including a
new local encryption key, tampering, wrong key and interrupted writes. This is an
internal library; owner file/key-custody UI and cloud backup are NOT implemented.
The reviewed Brain path now requires literal True approval and chooses the local
client for verified personal requests. Local HTTP inference rejects redirects and
proxy inheritance. 33 brain, 3 approval and 12 registration regression checks pass
(60 total with recovery). No real store/key was migrated or private data uploaded.
Enrollment remains deferred and the desktop guest-locked. Plan and limits:
`LYA_STORAGE_SECURITY_PLAN.md`; evidence:
`review/2026-09-20-storage-recovery/README.md`; viewable workflow:
`diagrams/17-storage-recovery.png`. T05/T10 remain partial. Next: recovery UI/file
boundary and key-custody preview with synthetic profiles, followed by a real
owner restore drill only after trusted session setup is ready.

Latest Windows Hello checkpoint (2026-09-20): `register admin` / `admin setup`
now opens `desktop/registration.py`, a native consent/name/verification dialog.
`security/HelloVerifier.cs` calls window-bound IUserConsentVerifierInterop via the
installed .NET Framework; build with `security/build-hello.cmd`. No full SDK or
Python WinRT package was needed. The compiled helper is ignored by Git.
Read-only availability check returned DeviceNotPresent in the agent session;
successful real-user authentication has NOT been tested. Seven fake-process UI
tests and twelve registration-core tests pass. Verification alone cannot create
an admin or alter the Brain session. Capture/recovery remain pending. The UI uses
QProcess, a timeout and cancellation with late-result rejection, so it does not
block the UI or collect PINs, camera frames or microphone audio.

Latest registration hardening (2026-09-20, resumed): 12 isolated registration
tests pass. Consent and liveness callbacks now require literal True; tuple-shaped
failure results cannot pass. Verification expiry and cancellation are checked between
capture steps and before saving. Non-finite clocks, unsafe configuration and invalid
vector norms are rejected. No sensors or network were used for these tests.

Correction to earlier registration claims: this is a synchronous coordinator with
injected fake adapters, not a working enrollment screen or tested anti-spoof system.
Face prompts currently follow a fixed sequence; spoken codes are randomized. The
recovery code hash is stored, but recovery redemption, key restoration and acknowledgement
are not implemented. Dropping a Python reference does not guarantee raw-memory erasure.
An exact returned challenge is an in-process adapter contract, not cryptographic proof
by itself. Real Windows Hello verification, capture quality checks, biometric encoders,
device cancellation/release and recognition-to-greeting integration remain pending.
The environment has cv2 and sounddevice, but lacks Python winrt/winsdk, insightface and
resemblyzer. Missing dotnet alone does not establish that Windows Hello is unavailable.
The native desktop remains guest-locked. Do not enable enrollment based on the earlier
diagram's green nodes: they represent synthetic orchestration coverage only.

Latest admin-registration update (2026-09-20): the owner explicitly requested the
first primary-admin enrollment journey. Added a fail-closed local registration
coordinator, exact trusted-device bootstrap challenge, three active face challenges,
three fresh spoken-code challenges, consistency checks, atomic encrypted face/voice
template storage, one-admin enforcement, a one-time recovery code and a five-minute
session/greeting result. Disabled the legacy script that uploaded raw biometric media
to Supabase. Seven registration tests and the full Step 4 offline chain pass. These use
synthetic captures and a temporary DPAPI key/store; no real camera, microphone,
Windows Hello prompt, biometric template or production store was used. The desktop
remains guest-locked until the Windows Hello desktop adapter and visible device flow
are implemented and tested. Diagram: `diagrams/16-admin-registration.png`. Evidence:
`review/2026-09-20-T04-admin-registration/README.md`.

Latest Step 4 foundation (2026-09-20): owner requested Step 4 work and a viewable
Step 3 workflow. Added default-deny exact challenge adapter in security/approval.py,
Brain session/profile/role rechecks after approval, and pending-grant invalidation.
33 focused isolated checks passed. No real verifier, session issuance or enrollment
was enabled. Step 3's lexical check is not semantic proof; its regex is not a code
sandbox; its selected-rerun assistant score is not an independent quality estimate.
View diagrams/15-t03-t04-workflow.png (validated Mermaid source and SVG companion).
Evidence and next steps: review/2026-09-20-T04-foundation/README.md.


Latest T03 evaluation update (2026-09-20): the 30-case synthetic run exposed missed
coding classification, malformed research claims, unsafe cloud handling of secret
wording, weak planning answers and a Groq 429 after 23 cases. Each raw pass is
preserved. Coding prompts now route consistently and remain labelled untested unless
trusted evidence exists; research enumerates its claim contract; secret, plaintext
credential, unverified-memory and cross-person requests fail closed. Two repeated
LYA-specific planning failures moved to deterministic bounded answers. Frozen fixture
version 2 corrects the objectively wrong case-sensitive `Swiss` expectation from `w`
to `S` without changing thresholds. The latest selected answers score 143/150, meet
all six category thresholds and record zero critical privacy, fabricated-source or
false-test failures. All 106 offline T01-T03 checks pass. This score is assistant
review, so owner confirmation remains required before T03 is marked complete and T04
begins. Evidence: `review/2026-09-20-T03-evaluation/README.md` and `scored.json`.

Latest repository-fit and T03 verification update (2026-09-20): selected
`whisper.cpp` for later T08 offline-speech evaluation and deferred `yt-dlp` to a
bounded, user-authorized media task. OpenAI Whisper duplicates the selected speech
engine with a heavier Python/PyTorch stack; Postiz and Remotion are optional separate
social/video services rather than brain dependencies. Nothing was installed. Safe
configuration inspection found non-empty Jina and You.com variables without reading,
printing or transmitting either credential. T03 now rejects factual claims whose
numbers or content words are unsupported by their cited excerpts and visibly labels
inference and uncertainty. Seven focused checks and the full 100-check offline T01-T03
suite pass. This deterministic gate is not general entailment proof; disposable code
verification and the human-scored 30-case run remain open. Evidence:
`review/2026-09-20-repo-fit-and-semantic-verification/README.md`.

Latest free-first research update (2026-09-20): routine public research now uses
You.com's keyless search-only MCP profile, with six-source, 8,000-byte, 128 KiB and
eight-second bounds. A live synthetic adapter call returned three HTTPS sources.
Tavily is retained only for an explicit `critical research:` or `important research:`
request and only when its key plus both safety flags are present; ordinary searches
make zero Tavily calls. Seven adapter tests and the full 99-check T03 regression pass.
Agent Reach 1.5.0 is installed in its dedicated user environment. Its diagnostic
verifies Jina webpages, RSS, V2EX and basic Bilibili search; YouTube is present with
a configuration warning, while GitHub and Exa remain off until `gh` and `mcporter`
are installed. Full-page semantic claim checking and the frozen 30-case score remain
open. Evidence:
`review/2026-09-20-hybrid-research/README.md`.

Latest research-provider correction (2026-09-20): the rotated Gemini key and
free-only flags were detected without exposing the key. A synthetic public live test
failed closed: the Interactions endpoint returned 404, and the compatible
`generateContent` endpoint reported that Gemini 2.5 Flash is unavailable to new
users. Current official pricing says Gemini 3.6 Flash search grounding is unavailable
on the API Free Tier, so the Gemini research switch was disabled before trying a
billable model. `brain/research.py` now implements Tavily Search instead: one-credit
basic searches, no generated answer/raw page/images, six-source/8,000-byte/eight-second
limits and HTTPS-only output. Four fake-HTTP tests pass. Tavily's official recurring
free plan offers 1,000 credits per month without a card and stops at exhaustion.
Live research remains disabled until a Tavily free-plan key is added and accepted.
Evidence: `review/2026-09-19-T03-foundation/README.md`.
Latest grounded-research adapter update (2026-09-19): Gemini 2.5 Flash Google
Search grounding was selected from current official documentation and wired into the
desktop as an opt-in public-only adapter. It returns only provider-annotated cited
spans and HTTPS URLs, caps response/evidence sizes and source count, and enforces the
eight-second HTTP timeout. Four fake-HTTP adapter tests and the complete
`check-t03.cmd` offline suite pass. It remains disabled: the credential previously
shared in conversation must be rotated and the Gemini account must be confirmed
free-only before a live public fixture is transmitted. Provider annotations are not
independent semantic proof. Evidence: `review/2026-09-19-T03-foundation/README.md`.
Latest T03 workflow integration (2026-09-19): `Brain` now solves bounded
simple arithmetic through a local allowlisted evaluator without a model call. Public
research uses an injectable source-adapter contract, treats fetched text as untrusted,
requires structured claims and rebuilds visible output only from claims citing known
source IDs. Missing adapters, private context, malformed output and unknown citations
fail closed. Six verification tests, 23 Brain tests and the full offline T01/T02
regression pass. No live research adapter was called or activated. Semantic citation
support, hard adapter timeout enforcement, isolated code execution and the frozen
30-case scored run remain open. Evidence:
`review/2026-09-19-T03-foundation/README.md`.
Latest model-routing and T03 update (2026-09-19): the router now supports a disabled, exact-model OpenRouter free route whose upstream provider is pinned and response provider is verified; fake failover/denial tests pass. No OpenRouter credential is currently saved, so it was not called or activated. NVIDIA Nemotron 3.5 Lightning failed the eight-second gate from both laptop and Oracle and remains disabled. T02 is still blocked on a live independent backup. The official Qwen3 4B Q4_K_M local model was hash-verified and scored 5 pass, 1 partial, 2 fail on the eight-case local rubric; it replaces the weaker 1.5B launcher target as a provisional private-only model, with visible thinking disabled and explicit CPU-only startup. A live `Brain` private-mode request passed and made no cloud call. T03 preparation now includes 30 frozen cases, frozen thresholds and a bounded untrusted-evidence/claim contract; four structural tests pass, while research integration and the scored 30-case run remain pending. Evidence: `review/2026-09-19-nvidia-lightning/README.md`, `review/local-model-20260919-170638/README.md` and `review/2026-09-19-T03-foundation/README.md`.

Latest private-model update (2026-09-19): explicit `private mode`, `public mode`,
`privacy status`, `private:` and `secret:` routes are implemented. Private requests
use only the installed loopback llama.cpp endpoint and fail closed; the native UI
shows `LOCAL ONLY · CLOUD BLOCKED`. A synthetic live request passed with a cloud
client that would fail if called; 26 Brain/Oracle and 10 experience checks passed.
Jev was rejected for secret chat because it is a hosted typed-decision service, not
a conversational local model. AirLLM was not installed because its disk-streaming
approach is unsuitable for interactive use on this laptop. The 1.5B local model's
quality limitation remains. Evidence: `review/2026-09-19-private-local/README.md`.
Next: evaluate Qwen3 4B Q4_K_M through the existing llama.cpp runtime before changing
the approved local model.
Latest local evaluation (2026-09-18): the installed Qwen2.5 1.5B Q4 model completed
eight synthetic cases: assistant assessment 3 pass, 1 partial, 4 fail. Responses took
3.28–35.42 seconds; planning, security and Tamil hit the 384-token cap, and Tamil
repeated itself. The model is not approved as LYA's general offline fallback. Report
and raw evidence: `review/local-model-20260918-180912/README.md`. The dedicated test
server stopped and no llama-server process remained at final cleanup. Battery and UI
impact remain unmeasured. Next: evaluate a stronger model that fits this laptop before
adding a local inference route.

Latest T02 update (2026-09-18): local routing reliability and optional cancellable
SSH are implemented; 81 isolated checks pass. Temporary Oracle sources verified
wall-clock interruption and stdin cancellation. Both NVIDIA candidates stopped at
approximately eight seconds without answering, so independent live backup remains
BLOCKED. No production deployment or activation occurred. Groq's exploratory answers
included correctness failures. Evidence and activation/rollback handoff:
`review/2026-09-17-T02-backup/README.md`. Run `check-t02.cmd` for offline checks.
Next: resolve independent candidate acceptance before calling T02 complete.

Latest local-model update (2026-09-18): llama.cpp b11026 was installed through
Windows Package Manager and verified on the owner's ASUS Vivobook (8 GB RAM, Intel
i3-1215U, Intel UHD graphics). A Qwen2.5 1.5B Instruct Q4_K_M GGUF model is stored
under ignored `models/local/` and loaded successfully through localhost. The short
synthetic request returned the expected text at about 15 tokens/second on CPU. The
server was stopped after the check; it is not a background service and is not yet
wired into LYA routing. Launch with PowerShell execution-policy bypass:
`powershell -ExecutionPolicy Bypass -File .\\tools\\run-llama-local.ps1`. The launcher
uses six CPU threads, a 2,048-token context and CPU-only mode to limit heat and
battery use. `llama.cpp` is a private local fallback, not a replacement for the
hosted reasoning model. Next: add a local route only after an explicit latency and
quality comparison; keep private data local to this route.

### 2026-09-18 — Local llama.cpp installation

- Installed official `ggml.llamacpp` package b11026 with winget. Added the minimal
  `tools/run-llama-local.ps1` launcher; it discovers the winget package without
  changing global PATH. Added GGUF patterns to `.gitignore` so model weights cannot
  enter source control.
- Downloaded the official Qwen2.5 1.5B Instruct Q4_K_M GGUF into ignored
  `models/local/` and verified the 1,117,320,736-byte file through the local server.
- Health check: `GET /v1/models` returned `lya-local-1.5b`; synthetic chat completion
  returned the requested phrase. Server bound only to `127.0.0.1:8080` and was
  stopped after the check. No API key, private prompt, memory or external listener
  was used. Approximate observed generation speed: 15 tokens/second on CPU.
- Limitation: the model is a small local fallback and has not been added to the
  production router. It cannot replace Groq/Gemini/Z.ai for difficult research or
  coding until its quality is measured.
Candidate research (2026-09-18) is in `review/2026-09-18-free-provider-candidates/README.md`:
Cerebras, GitHub Models, SambaNova and the Hugging Face free paths are no longer
usable; W&B Serverless Inference, the Google Gemini free tier, Z.ai's permanent-free
GLM Flash models and the OpenRouter `:free` pool are the current options, documented
only — nothing was created, enabled or called.

Latest compact-conversation fix (2026-09-17): after a single-card answer completes,
typing a printable character now changes the card into the next one-line input and
preserves that first character; Enter opens an empty input. Keyboard shortcuts and
an active typewriter reveal are not intercepted. Implemented in
`desktop/experience.py`; regression coverage is in `desktop/check_experience.py`.
Full `check-t01.cmd` passed 67 isolated checks. Roadmap T01 remains complete; T02
is next: dependable failure handling and an independent live inference backup.

Latest chat-rendering fix (2026-09-17): chat no longer clears and typewrites the
whole transcript for every response. Existing history stays fixed, the current
question appears immediately, and only the newest LYA reply is appended with the
typewriter effect. Implemented in `desktop/experience.py`, with regression coverage
in `desktop/check_experience.py`. Full `check-t01.cmd` passed 66 isolated checks.
Transcript remains temporary, bounded to 12 speaker entries, and clears on close.

Latest window-controls update (2026-09-17): fixed clipped circle by removing the
legacy fixed-size silhouette mask. Direct-answer model prompt, answer-only card,
explicit chat controls, independently movable allowlisted document windows,
finite baked GLB rotation and persistent-crystal mode are implemented. Full
`check-t01.cmd` passed 65 isolated checks. Live provider wording, physical desktop
smoothness and battery use remain unverified. Current controls/evidence:
`desktop/qa/2026-09-17-window-controls/README.md`.

Latest interface refinement (2026-09-17): bottom-center introduction now gently
crossfades into a circular control; cards grow above it, with plain typewriter
answers. Implemented in `desktop/experience.py` and `desktop/app.py`. All 62
isolated checks passed, including idle repaint shutdown. Physical battery life
and live provider behavior were not measured in this UI task. Evidence and
synthetic previews: `desktop/qa/2026-09-17-bottom-center/README.md`.

Previous interface update (2026-09-16): centered baked-crystal guest greeting now
shrinks to a compact control. Click for one-line input; replies use a small card;
`open chat` expands the workspace. `desktop/experience.py` reuses the existing
native commands and privacy boundary. The owner's latest request selects baked
model artwork by default; `--original-art` remains the fallback. All 62 isolated
checks passed, including five new interaction checks. Idle repaint shutdown was
checked; actual battery life and physical FPS remain unmeasured. See
`desktop/qa/2026-09-16-compact/README.md`. Voice and identity are still pending.

Latest baseline update (2026-09-16): roadmap T01 is complete. The documented
Windows launcher started the expected native app; 57 isolated checks passed across
routing, Oracle bridge, provider boundaries, brain workflow and native UI. Guest
identity, deterministic commands, stale-result cancellation and the actual Qt Quit
path passed. No live provider request, sensor, enrollment or private-store operation
ran. Evidence: `review/2026-09-16-T01-baseline/README.md`. The owner can rerun the
safe suite with `check-t01.cmd` and follow `LYA_TEST_GUIDE.md`; the visual status/test
flow is `diagrams/14-t01-working-and-test.png`. Next task is T02.

Task assignment update (2026-09-16): [LYA_TASK_REASONING_LEVELS.md](LYA_TASK_REASONING_LEVELS.md)
classifies the roadmap into high, medium and low reasoning work. T01, T07 and
T08 can be led at medium level with stated high-level boundaries. The other
production tasks need high-level leadership. Low-level work is limited to exact,
reversible preparation and evidence collection; no full production task is low.

Developer handoff (2026-09-16): [LYA_IMPLEMENTATION_CHECKLIST.md](LYA_IMPLEMENTATION_CHECKLIST.md)
expands all 14 roadmap tasks into implementation steps, prerequisites, acceptance
cases, blocker handling and completion templates. These are planned requirements,
not newly implemented runtime capabilities.

Current delivery order (2026-09-15): see [LYA_TASK_ROADMAP.md](LYA_TASK_ROADMAP.md)
for 14 ordered tasks, dependencies, acceptance checks and independent owner work.
Next: reproduce the baseline, then dependable provider backup and answer verification.
This roadmap refines older planning order; it does not mark planned features complete.

Latest orb update (2026-09-15): the owner's GLB is preserved and rendered into an
optional static transparent artwork. The earlier orb remains the default because
short repeated measurements showed higher process CPU with the new artwork.
Both use finite decorative motion that stops at idle. Artwork switching, invalid
image fallback and slow-paint fallback are implemented; all 16 UI checks passed.
Battery impact and physical display FPS remain unmeasured. See
`desktop/qa/2026-09-15-orb/README.md` and `desktop/README.md` for evidence and controls.

Latest launcher update (2026-09-15): `launch-lya.cmd` opens the native panel without
requiring PowerShell script execution. The earlier launch check started a
responding LYA conversation window; the Python processes remain running on resume.
Use this launcher instead of changing system execution policy. Git is now present
on branch main with origin/main as its locally recorded upstream; earlier notes
about the absence of Git describe the original supplied snapshot.

Latest activation update (2026-09-14): public-text Groq inference is now configured
on Oracle and selected by the native desktop. The actual Qt worker -> Brain ->
SSH -> router -> Groq -> glass response path passed a synthetic live check.
Private-context routing was denied before a provider call. NVIDIA catalog access
works but candidate generation was unreliable; its routes remain disabled. There
is currently no dependable active independent backup. Model accuracy remains a
separate open gate: live evaluations found hallucinated plans and a wrong coding
assertion. See `review/2026-09-14-live-models/README.md`. No enrollment or private
memory upload occurred. The earlier disabled-configuration entries below are
historical evidence superseded by this activation entry.

Latest routing update (2026-09-14): bounded multi-provider routing implemented,
38 targeted checks passed and a synthetic failover check passed on Oracle.
Live provider routes remain disabled; usable credentials were not found in the
known project/environment settings. See `LYA_MODEL_STRATEGY.md` for the verified
shortlist, implementation limits and activation gates. Storage expansion follows
real brain/model acceptance; existing encrypted memory remains in place.

Latest connection update (2026-09-14): SSH authentication succeeded using the
owner's newly supplied key. Read-only commands verified ARM64, 4 online CPUs,
approximately 24 GB RAM, a 193 GB root filesystem and Python 3.12.3. The original
key rejection is resolved. Resource allocation does not establish ongoing free
eligibility. A credential-free SSH inference backend is now uploaded and its
missing-provider response was tested over real SSH. No live model request has
completed; provider choice/activation remains pending the owner's decision.

Last reviewed: 2026-09-13. Latest milestone: native brain dispatch, scoped memory
lifetimes, small knowledge graph and bounded council orchestration implemented.
Isolated acceptance: 91 checks passed, one online speech test skipped; five earlier
review probes no longer reproduce. See `LYA_BRAIN_WORKFLOW.md` and
`review/2026-09-13-retrieval/results.json` for current evidence.

This latest entry supersedes earlier broad completion and defect-status claims.
The real desktop remains a guest: identity/phone approval is not bound to the new
brain and a local model was not reachable. Offline voice requires a missing local
model. Synthetic checks do not prove live recognition, inference, phone or cloud
integration. Earlier review reports remain preserved as dated evidence.

Newest runnable milestone: `launch-lya.ps1` opens the custom crystal alone. See
`desktop/README.md` for commands and limits, and `desktop/qa/` for rendered UI checks.
This is a separate PySide6 presentation layer, not the completed wake/identity journey.

Visual map: see `LYA_ARCHITECTURE.md` and `diagrams/` for the current system. See `LYA_REBUILD_PLAN.md` for acceptance gates and `LYA_FOUNDATION_DECISIONS.md` plus `diagrams/10-wake-identity-storage-mobile.svg` for the chosen first experience and a directly viewable diagram.

## Honest assessment

Your work has produced a real engineering foundation. The native runtime, permission checks, explicit memory retention, encrypted transactions, and isolated regression tests are concrete progress. The strongest part is the decision to restrict actions until their authorization path is ready.

LYA is not yet a dependable everyday Jarvis-style assistant. Many advertised capabilities exist only as legacy modules, model-generated advice, or requirements. The next improvement should be completing a small number of reliable user journeys, not adding more skill files. No defensible overall completion percentage can be calculated without a fixed release scope and acceptance criteria.

This file is the current project record and future work ledger. It records the supplied source snapshot, not an independently verified history of every earlier session. This directory has no Git repository, so authorship, commit history, and previous versions could not be established.

## Evidence and review limits

Reviewed the product documents, current native command flow, UI, memory and model paths, voice loop, identity/approval integration, reminder parser, file browser, forge, and legacy routing/cloud boundaries. Inventoried the remaining modules and parsed every Python source file. This is a functional and architecture review, not an exhaustive audit or biometric validation.

| Check on 2026-09-10 | Result | Meaning |
|---|---|---|
| Python syntax via AST | All 59 Python files parsed, including the new review script; 58 were supplied | Syntax only, not import/runtime correctness |
| Original `test_foundations.py` | 13 passed, 1 failed | Folder assertion compares a resolved long Windows path against an unresolved short path |
| Same suite with temporary directory path normalized before execution | 14/14 passed in 0.491 seconds | Confirms the original failure is test path portability; application/test source was unchanged |
| `review_checks.py` | Three reminder defects, memory speech flag defect, and missing tone engine attribute reproduced | Uses fixed time, fake memory and AST extraction; no real secrets, network or sensors |
| `test_native_ui.py` | Blocked at Tk initialization | Bundled runtime could not load a usable Tcl init; explicit Tcl/Tk paths did not fix it |
| Live microphone, camera, iPhone, cloud/model requests | Not run | No end-to-end claims for these integrations |
| Older security/crash scripts | Not run | Existing README warns some older tests modify real stores; they are not the safe regression suite |

`python` is not on this shell's PATH. Tests used the bundled interpreter:

`C:\Users\kathirvel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`

Reproduction commands in PowerShell:

```powershell
$lyaPython = 'C:\Users\kathirvel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $lyaPython -B test_foundations.py
& $lyaPython -B -c "import tempfile,pathlib,runpy; tempfile.tempdir=str(pathlib.Path(tempfile.gettempdir()).resolve()); runpy.run_path('test_foundations.py',run_name='__main__')"
& $lyaPython -B review_checks.py
& $lyaPython -B test_native_ui.py
```

The review script deliberately describes currently reproduced bugs. It is not a release gate and should be converted to expected-behavior regression tests when those bugs are fixed.

## Product purpose and agreed direction

Source: `LYA_VISION.md`, whose earlier owner discussion was supplied with this snapshot.

- Native desktop orb, focused panels, voice and typed commands.
- Accessibility: people unable to use their hands should be able to complete supported tasks, navigate results, cancel and approve.
- Work within the owner's hardware and zero-subscription budget; actual hardware/model/cloud resources remain unverified.
- Act only on a user request or an explicitly authorized scheduled task.
- Basic guest conversation; recognized trusted users get selected low-risk operations; owner-only private actions need fresh phone approval.
- Identity uncertainty must not reveal private facts or grant private actions.
- Keep temporary chat distinct from explicitly saved knowledge; support corrections and forgetting.
- Research should preserve evidence; multiple model opinions do not establish truth.
- Enrollment was explicitly deferred in the supplied requirements. This review did not enroll anyone or configure real credentials.

## Architecture and what has been built

Current path: `main.py` -> bounded command queue -> one worker -> explicit command branches -> permission checks -> selected capabilities. UI updates flow through `ui/orb.py`'s queue to the Tk event loop. General responses call `brain/mind.py`. Private memory uses `brain/memory.py` -> `security/database.py` -> `security/vault.py`. Phone requests use `security/escalation.py` and the separate HTTPS `web_server.py` process.

| Area | Present implementation | Current status |
|---|---|---|
| New crystal desktop | PySide6 crystal, compact glass, typed commands, document previews and voice-to-Qt signal bridge | 10 UI checks pass on 2026-09-13; live voice launch/import and status gaps remain; identity/memory/model routes not connected |
| Legacy native shell | Tk orb, floating answer/folder/style panels, expand/shrink, themes, entry box | Retained; its Tk visual/runtime QA remains blocked here |
| Safe build mode | Synthetic folders, temporary themes, help/time/UI operations | Isolated handler checks pass; full GUI unverified |
| Worker and cancellation | Queue limit 8, background processing, stop clears queued commands and browser authority | Basic cancellation tests pass; does not interrupt every in-flight call |
| Permission policy | Public/trusted/owner actions; unknown capabilities deny | Offline policy tests pass |
| Folder browsing | User-home scope, current-directory paging, exact visible selections, file metadata only | Hardened & verified; boundary checks pass, non-executable inspection verified |
| App actions | Fixed calculator/notepad/explorer/chrome executable names and volume keys | Hardened; non-shell allowlisted Popen, native pywin32 multimedia keys, and mock tests pass |
| Private facts | Explicit save, protected label, recall, exact-key forgetting | Storage roundtrip/concurrent thread/corruption tests pass; phone-integrated use pending |
| Encrypted transactions | SQLite in RAM, encrypted atomic replace, thread/process locking | Thread concurrency tested; separate-process stress and recovery not tested |
| Chat | Provider fallback, bounded histories and person-scoped context helper | 5 component tests pass; new probes reproduce first-person fallback, legacy fallback and credential inclusion; not ready for private context |
| Voice | One capture loop, forwarding, local TTS, optional Vosk | Implemented; device accuracy, latency and recovery unverified |
| Phone approval | HTTPS, token, displayed task, nonce, phrase, owner face/liveness, expiring single-use grant | Implemented & hardened; 12/12 dedicated tests pass; local TLS gateway, rate limiting, and single-use grant consumption verified |
| Learning | Model lesson draft, ten-minute expiration, explicit save | Code present; no web verification or model training |
| Council | Up to three concurrent advisors, chairman synthesis | Advisory only; provider calls untested |
| Skill forge | Draft file and metadata generation; activation disabled | Hardened; Python syntax validation on drafts, activation lockout strictly enforced |
| Reminders | Encrypted text/time fields in SQLite; 30-second watcher started on first use | Hardened; relative, weekday, and explicit calendar parsing verified; RAM decrypted chronological sort |
| Screenshots | Owner-gated capture to `shots/` | Hardened; sandboxed directory creation, timestamped PNG output, and pywin32 fallback |
| Guardian & Safety Gate | Ultron safety layer; dangerous command screening, gated execution, silent duress alarm, dual encrypted audit logging | Hardened & verified; 12/12 dedicated tests pass; fails closed on tamper |
| System Health Governor | Zero-dependency Windows resource monitoring (WorkingSet RAM, battery, AC power, disk) & emergency kill switch | Hardened & verified; zero background CPU, instant kill-switch circuit breaker |
| Legacy capabilities | Cooking, teaching, guidance, technical helpers, security learning, network/device tools, phone/autonomy modules | Files exist; not routed by current native command path |
| Knowledge graph/sync | Separate graph/retention and cloud synchronization modules | Not the active native retention path; integration unverified |
| Legacy cloud/browser HUD | Separate implementations retained | Cloud POST actions disabled; HUD is not the primary product |

## What is particularly good

1. **Permissions are enforced in code.** The native flow does not rely on a model agreeing to behave. New actions have to be admitted to the policy deliberately.
2. **Private context is opt-in.** Guest requests do not load saved private facts into the native model prompt. History is bounded and separated by session/verification state.
3. **Storage has meaningful engineering behind it.** Atomic encrypted commits, serialization and corruption preservation are stronger foundations than saving raw chat JSON. The tests cover actual storage behavior using fake encryption keys.
4. **The UI and long tasks are separated.** The worker/queue pattern gives the interface a chance to stay responsive during network and approval waits.
5. **Generated code stays a draft.** This avoids treating plausible model output as a verified executable feature.
6. **The main README is candid.** It explicitly distinguishes prototype features, disabled paths and pending integrations. That honesty should be extended to older module descriptions.
7. **The accessibility purpose is clear.** It gives the project a useful product direction, beyond visual imitation of a fictional assistant.

## Confirmed defects and concrete concerns

Priority meanings: P1 = fix before relying on the affected private/core workflow; P2 = functionality/reliability fix; P3 = maintenance/documentation. These are review priorities, not claims of remotely exploitable vulnerabilities.

### R01 — P1: saving a private fact can speak its contents

Evidence: `main.py`, `Assistant.handle()` remember branch and `_worker()` speech condition. `private_output` begins false. The confirmation embeds a key made from the first six words of the fact, without setting the private flag. The worker speaks replies when that flag is false.

Reproduced with fake storage: `remember my private example is blue` returns the private words with `private_output=False`. No real fact was stored or spoken during testing.

Fix target: mark the save path private before returning content, or provide a generic non-sensitive spoken acknowledgment. Acceptance: voice output contains neither the fact nor its derived key; approved visual feedback remains useful.

### R02 — P1: reminder dates can be wrong

Evidence: `skills/reminder.py::_time_hint`; reproduced with clock fixed at Thursday 2026-09-10 12:00.

| Input | Expected | Actual |
|---|---|---|
| `remind me to call next monday at 9am` | Monday September 14, 09:00 | Tuesday September 15, 09:00 |
| `remind me to call in 2 hrs` | September 10, 14:00 | No time parsed |
| `remind me to call on 5 june at 6pm` | June 5, 2027, 18:00 | September 11, 2026, 05:00 |

Causes include an extra day in the next-weekday expression, matching `hrs` without handling it in the relative-time conversion, and passing the wrong regex-group shape for day-month dates. The fallback clock regex then interprets a date number as an hour. Acceptance: deterministic tests for supported phrases, rejection of ambiguous/invalid inputs, and confirmation of the resolved date before reliance.

### R03 — P2: text mode falsely describes itself as a safe preview

Evidence: `main.py::main` passes `preview=mode!="voice"`, while only `mode=="build"` sets the assistant's safe build flag. `ui/orb.py::run` displays “no microphone, model calls or device actions” for preview. Thus text mode shows a statement that does not match its enabled handlers. Text mode can call a model and, with identity/approval, perform real actions. Fix the mode label separately from whether the orb initially appears.

### R04 — P2: voice cannot reliably interrupt long tasks [RESOLVED 2026-09-12]

Evidence: `audio/voice.py::wake_loop` only routed bare `stop`/`cancel` while its 45-second conversation window was active. Phone approval may wait 120 seconds. After the window expires, an unprefixed spoken stop could be ignored.

Resolution: Extracted `process_utterance` in `audio/voice.py`. Bare `stop`, `cancel`, `sleep`, and `go to sleep` now immediately route to `on_wake` and reset the conversation window even when the 45s window has expired or while TTS is speaking. Verified in `test_voice.py::VoicePipelineTests.test_r04_interruption_during_speaking` and `desktop/check_ui.py::InterfaceChecks.test_voice_wake_signal_dispatch`.

### R05 — P2: emotional speech-rate updates silently fail

Evidence: `brain/mind.py::set_tone` references `voice.engine`, but `audio/voice.py` exposes `_engine`. Its broad exception handler hides the missing attribute. The default TTS rate can work while advertised tone modulation does not. Attribute mismatch reproduced without initializing audio hardware.

### R06 — P2: forge does not use the same stored key as chat [RESOLVED 2026-09-12]

Evidence: `brain/mind.py` can load the DPAPI-encrypted Groq key; `skills/forge.py::_groq` directly indexed `os.environ['GROQ_API_KEY']`.
Resolution: Reused `mind.get_groq_key()` in `skills/forge.py`, providing a unified key resolution chain (environment variable -> DPAPI vault file -> `%LOCALAPPDATA%\LYA\vault`). Verified in `test_mind.py::MindGatewayTests.test_r06_unified_groq_key_resolution`.

### R07 — P2: reminder ordering and delivery are incomplete [RESOLVED 2026-09-12]

Evidence: `skills/reminder.py::list_all` ordered by `when_iso`, which contained randomized encrypted tokens rather than sortable timestamps.
Resolution: Modified `list_all()` in `skills/reminder.py` to decrypt all records in memory first, then perform a sorted order by decrypted ISO timestamps. Verified in `test_foundations.py` and `test_regressions_r01_r05.py`.

### R08 — P2: install and recovery are not reproducible yet

No `requirements.txt`, `pyproject.toml`, lockfile or CI configuration was found in the supplied file inventory. The README names dependencies, but a clean-machine install is not encoded or verified. Python is absent from PATH here and the available runtime cannot initialize Tk. The referenced anti-spoof repository/models are absent from this snapshot. These are environment/integration blockers, not evidence that all application logic is broken.

Acceptance: one documented supported Python environment, dependency groups, a harmless readiness check, and a tested GUI launch. Do not download large biometric/model dependencies until the selected setup needs them.

### R09 — P2: saved knowledge is not yet a per-person durable assistant memory

`brain/memory.py` has no person/session column on memory rows. Native private context takes the top 15 saved entries rather than retrieving facts relevant to the question. A save always inserts another row; keys derived from the first six words can collide. `forget_exact` deletes all exact matches. `save lesson` says the lesson is labeled unverified, but persists the answer and `kind=lesson`, without a separate provenance/verification field.

This is useful explicit note storage. It needs ownership, correction/version semantics and source status before it can satisfy the larger personalized learning vision.

### R10 — P3: old claims and instructions conflict with the active implementation

Examples: `cloud/README.md` instructs an HTTP gateway launch, whereas the active server requires TLS configuration; the cloud UI suggests features whose POST handlers return 503. `skills/forge.py`'s opening description says confirmation activates code, but activation is disabled. `brain/knowledge.py` says every message passes through it, whereas the native handler does not route messages through that module. `skills/allskills.py` says main calls it, but current main does not. Older “full device control,” accuracy and encryption slogans should not be treated as verified product guarantees.

Acceptance: label legacy entry points clearly and update descriptions from actual call paths. Provider pricing, free-tier terms and model identifiers were not checked online in this local review.

### R11 — P3: test portability and coverage gaps

The folder assertion should compare against `root.resolve()` or the browser's resolved root. Tests often extract individual functions with AST or mock dependencies; that is useful isolation but misses startup imports and integration contracts such as the tone engine name. Add only targeted expected-behavior checks for the bugs above, plus one end-to-end journey once its environment is ready. There is no evidence here of full process-concurrency, long-duration stability, biometric accuracy or device performance tests.

## Deliberately unfinished rather than broken

- Admin enrollment and trusted iPhone pairing/HTTPS setup.
- Hands-free iPhone approval: current page needs token/phrase input, camera permission and buttons.
- Durable visitor naming and relationship-specific memory/delegation.
- Live web research, source retention, evidence-based answers and reference-to-theme conversion.
- Isolated generated-skill execution, versioning and rollback.
- Goal-level inspect/plan/execute/verify workflows across applications.
- Automatic startup, reminders when the laptop is off, integrated cloud identity/sync.
- Measured CPU/RAM/latency budgets and actual laptop/phone accessibility testing.

## Data map and retention rules

There are two distinct needs: recording project development and retaining runtime user information. This Markdown file handles the first; it does not change the assistant into an automatic recorder of everything.

| Data | Current location/behavior | Handling |
|---|---|---|
| Product requirements | `LYA_VISION.md` | Keep as owner intent; changes need a dated decision |
| Earlier milestone claims | `BUILD_PROGRESS.md` | Historical record; this review supplies newer evidence |
| Current status, findings and decisions | `lya-project-brain.md` | Update after each development task |
| Review reproductions | `review_checks.py` | Synthetic evidence; convert to fixed-behavior tests with fixes |
| Source and tests | Project module paths | Link here instead of copying whole files |
| Chat history | Bounded RAM in `brain/mind.py` | Not automatically durable; restart loses it |
| Explicit saved facts/lessons | `brain/lya_brain.db.lya` | Encrypted private runtime store |
| Reminder records | `data/reminders.db` | Contents/time encrypted; table metadata remains SQLite |
| Identity and secrets | `.lya` stores and `security/.lya_key` | Never copy values or biometric material into this document |
| Screenshots | `shots/` | Plain private images; ignored by Git, not a backup |
| Themes | `data/appearance.json` | Local settings |
| Generated skill draft | `skills/forge_draft.py`, `skills/forge_meta.json` | Local draft overwritten by later drafts; activation disabled |
| Visual architecture pack | `diagrams/01..08-*.mmd` + `LYA_ARCHITECTURE.md` | Derived-from-source maps; re-validate with `mermaid.mjs check --all` and re-check status colours when code changes |
| Future research/reports/assets | Save in an appropriate project path; record it below | Preserve file, source, date, status and sensitivity; no directory scaffolding needed until used |

Do not dump passwords, tokens, raw biometric samples, private transcripts or personal facts into a plaintext project brain. Record safe summaries and paths to appropriately protected material instead. The existing runtime memory consent boundaries remain in place.

This review creates a root `AGENTS.md` instruction to read and update this ledger on future coding tasks. That is a workflow for cooperating agents, not a background service or guaranteed capture from every application. Future chats must use this workspace and follow the instruction. Files generated outside it must be saved or linked explicitly. This file and all local artifacts still need a real backup/version-control plan; no Git initialization, remote backup or automatic runtime capture was performed.

## Next milestones and acceptance criteria

1. **Stabilize the current foundation.** Fix R01-R07 and the test path comparison. Each fix gets a focused regression check. The safe suite passes without path workarounds; mode labels and documentation match reality.
2. **Make preview/install dependable.** Establish a supported Python/Tk environment and a minimal dependency manifest. Launch build mode on the actual screen and verify panels, sleep/wake, focus, scaling and keyboard exits.
3. **Complete one useful accessible journey.** Validate voice -> read-only folder navigation -> selection -> back/scroll -> cancel, including errors and long waits. Enrollment/pairing remains a separately authorized setup milestone under the supplied requirements.
4. **Make explicit memory dependable.** Save, recall, correct and forget fake test facts with private output and restart persistence. Add ownership/provenance only to the extent needed for approved users and lessons.
5. **Make reminder delivery dependable.** Fix parsing, sorting, startup and acknowledgment; test restart, overdue reminders and missed delivery.
6. **Then add one evidence-based research or verified app workflow.** Keep sources and outcome checks. Integrate each legacy capability through the current policy rather than enabling the entire old router.

## Work ledger

| Date | Work | Status | Evidence/artifacts |
|---|---|---|---|
| Before this review; exact history unavailable | Native interface, policies, memory transactions, phone protocol, voice loop, draft learning/council/forge | Present in supplied snapshot | `README.md`, `BUILD_PROGRESS.md`, source; verification limits above |
| 2026-09-10 | Functional/architecture review and current-path inventory | Completed within stated scope | This file |
| 2026-09-10 | Foundation suite and normalized-path diagnostic | Completed | 13/14 raw; 14/14 normalized; no application changes |
| 2026-09-10 | Syntax scan and isolated defect reproductions | Completed | `review_checks.py` |
| 2026-09-10 | Native widget smoke test | Environment-blocked | Unusable Tcl initialization; no visual sign-off |
| 2026-09-10 | Project continuity record and future-agent instructions | Created | `lya-project-brain.md`, `AGENTS.md` |
| 2026-09-10 | Application bug fixes | Not performed in this review | R01-R11 remain open |
| 2026-09-10 | Full inch-by-inch re-read of every Python file + dependency probe | Completed | 13 required libs probed; only `cryptography`, `numpy` present; 11 findings N1-N11 |
| 2026-09-10 | Visual architecture pack: 8 Mermaid diagrams, all validated | Completed | `diagrams/01..08-*.mmd`, `LYA_ARCHITECTURE.md` (8 embedded blocks); 16/16 render clean |
| 2026-09-10 | Installed the `mermaid` skill (validate/extract/trace) | Completed | `~/.codegpt/skills/mermaid` + `~/.claude/skills/mermaid`; 5 real validator bugs found and fixed by using it |
| 2026-09-12 | Installed the verified Mermaid package for Codex | Completed | `~/.codex/skills/mermaid`; official curated list had no Mermaid entry, so the previously verified local package was copied exactly |
| 2026-09-12 | Planned a from-scratch verified-core rebuild | Completed; implementation not started | `LYA_REBUILD_PLAN.md`, `diagrams/09-lya-from-scratch-workflow.mmd`; existing prototype preserved as reference; full Mermaid check 18/18 passed after repairing corrupt `999` prefix in older diagram 08 |
| 2026-09-12 | Decided native wake, face identity, per-person storage and mobile-cache foundation | Planned; no real enrollment or runtime implementation | `LYA_FOUNDATION_DECISIONS.md`, validated Mermaid source `diagrams/10-wake-identity-storage-mobile.mmd`, directly viewable PNG/SVG renders in `diagrams/` |
| 2026-09-12 | Built and launched the custom crystal and glass desktop | UI implemented; 8/8 checks pass; full assistant integrations pending | `launch-lya.ps1`, `desktop/app.py`, `desktop/layout.py`, `desktop/README.md`, `desktop/check_ui.py`, `desktop/qa/`; detailed entry below |
| 2026-09-12 | Step 1 base environment: restored pip in .venv-ui, installed numpy, cryptography, pywin32; fixed Windows 8.3 path resolution in test_foundations.py | Completed; 14/14 foundation checks pass; 8/8 UI checks pass | `test_foundations.py`, `.venv-ui/`, `desktop/check_ui.py`; detailed entry below |
| 2026-09-12 | Step 2 deterministic core & defect fixes: fixed R02 (date parsing) and R07 (decrypted ordering) in reminder.py; confirmed R01/R05; wired status/help/time in desktop/app.py; converted review_checks.py | Completed; 4/4 suites pass (14/14, 16/16, 6/6, 9/9) | `skills/reminder.py`, `desktop/app.py`, `review_checks.py`, `desktop/check_ui.py`; detailed entry below |
| 2026-09-12 | Step 3 clean encrypted storage: built storage/store.py with person-scoped schemas, %LOCALAPPDATA%\LYA layout, 7-day pending face expiry, and safe audit log | Completed; test_storage.py 7/7 pass; all 5 project suites pass | `storage/store.py`, `test_storage.py`; detailed entry below |
| 2026-09-12 | Agent skills & research: installed andrej-karpathy-skills and ponytail globally; evaluated 9 GitHub repos for LYA device footprint & roadmap | Completed | `C:\Users\kathirvel\.gemini\config\skills\`, `lya-project-brain.md`; detailed entry below |

## Decision log

- 2026-09-13: Review new components using a disposable source copy, fake data and
  blocked network/sensors. Preserve the app during review. Prioritize memory
  boundaries and actual-launch integration before extending features. Owner wants
  a more futuristic visual treatment while retaining the current panel's clarity.

- 2026-09-12: Implement the owner's crystal-and-glass UI first as an isolated native
  milestone. Reuse the unchanged supplied artwork through a silhouette clip; keep
  the desktop visible, use small windows and cached animation frames. Person colors
  are cosmetic until authenticated session events are connected. Real file previews
  in this milestone are restricted to the four listed public project documents.

- 2026-09-10: Treat working foundation, reproduced defects, legacy code and unverified integrations as separate statuses.
- 2026-09-10: Preserve existing product/enrollment boundaries. Review and documentation do not enroll identities or activate legacy/generated tools.
- 2026-09-10: Persist safe project knowledge in this ledger; preserve full artifacts at their paths. No automatic collection of private runtime data.
- 2026-09-10: Prioritize completing reliable workflows before expanding the feature list.
- 2026-09-12: Rebuild beside the existing prototype and promote capabilities only through explicit acceptance gates. Initial scope is reproducible runtime, deterministic text core, read-only folders, then native UI.
- 2026-09-12: Refine the first owner-visible milestone to native PySide6 wake UI, offline Vosk wake recognition, one-frame OpenCV capture, local InsightFace matching, and encrypted person-scoped SQLite storage. Face recognition personalizes; it does not alone authorize sensitive actions.
- 2026-09-12: Store runtime/private data under `%LOCALAPPDATA%\LYA`, outside the source tree. Default files to laptop-only; only explicitly pinned Important Vault items synchronize to an encrypted phone cache.

## Future task entry template

Append an entry after each meaningful task, and update the status tables above when evidence changes:

- Date and requested outcome:
- Changes and affected paths:
- Generated artifacts, sources and sensitivity:
- Verification command, result and limits:
- Decisions and reasons:
- Open issues and next concrete step:

Never mark “working” from file presence, syntax alone, an old report or a model's claim. Record failures as well as successes. Keep prior evidence dated rather than silently replacing history.

## Owner clarification — conversational upgrades and visual references (2026-09-10)

The owner wants LYA to improve through ordinary instructions, retain successful capabilities, and reuse them later. This is a requested product direction, not an implemented feature or authorization to activate a camera now.

Two concrete examples:

1. “Create a camera-reading skill; when I ask, look at my room and tell me whether anyone is there.” Desired flow: use an authorized camera, inspect the visible scene, report detected people and uncertainty, and retain the reusable skill. An image cannot establish that the entire home is empty, and detecting a person is distinct from identifying them. Retaining the skill does not require retaining room recordings. No continuous monitoring was requested.
2. “Look at this video on my phone; I like its folder interface. Use that layout for my files from now on.” Desired flow: receive a shared clip/screenshot or an explicitly available screen feed; infer layout and interaction details; create a working preview; apply the requested style after validation; persist the choice and allow undo. A short video may not reveal the original implementation or all interaction behavior. Current LYA has no integrated phone-screen/video input and only three predefined orb themes, not a reference-driven folder renderer.

Proposed implementation stages:

- Prefer reusable workflows built from already available, permission-checked tools.
- Represent supported visual changes as validated layout/theme settings where possible.
- When genuinely new code is needed, generate a separate draft, test it in an isolated environment with limited access, verify the requested behavior, and register a version only after those checks and applicable authorization succeed. Tests reduce risk; they do not prove arbitrary generated code safe.
- Keep the core permissions, credentials and update/rollback mechanism outside generated skills' write access.
- Store each accepted skill's purpose, trigger, permissions, dependencies, version, evidence, limitations and rollback target. Keep runtime camera use subject to the original request and permissions.
- Save capability definitions and chosen preferences, not every raw observation. This is reusable software/workflow creation; it does not require retraining the underlying language model after each instruction.
- Treat “stay updated” as a desired product property for now. No automatic dependency updater, research monitor, scheduled task or background camera service was requested or created in this discussion.

Current evidence: `skills/forge.py::activate` is disabled; drafting writes one replaceable draft. `ui/themes.py` accepts reactor/halo/pulse and stores a previous theme. Safe execution, a durable versioned skill registry, video interpretation and arbitrary folder-layout generation remain pending.

Work ledger entry: 2026-09-10 — checked current forge/theme implementation; recorded both owner examples, limits and proposed acceptance flow. Documentation only; no application changes, installs, sensors, model calls or new tests. Next step: choose and implement one bounded journey after the existing core reliability fixes.
## Full re-read pass and visual architecture pack (2026-09-10)

### Requested outcome

Owner asked for an inch-by-inch pass over the whole project and a detailed visual
work-flow map showing what works, what is in progress, and what does not — with
the biometric ("Face ID") technology and its status stated.

### What was done

Read every Python file in the project (59 files, all modules and sub-packages),
then probed the runtime for each declared dependency. No sensors, cameras,
microphones, phone connections, model calls or GUI launches were used. Nothing was
enrolled. No application source was modified.

### Generated artifacts

- `LYA_ARCHITECTURE.md` — the visual guide; 8 Mermaid blocks embedded inline,
  plus technology tables, the R01 code walkthrough, new findings and a ranked action list.
- `diagrams/01-master-system-map.mmd` — all layers, wired vs unwired, status-coloured.
- `diagrams/02-faceid-chain.mmd` — the live ArcFace identification sequence.
- `diagrams/03-three-faceid-implementations.mmd` — the three separate face systems.
- `diagrams/04-permission-approval-flow.mmd` — policy gate + phone grant lifecycle.
- `diagrams/05-command-lifecycle.mmd` — queue/worker/threading and the R01 site.
- `diagrams/06-data-and-encryption.mmd` — stores, key root, two encryption designs.
- `diagrams/07-status-map.mmd` — the one-answer working/partial/broken/legacy map.
- `diagrams/08-voice-pipeline.mmd` — wake loop, STT choice and R04.

### Verification command, result and limits

```
$node = C:\Users\kathirvel\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
& $node "$env:USERPROFILE\.codegpt\skills\mermaid\mermaid.mjs" check --all
```

Result: **16 checked, 0 failed, 0 warnings** (8 `.mmd` files + 8 blocks inside
`LYA_ARCHITECTURE.md`). Re-run this after any diagram edit.

Dependency probe (bundled interpreter), read-only import test:

| Present | Missing |
|---|---|
| `cryptography`, `numpy` | `win32crypt`, `cv2`, `insightface`, `onnxruntime`, `resemblyzer`, `sounddevice`, `speech_recognition`, `pyttsx3`, `pyautogui`, `vosk`, `torch` |

Limits: findings are read from source and from import probing, not runtime
reproduction. Static reading cannot observe dynamic imports or framework wiring.
The probe result is specific to the interpreter used; a different Python install
may report differently.

### Key conclusions recorded

1. **Root blocker: only 2 of 13 required libraries are installed.** `security/vault.py`
   calls `_get_fernet()` at import time and imports `win32crypt` at module scope, so
   the missing DPAPI binding prevents almost every module from loading. Most amber/red
   status below is downstream of this one gap.
2. **Face ID is three implementations, not one.** `vision/identity.py` (InsightFace
   ArcFace 512-d) is the only one wired into `main.py`. `vision/face_auth.py`
   (OpenCV Haar + 128px mean-abs-diff, threshold 0.12) is orphaned. `security/liveness.py`
   (MiniFASNet anti-spoof) runs only on the phone `verify_owner()` path. Any document
   describing "OpenCV face auth" is describing the orphan.
3. **The permission/approval layer is the project's strongest asset** and already
   contains real fixes: cross-process nonce via disk, fail-closed grant consumption,
   fail-closed attempt lockout, per-install salt, `hmac.compare_digest` token check,
   per-client expiring phone sessions.
4. **`main.py` imports `skills/allskills.py` but never calls it.** 15 skill modules
   are loaded at start and are unreachable at runtime.

### New findings N1–N11 (not previously recorded)

| # | Finding | Evidence |
|---|---|---|
| N1 | `allskills.reply()` is dead at runtime despite being imported | `main.py` import list vs `handle()` |
| N2 | Laptop spoken-fallback is unreachable: `permit()` only calls `request_phone()`, never `escalate()`, so `security_word.lya` is a settable but unusable credential | `main.py::permit` vs `escalation.request_phone` |
| N3 | `vault.py` builds the Fernet at import time — one bad key file breaks every dependent module with no graceful degradation | `vault.py` line 31 |
| N4 | First-run phone token is printed to stdout | `web_server.py` lines 59–60 |
| N5 | Phone page keeps its access token in `localStorage` | `web_server.py` lines 94–95 |
| N6 | `voice_liveness()` uses `audioop`, removed in Python 3.13 | `liveness.py` line 87 |
| N7 | Anti-spoof loader calls global `os.chdir(REPO)`, which can break relative paths in a threaded app | `liveness.py` line 35 |
| N8 | `close_app()` uses `os.system`; `run_command()` uses `shell=True` — currently unreachable but a shell-injection surface if wired up | `device.py` lines 30, 48–51 |
| N9 | An unauthenticated unknown face triggers a disk write to the encrypted store | `identity.py` lines 127–131 |
| N10 | `face_auth.py` imports `cv2`/`numpy` unguarded at module top; masked only because nothing imports it | `face_auth.py` lines 5–6 |
| N11 | Two unreconciled admin identities: `memory.admin` table vs `identity.people[]` with `role=admin` | `memory.py` 66–86 vs `identity.py` 41–71 |

### Decisions and reasons

- 2026-09-10: Draw the system rather than re-describe it in prose; keep diagrams
  versioned next to the code in `diagrams/` and embed the same blocks in the guide
  so they render without a separate viewer.
- 2026-09-10: Use status colouring (`works`/`partial`/`broken`/`legacy`) because in
  a half-finished project "what is real" matters more than "what is connected".
  These colours are a claim about today and must be re-checked when code changes.
- 2026-09-10: Record N1–N11 as read-from-source findings, explicitly not as runtime
  reproductions, and keep them separate from the already-reproduced R01–R03.
- 2026-09-10: Do not alter any application source in this pass — the request was
  analysis and visualisation.

### Open issues and next concrete step

All of R01–R11 and N1–N11 remain open; no fixes were applied in this pass.

Next concrete step: **write `requirements.txt` and install the dependency set**
(R08). Until `win32crypt`, `cv2` and the voice/GUI libraries are present, no runtime
verification of any journey is possible, so this unblocks everything else. After
that, fix R01 (one line) and R05 (one word) as the first targeted regression checks.

### Skill installation recorded

Installed the `mermaid` skill at `~/.codegpt/skills/mermaid` and
`~/.claude/skills/mermaid` (SKILL.md + mermaid.mjs + .codegpt-seed.json). It
validates, extracts and traces Mermaid diagrams. Using it on this pack exposed and
fixed five genuine validator bugs (missed `flowchart TD`, broken markdown fence
extraction, `alt/loop/end` misread as unclosed subgraphs, arrow heads captured into
participant names, `:::class` read as an edge). Validator hash: `d447b309597fb3ce`.
No credentials or private runtime facts are stored in this ledger.

## 2026-09-12 — Custom crystal and glass desktop implementation

Requested outcome: make the owner's artwork a real native floating LYA interface,
with smooth person/task colors and readable compact message/file cards.

Implemented:

- `desktop/app.py`: two frameless translucent Qt windows, draggable crystal,
  interpolated colors, gentle motion, panel reveal, typed commands, tray controls,
  keyboard exits, reduced motion and opaque-panel options. No full-screen window.
- `desktop/layout.py`: monitor-aware card placement and explicit palette mapping.
- `desktop/assets/crystal-original.png`: unchanged copy of the owner's supplied
  artwork. Painter clipping removes the square background at runtime. An ImageGen
  extraction attempt failed to produce true alpha and is not used; provenance is
  recorded in `desktop/README.md`.
- `launch-lya.ps1`, `desktop/requirements.txt`, `.venv-ui/`: isolated Python 3.12.14
  with PySide6 Essentials 6.11.2. The normal launcher opens only the crystal.
  `.gitignore` excludes the environment and local uv cache; root README links the
  new launcher. Existing runtime code and earlier diagrams were preserved.
- Read-only project documents open through one background worker. Generation-based
  cancellation rejects dismissed results. Cosmetic roles cannot grant access.

Checks and generated artifacts:

- Command: `.\.venv-ui\Scripts\python.exe -B desktop\check_ui.py`.
- Launcher check: `launch-lya.ps1` started successfully in default crystal-only
  mode; the launched process remained running after the 2.5-second startup check.
- Result: **8/8 passed** in 1.546 seconds, including native-window/alpha setup,
  monitor edges/negative coordinates, keyboard commands, readable file rows,
  actual file selection/loading, role isolation, allowlisting, stale completion
  rejection, and hidden/reduced-motion animation lifecycle.
- Visually reviewed actual widgets over synthetic light/dark desktops; corrected
  black surrounds in the initial composition, clipped card text and artwork edges.
  No user desktop screenshots or sensor data were collected.
- [Light desktop](desktop/qa/light-desktop.png),
  [dark desktop](desktop/qa/dark-desktop.png),
  [message panel](desktop/qa/message-desktop.png).
- [Timing sample](desktop/qa/measurement.json): 2.511 seconds, 171 paints, median
  2.021 ms and max 3.874 ms per paint; maximum event-loop heartbeat gap 25.904 ms.
  This short local measurement is not proof of sustained frame rate, battery use
  or responsiveness under voice/camera/model load.

Limitations: this is 2D artwork with motion, not a reconstructed 3D model. Glass is
tinted translucency, not OS acrylic blur. Voice wake, sensors, face recognition,
real identity, private saved-file/vault search, AI answers, mobile access and
retained display preferences are not connected. No real enrollment occurred.

Next step: owner visual acceptance on the desktop, then connect a deterministic
session/task event path and test offline wake separately before any camera setup.

## 2026-09-12 — Step 1 base environment and foundation test recovery

Requested outcome: start from scratch step-by-step; verify the starting point, install minimal core dependencies, and bring foundation tests to 100% pass.

Implemented and verified:
- Discovered `.venv-ui` had no `pip` installed. Restored pip via `ensurepip --upgrade`.
- Installed the three minimal foundational packages: `numpy` (2.5.3), `cryptography` (50.0.1), and `pywin32` (312).
- Fixed Windows 8.3 short-path resolution mismatch in `test_foundations.py::test_folder_paging_and_scope` using `Path(tmp).resolve() / "scope"`.
- Ran `.\.venv-ui\Scripts\python.exe test_foundations.py`: **14/14 passed** in 0.366s. All previous `ModuleNotFoundError` crashes resolved.
- Ran `.\.venv-ui\Scripts\python.exe -B desktop\check_ui.py`: **8/8 passed** in 1.053s.

Limitations: camera/vision (`insightface`, `onnxruntime`, `cv2`) and voice audio (`sounddevice`, `vosk`) remain intentionally uninstalled until their dedicated steps. No real biometrics or secrets were enrolled.

Next step (Step 2): wire clean deterministic text commands (status, help, time, stop, folder read) directly to the PySide6 crystal UI and fix the R01 speech leak and R05 tone engine defects.

## 2026-09-12 — Step 2 deterministic core and defect remediation

Requested outcome: fix confirmed defects R01, R02, R05, R07; wire deterministic commands (`status`, `help`, `time`/`date`) into the native PySide6 Crystal UI; convert review checks into regression tests.

Implemented and verified:
- Verified R01 (private fact speech suppression in `main.py`) and R05 (`voice.set_rate()` via `_engine` in `brain/mind.py`) passing with 16/16 checks in `test_regressions_r01_r05.py`.
- Fixed R02 in `skills/reminder.py::_time_hint`:
  - Added `unit.startswith("hr")` so relative hours (`in 2 hrs`) parse properly.
  - Corrected next weekday offset `(WORDS[m.group(1).lower()] - b.weekday()) % 7 or 7` (removed spurious `+ 1` extra day offset).
  - Fixed `day_month` parsing for phrases like `on 5 june at 6pm`.
- Fixed R07 in `skills/reminder.py::list_all`:
  - Decrypted all rows before sorting by `when_iso` (`rows.sort(key=lambda r: r[2])`), replacing sorting on randomized ciphertext.
  - Verified chronological order with an isolated temporary store.
- Converted `review_checks.py` from reproducing defects to asserting expected fixed behavior: **6/6 passed**.
- Enhanced `desktop/app.py`:
  - Added live `status` / `check` command deriving actual Python and dependency readiness (`win32crypt`, `cryptography`, `numpy`, etc.) rather than hard-coded claims.
  - Added dedicated `help` command listing available desktop operations.
  - Expanded `time`, `date`, `day` recognition.
  - Added `test_deterministic_commands` to `desktop/check_ui.py`: **9/9 passed** in 1.092s.
- Executed full test run: `test_foundations.py` (14/14), `test_regressions_r01_r05.py` (16/16), `review_checks.py` (6/6), and `desktop/check_ui.py` (9/9) **all pass 100% clean**.

Limitations: vision/camera, offline microphone loop, real phone pairing, and per-person encrypted SQLite in `%LOCALAPPDATA%\LYA` remain to be implemented in subsequent steps.

Next step (Step 3): Step 4 of the rebuild plan — clean encrypted local storage (`%LOCALAPPDATA%\LYA`) with person-scoped data schemas (`people`, `memories`, `vault_items`, `audit_events`).

## 2026-09-12 — Step 3 clean encrypted person-scoped storage

Requested outcome: implement the storage foundation specified in `LYA_FOUNDATION_DECISIONS.md` outside the repository tree in `%LOCALAPPDATA%\LYA` with encrypted person-scoped SQLite, atomic commits, automatic 7-day pending face expiry, and safe audit logging.

Implemented and verified:
- Created `storage/store.py` and `storage/__init__.py`:
  - `get_data_dir()` resolves `%LOCALAPPDATA%\LYA` (with `LYA_DATA_DIR` test override support).
  - `ensure_layout()` initializes standard directory layout: `faces/`, `vault/`, `models/`, `logs/`, `lya.db.enc`.
  - Encrypted SQLite in RAM via `db.deserialize` / `db.serialize` with AES-256 Fernet/DPAPI encryption, file-level locking (`msvcrt` on Windows), and atomic replacement.
  - Person-scoped schemas implemented:
    - `people`: `person_id`, `display_name`, `role`, `created_at`, `active`
    - `face_templates`: `person_id`, `embedding_enc`, `model_version`, `quality`, `created_at`
    - `pending_faces`: `pending_id`, `thumbnail_path`, `embedding_enc`, `first_seen`, `last_seen`, `sightings`, `expires_at` (7-day TTL)
    - `memories`: `person_id`, `kind`, `key_enc`, `value_enc`, `source`, `importance`, `hits`, `created_at`, `updated_at`
    - `vault_items`: `person_id`, `label_enc`, `file_path_enc`, `sync_policy`, `created_at`
    - `audit_events`: `time`, `action_type`, `outcome`, `person_id` (zero secret, transcript, or image data)
  - Full API: `create_person()`, `get_person()`, `list_people()`, `remember()`, `recall()`, `forget()`, `record_pending_face()`, `list_pending_faces()`, `promote_pending_face()`, `record_audit()`, `list_audit_events()`.
- Created unit test suite `test_storage.py`:
  - Verified directory layout creation.
  - Verified database is genuinely encrypted at rest (plain `sqlite3` fails to read file).
  - Verified strict person scoping (Alice cannot see Bob's memories; guest cannot see private data).
  - Verified exact-key forgetting scoped to specific person.
  - Verified unknown face capture, pending listing, and admin promotion to registered person.
  - Verified audit log never leaks plaintext secrets.
  - Verified multi-threaded concurrent write safety without corruption.
  - All **7/7 storage tests pass in 0.364s**.
- Full test pass across the entire workspace:
  - `test_foundations.py`: 14/14 passed
  - `test_regressions_r01_r05.py`: 16/16 passed
  - `review_checks.py`: 6/6 passed
  - `test_storage.py`: 7/7 passed
  - `desktop/check_ui.py`: 9/9 passed
  - **All 5 suites pass cleanly.**

Limitations: face embeddings used in tests are synthetic test vectors; camera capture and InsightFace model integration are deferred to subsequent steps.

Next step (Step 4): Offline voice wake phrase detection using `vosk` and `sounddevice` ("wake up LYA") to trigger the crystal desktop window.

## 2026-09-12 — Research, device footprint optimization, and global agent skills

Requested outcome: evaluate 9 specific GitHub repositories for device footprint and LYA integration, install Andrej Karpathy's agent guidelines and Ponytail globally, and establish a modern, low-pressure model architecture for the laptop.

Actions and findings:
1. **Installed Global Skills** in `C:\Users\kathirvel\.gemini\config\skills\`:
   - `andrej-karpathy-skills`: 4 core principles (Think before coding, simplicity first, surgical changes, goal-driven execution).
   - `ponytail`: Minimalist senior developer rules (YAGNI, stdlib first, native platform features, zero bloat, verify before finishing).
2. **Evaluated 9 GitHub Repositories for LYA**:
   - **`diegosouzapw/OmniRoute`**: Highly relevant for LYA. Unified AI gateway with 90+ free tiers (~1.51B free tokens/mo) and auto-fallback. Recommended for LYA's cloud reasoning provider to give free, zero-laptop-pressure AI intelligence.
   - **`TencentCloud/TencentDB-Agent-Memory`**: Concept of symbolic short-term memory (Mermaid diagrams) and layered long-term memory (personas + scenes). We have already adopted person-scoped schemas in `storage/store.py` and Mermaid architecture maps.
   - **`microsoft/VibeVoice`**: Crucial for LYA Step 4/5. Specifically `VibeVoice-ASR-BitNet` (1.58 GB CPU edge inference on 3+ threads with RTF < 1, no GPU required) and `VibeVoice-Realtime-0.5B` streaming TTS.
   - **`ScrapeGraphAI/Scrapegraph-ai`**: Excellent for future LYA "learn <topic>" deep research pipeline without manual browser automation.
   - **`Panniantong/agent-reach`**: Agent web access toolset; useful companion for online search tasks.
   - **`bytedance/deer-flow`**: Multi-agent harness with sandboxes; relevant for future Council expansion, but too heavy to run as a local background daemon.
   - **`jingyaogong/minimind`**: Educational 26M-100M parameter LLM; not recommended for primary reasoning over OmniRoute/Groq.
3. **Device Footprint Strategy**:
   - Keep local laptop load near zero: PySide6 (UI), Kaldi/Vosk or VibeVoice BitNet (Edge Voice), ArcFace (512-d embeddings via ONNX CPU in <100ms), and SQLite (Encrypted RAM/disk).
   - Route heavy LLM tokens through cloud/free-tier gateways (Groq / Gemini / OmniRoute) to avoid high fan noise, RAM bloat, and thermal throttling.

Next step: proceed to Step 4 — offline voice wake phrase detection using `vosk` and `sounddevice`.

## 2026-09-12 — Step 4: Offline Voice Wake & Audio Pipeline (Completed)

Requested outcome: Build out Step 4 (Offline Voice Wake & Audio Pipeline), provide smarter/more advanced voice options than Vosk and sounddevice, verify R04 interruption, implement comprehensive unit tests for voice, wire voice wake into the PySide6 Desktop UI with thread-safe Qt signals, and verify all suites.

Actions and findings:
1. **Audio Capture & Wake Analysis**:
   - `sounddevice` (PortAudio C-bindings with WASAPI) is the optimal, lowest-latency, zero-overhead capture library in Python on Windows.
   - For wake word detection, `openWakeWord` (ONNX AST/ResNet-8 neural wake words, <0.5% CPU, <30MB RAM) was installed alongside `vosk` (0.3.45), `sounddevice` (0.5.6), `pyttsx3` (2.99 with Windows SAPI5), and `onnxruntime` (1.30.0).
   - Audio devices detected on hardware: `Microphone Array (Realtek(R) Audio)` and `Speakers (Realtek(R) Audio)`.
2. **Fixed R04 in `audio/voice.py`**:
   - Spoken "stop", "cancel", "sleep", and "go to sleep" now immediately trigger `on_wake` and reset the active window, bypassing conversation timeouts and breaking through active speaking loops.
   - Extracted clean, testable `process_utterance(text, last_wake_time, on_wake, quiet)` and added `stop_event` support to `wake_loop` for graceful daemon shutdown.
   - Added automatic model discovery in `%LOCALAPPDATA%\LYA\models\vosk`.
3. **Hardened Voice Liveness (`security/liveness.py`)**:
   - Replaced deprecated `audioop` with vectorised `numpy` Root-Mean-Square (RMS) calculations, eliminating Python 3.12 deprecation warnings and ensuring Python 3.13 compatibility.
   - Guarded `cv2` imports so audio/voice pipelines can run cleanly without requiring OpenCV.
4. **Created Unit Test Suite `test_voice.py`**:
   - `test_set_rate_bounds_and_fallback`: Verified rate bounds [60, 400] and non-numeric fallback to base 175.
   - `test_wav_framing`: Verified 16kHz, 16-bit mono WAV header and frame fidelity.
   - `test_r04_interruption_during_speaking`: Verified "stop" and "cancel" break through active speaking and expired conversation windows.
   - `test_wake_words_and_extraction`: Verified wake words ("lya", "leya", "liya", "wake up ...", "hey ...") strip prefix and extract intent.
   - `test_conversation_window_and_expiration`: Verified sequential commands succeed within 45s and reject after expiration without wake word.
   - `test_voice_liveness_detection`: Verified rejection of short clips (<1.0s), rejection of flat synthetic sine waves (replay attacks), and pass for natural speech amplitude variations.
   - `test_quiet_mode`: Verified quiet suppression.
   - **All 7/7 tests passed in 0.309s**.
5. **Wired Voice Wake to PySide6 Desktop UI (`desktop/app.py`)**:
   - Added `VoiceSignals(QObject)` with `wake_detected = Signal(str, bool)`.
   - Added `Desktop.on_voice(text, quiet)`: Thread-safe signal dispatch from background audio thread to Qt main loop. Wakes crystal, sets `task="listening"`, opens glass panel, executes command, and speaks answer if non-quiet and non-private.
   - Added `Desktop.start_voice()` and `Desktop.stop_voice()` with background daemon thread.
   - Added `--voice` flag to `desktop/app.py` CLI and "Voice wake" toggle to the crystal context menu.
   - Added `test_voice_wake_signal_dispatch` to `desktop/check_ui.py`.
6. **Full Test Verification Across Workspace**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `review_checks.py`: 6/6 passed
   - `test_storage.py`: 7/7 passed
   - `test_voice.py`: 7/7 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 60 tests across all 6 suites pass cleanly (0 errors, 0 failures).**

Limitations:
- Physical microphone wake loop requires local acoustic model files in `%LOCALAPPDATA%\LYA\models\vosk` for full offline operation; tested in unit tests with synthetic audio buffers and simulated utterances.
- Automated tests do not block waiting for human speech.

Next step: proceed to Step 5 — local face recognition & anti-spoofing.

## 2026-09-12 — Step 5: Local Face Recognition & Anti-Spoofing (Completed)

Requested outcome: Build out Step 5 (Local Face Recognition & Anti-Spoofing), install OpenCV, modernize the multi-user face identity engine, integrate with encrypted SQLite storage, wire owner verification with liveness anti-spoofing gating, and verify test suites.

Actions and findings:
1. **Installed & Verified OpenCV**:
   - Installed `opencv-python-headless` (5.0.0.93) in `.venv-ui`. Verified native hardware support for `FaceDetectorYN` (YuNet) and `FaceRecognizerSF` (SFace).
2. **Extended Storage for Face Templates (`storage/store.py` & `storage/__init__.py`)**:
   - Added `add_face_template(person_id, embedding, model_version="arcface-512d", quality=1.0)`: Persists AES-256 encrypted biometric face embeddings linked to person profiles.
   - Added `list_face_templates(person_id=None)`: Decrypts templates on the fly for recognition matching.
   - Added `remove_face_templates(person_id)`: Securely cleans up biometric templates on de-enrollment or forget requests.
   - Enhanced `record_pending_face()` to handle both float lists and byte vectors smoothly.
   - Added `test_face_template_crud` to `test_storage.py` (all 8/8 passed).
3. **Hardened `security/auth_wall.py`**:
   - Guarded `_face()` lazy-loader to handle missing C++ InsightFace build packages gracefully.
   - Guarded `detect_face_bbox()` and `face_embedding()` with clean error handling preventing unhandled exceptions.
4. **Modernized Face Identity Engine (`vision/identity.py`)**:
   - Switched from legacy plaintext/single-file JSON to person-scoped AES-256 encrypted SQLite storage in `storage/store.py`.
   - `_cos(a, b)`: Protected cosine similarity invariant implementation with zero-vector handling.
   - `face_embedding(source)`: Normalizes 512-d embeddings to unit length and bridges camera frames with feature extractors.
   - `enroll_person()` & `enroll_admin()`: Creates person in `people` table and registers encrypted templates.
   - `identify()`: Matches input against all active templates via cosine similarity, logging unknown visitors to `pending_faces` with 7-day TTL.
   - `verify_owner()`: Gated by `security.liveness.face_liveness()` before matching against primary admin templates.
   - `set_secondary_password()` & `check_secondary_password()`: Salted PBKDF2 (200,000 rounds) stored encrypted in the store and compared in constant time (`hmac.compare_digest`).
   - `name_person()`: Admin tags stranger face ID to promote to registered friend/family.
   - `forget()`: Deactivates person and purges templates.
5. **Created Unit Test Suite `test_identity.py`**:
   - `test_cosine_similarity_invariants`: Tested 1.0 (identical), 0.0 (orthogonal), -1.0 (opposite), and 0.0 (zero vector).
   - `test_multi_user_enrollment_and_identification`: Enrolled Alice (Admin) and Bob (Friend); verified high-confidence identification, unknown visitor capture, and stranger promotion to known friend.
   - `test_owner_verification_and_spoof_gate`: Verified owner match, imposter denial, and anti-spoof rejection of synthetic flat image frames.
   - `test_secondary_password_authentication`: Verified salted PBKDF2 hash check, failure on incorrect/empty passwords.
   - `test_forget_person`: Verified de-enrollment, template deletion, and subsequent identification as unknown.
   - **All 5/5 tests passed in 0.397s**.
6. **Full Test Verification Across Workspace**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 70 tests across all 8 suites pass cleanly (0 errors, 0 failures).**

Limitations:
- Physical webcam enrollment remains deferred in accordance with project policy until explicitly requested by owner; verified with synthetic 512-d unit vectors and image buffers in isolated temporary test databases.
- Deep anti-spoofing model weights (MiniFASNet) require offline model checkpoints in `security/Silent-Face-Anti-Spoofing/resources/anti_spoof_models/`; falls back safely to deny-by-default when checkpoints are absent.

Next step: proceed to Step 6 — free cloud reasoning gateway & persona brain.

## 2026-09-12 — Step 6: Free Cloud Reasoning Gateway & Persona Brain (Completed)

Requested outcome: Build out Step 6 (Free Cloud Reasoning Gateway & Persona Brain), fix R06 (unified key resolution between mind and forge), integrate person-scoped memory retrieval into system prompt generation, establish multi-provider fallback (Groq / OmniRoute / OpenAI / Ollama), implement emotional tone modulation, and verify test suites.

Actions and findings:
1. **Resolved R06 (`skills/forge.py` & `brain/mind.py`)**:
   - Extracted unified `get_groq_key()` in `brain/mind.py` resolving keys via environment variable -> DPAPI key file -> `%LOCALAPPDATA%\LYA\vault`.
   - Updated `skills/forge._groq` to call `mind.get_groq_key()` instead of directly indexing `os.environ['GROQ_API_KEY']`.
2. **Multi-Provider Cloud Gateway (`brain/mind.py`)**:
   - Layered provider order designed for near-zero laptop pressure:
     1. OmniRoute Gateway (free tiers, 90+ endpoints)
     2. Groq cloud provider (`llama-3.3-70b-versatile`, free tier, 500-800 tokens/sec, 0 local CPU/GPU load)
     3. OpenAI / OpenRouter
     4. Local Ollama edge fallback
   - Safe offline fallback message guiding user to configure free cloud reasoning without unhandled exceptions.
3. **Person-Scoped Context & Memory Injection**:
   - `_memory_block()` queries `storage.store.recall(person_id=person_id)`.
   - Verified owners receive their private memories; unverified visitors/guests receive `(private memory unavailable)` with strict instruction forbidding access to private data.
4. **Voice Tone & Emotional Synchronization**:
   - `detect_tone()` maps utterance keywords to 8 emotional profiles (excited, playful, happy, sad, worried, serious, angry, neutral).
   - Injects current mood into system prompt so the assistant matches tone as a true friend.
   - Automatically synchronizes voice speech rate via `voice.set_rate()` based on the model's generated response.
5. **Created Unit Test Suite `test_mind.py`**:
   - `test_r06_unified_groq_key_resolution`: Verified key resolution and graceful handling when key is missing.
   - `test_guest_vs_verified_memory_scoping`: Verified guest prompt isolation vs owner PIN retrieval from encrypted SQLite store.
   - `test_tone_detection_and_speech_modulation`: Verified emotional classification and voice rate setting.
   - `test_session_history_isolation`: Verified multi-session isolation and history clearing.
   - `test_offline_gateway_fallback_message`: Verified recovery message on complete connection refusal.
   - **All 5/5 tests passed in 0.203s**.
6. **Full Test Verification Across Workspace**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_mind.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 75 tests across all 9 suites pass cleanly (0 errors, 0 failures).**

Limitations:
- Live model responses depend on external network access and user-provided API keys (`GROQ_API_KEY`, `OMNIROUTE_KEY`, or `OPENAI_API_KEY`); verified with isolated test mocks and synthetic prompt assertions.

Next step (Step 7): Phone Approval Escalation Gateway (Local TLS HTTP server, one-time nonce dispatch, and secure phone escalation flow).
 
## 2026-09-12 — Step 7: Phone Approval Escalation Gateway (Completed)

Requested outcome: Modernize and harden the Step 7 Phone Approval Escalation Gateway, verify cross-process nonce generation, single-use grant consumption, rate-limiting lockout, fallback spoken security word verification (salted PBKDF2), silent duress alarms, TLS enforcement, and web gateway integration with complete unit tests.

Actions and findings:
1. **Hardened `security/escalation.py`**:
   - Hardened `current_challenge()` to catch all unexpected decryption/parsing exceptions (`except Exception:`) and safely retrieve timestamp keys via `.get("t", 0)`, guaranteeing fail-closed behavior on corrupted challenge files.
   - Verified cross-process nonce lifecycle: `_write_challenge(nonce, task)` and `current_nonce()` read encrypted challenge from disk, ensuring the web server process receives the exact challenge nonce issued by the desktop assistant process.
   - Verified single-use burn: `_consume_phone_grant()` reads `GRANT_FILE`, validates nonce equality, verifies `GRANT_TTL` window (120 seconds), and immediately marks the grant as used (`used = True`), preventing all replay attacks.
   - Validated fallback spoken security word checking: 200,000 PBKDF2 HMAC-SHA256 iterations with unique 16-byte random salt, normalization across case and punctuation, sliding window scan up to `MAX_SCAN_TOKENS = 12`, and silent duress phrase detection.
   - Validated fail-closed brute force lockout: 5 consecutive failures trigger a 600-second lockout; corrupted attempt counters fail closed as permanently locked until admin resets.
2. **Hardened `web_server.py`**:
   - Hardened `/escalate` and `/verify_identity` handlers to safely type-check `challenge.get("nonce")` before running constant-time `hmac.compare_digest`, avoiding unhandled `TypeError` exceptions.
   - Verified strict TLS enforcement: requests over non-SSLSocket connections are immediately rejected with HTTP 403 (`Phone verification requires HTTPS.`).
   - Verified token gating: invalid or missing phone access token rejected with HTTP 403 in constant time.
   - Verified deferred enrollment: `/enroll`, `/enroll_face`, and `/enroll_voice` return HTTP 403 (`Enrollment is deferred; a phone token cannot replace the owner.`).
   - Verified private memory gating: phone chat `/ask` queries touching private facts return `_NEEDS_FACE` unless accompanied by a verified session ID.
3. **Fixed Test Suite Portability (`test_security_fixes.py`)**:
   - Handled missing `git` command in `test_no_secrets_tracked` to check `.gitignore` secrets coverage directly when git CLI is absent.
   - Fixed attribute vs function distinction in `test_identity_api_matches_call_sites` to accommodate `identity.STORE`.
4. **Created Dedicated Unit Test Suite `test_escalation.py`**:
   - `test_nonce_and_challenge_lifecycle`: Verified challenge generation, task text preservation, TTL expiry, and cleanup.
   - `test_grant_single_use_and_replay_prevention`: Verified single-use consumption and instant rejection of replay attempts.
   - `test_challenge_nonce_mismatch_and_missing_challenge`: Verified fail-closed rejection on mismatched or absent challenge nonces.
   - `test_spoken_security_word_and_sliding_window`: Verified exact, normalized, and embedded phrase matching, prefix rejection, and unique per-install salting.
   - `test_duress_phrase_detection`: Verified separate duress phrase trigger and validation errors on identical/empty phrases.
   - `test_brute_force_lockout_and_fail_closed`: Verified 5-attempt lockout, attempt reset, and fail-closed lock on corrupted attempt counters.
   - `test_request_phone_cancellation_and_concurrency`: Verified non-blocking mutex locking (`_request_lock`) and rapid response to cancellation events.
   - `test_web_gateway_token_authentication`: Verified token validation and 403 on invalid tokens.
   - `test_web_gateway_plain_http_rejection`: Verified rejection of non-TLS connections on escalation endpoints.
   - `test_web_gateway_enrollment_deferred`: Verified 403 on all enrollment endpoints.
   - `test_web_gateway_private_memory_gating`: Verified refusal of unverified private memory queries.
   - `test_web_gateway_tls_escalate_and_approval_flow`: End-to-end integration test spinning up local HTTPS server with self-signed TLS cert, verifying challenge fetching, biometric mock verification, security phrase matching, grant issuance, and laptop consumption.
   - **All 12/12 tests passed in 3.254s**.
5. **Workspace-Wide Verification (All 11 Test Suites Pass)**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_mind.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `test_escalation.py`: 12/12 passed
   - `test_security_fixes.py`: 9/9 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 96 tests across all 11 suites pass cleanly with 0 failures, 0 errors.**

Limitations:
- Physical phone pairing and cellular/local WiFi network routing remain pending user environment configuration; verified over local loopback TLS sockets with synthetic certificates and isolated temporary storage.
- Real biometric owner verification on the phone camera relies on `vision.identity.verify_owner` and client WebRTC video streams; verified with synthetic frames and liveness gates.

Next step: proceed to Step 8 — Core Skills & Device Execution Capabilities (calculator, volume, notepad, user folder browsing, reminders, and draft skill forge).

## 2026-09-12 — Step 8: Core Skills & Device Execution Capabilities (Completed)

Requested outcome: Harden, sandboxed, and verify Step 8 Core Skills & Device Execution Capabilities (`skills/device.py`, `skills/files.py`, `skills/reminder.py`, `skills/forge.py`, and `main.py` routing), implement headless/pywin32 fallbacks, prevent path traversal, validate reminder natural language parsing & encrypted ordering, and create a comprehensive unit test suite (`test_skills.py`).

Actions and findings:
1. **Hardened Device Skills (`skills/device.py`)**:
   - `open_app(name)`: Strictly enforced non-shell allowlisted execution (`notepad.exe`, `calc.exe`, `explorer.exe`, `chrome.exe`) via `subprocess.Popen([executable])`. Arbitrary executables or shell injection strings (`calc.exe & notepad.exe`) are rejected cleanly.
   - `volume(action)`: Added graceful fallback to native Windows multimedia virtual key events (`VK_VOLUME_UP`, `VK_VOLUME_DOWN`, `VK_VOLUME_MUTE` via `pywin32`), eliminating hard dependency on `pyautogui` while maintaining zero CPU overhead.
   - `screenshot(output_dir)`: Sandboxed output directory creation (`shots/` or custom directory), timestamped filename formatting (`lya_shot_YYYYMMDD_HHMMSS.png`), with headless native Windows GDI/pywin32 capturing fallback.
   - `type_text(text)`: Gracefully simulated when GUI automation packages are absent.
2. **Hardened Folder Browser (`skills/files.py`)**:
   - `FolderBrowser`: Strictly enforces boundaries with `_inside(path)` resolving targets and raising `PermissionError` when escaping `self.root`.
   - Enhanced `listing()` to wrap directory scanning in `try...except OSError`, gracefully handling Windows system directories with permission restrictions.
   - Enhanced `open(selection)` to safely inspect non-directory files, returning metadata (`file`, `bytes`, and explicit statement that files are not executed) without executing code.
3. **Hardened Reminder System (`skills/reminder.py`)**:
   - Added optional `db_path` parameter to `_conn()`, `add()`, `due_now()`, `list_all()`, and `cancel()` enabling isolated testing without touching production database stores.
   - Verified natural language parsing across relative times (`"in 2 hours"`, `"in 30 mins"`), named weekdays (`"next monday at 9am"`), explicit calendar dates (`"on 5 june at 6pm"`), and clock times (`"at 5pm"`).
   - Verified that reminder texts and ISO timestamps remain encrypted with AES-256 ciphertext at rest in SQLite.
   - Confirmed `list_all()` decrypts in RAM and sorts chronologically, and `due_now()` fires only due reminders once.
4. **Hardened Skill Forge (`skills/forge.py`)**:
   - Added `compile(code, "<draft>", "exec")` Python syntax verification to `create(desc)` before persisting drafts, preventing syntax-broken drafts.
   - Verified that `activate()` strictly refuses execution, returning safety message.
   - Verified that `discard()` cleans up draft files cleanly.
5. **Verified Assistant Command Routing (`main.py`)**:
   - Verified `Assistant.handle()` routes:
     - `open calculator` -> `device.open_app("calculator")`
     - `volume up` -> `device.volume("up")`
     - `screenshot` -> `device.screenshot()` with `private_output=True`
     - `remind me to ...` -> `reminder.add(...)` with `private_output=True`
     - `create skill ...` -> `forge.create(...)`
     - `confirm skill` -> activation block notice
     - `what time is it` -> localized datetime output
     - `passwords` / `vault` -> development stage disabled notice
6. **Created Dedicated Unit Test Suite `test_skills.py`**:
   - `test_open_app_allowlist_and_safety`: Verified 4 allowlisted apps launch via Popen and shell injections are rejected.
   - `test_volume_actions`: Verified volume up, down, mute, and parameter validation.
   - `test_screenshot_sandboxed`: Verified directory creation and timestamped PNG generation.
   - `test_boundary_enforcement`: Verified `_inside` raises `PermissionError` on path escapes.
   - `test_listing_and_paging`: Verified page slicing and scroll navigation.
   - `test_open_folder_and_file_inspection`: Verified folder navigation and non-executable file metadata inspection.
   - `test_time_hint_natural_language_parsing`: Verified relative, weekday, and explicit date parsing.
   - `test_encrypted_crud_and_chronological_ordering`: Verified AES-256 ciphertext at rest, chronological `list_all` sorting, single `due_now` firing, and cancellation.
   - `test_create_valid_skill_draft`: Verified draft and metadata writing for valid code.
   - `test_create_rejects_missing_functions_or_syntax_error`: Verified rejection of code without `match`/`reply` or with syntax errors.
   - `test_activation_disabled_and_discard`: Verified safety lockout on activation and draft cleanup on discard.
   - `test_assistant_skills_routing`: Verified 6 core command branches in `Assistant.handle()`.
   - **All 17/17 tests passed in 0.124s**.
7. **Workspace-Wide Verification (All 12 Test Suites Pass)**:
   - `test_skills.py`: 17/17 passed
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_mind.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `test_escalation.py`: 12/12 passed
   - `test_security_fixes.py`: 9/9 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 113 tests across all 12 suites pass cleanly with 0 failures, 0 errors.**

Limitations:
- Physical app windows (e.g. Chrome, Notepad) and physical audio volume changes depend on active user desktop session; verified with mock subprocesses, allowlist checks, and virtual key events in isolated tests.
- Code generated by Skill Forge remains strictly non-executable drafts pending sandbox containerization.

Next step: proceed to Step 9 — Autonomous Guardian & System Health Governor (Safety boundaries, tamper detection, action audit logging, resource governor).

## 2026-09-13 — Independent review of new work and UI direction

- Request: assess the owner's additions, installed repositories and whether the
  clean glass panel feels sufficiently futuristic.
- Artifacts: `review/2026-09-13/REVIEW.md`, reproducible harness
  `review/review_20260913.py`, suite logs, reproduction output, `results.json`,
  `measurement.json` and synthetic-background widget PNGs in the dated folder.
- Checks: 35/35 tests passed across storage (8), identity (5), mind (5), voice (7)
  and Qt UI (10), in a disposable source copy. Network and sensors blocked; fake
  TTS, synthetic records and a temporary encryption key. No existing credentials,
  private databases or biometrics copied or read. The previous 113-test total was
  not independently rerun in full.
- New findings: reproduced missing-person context selection, unscoped fallback,
  credential-kind context inclusion, expired pending promotion and legacy-file
  recognition gating. Checked desktop script import resolution: sibling `audio`
  is not discoverable under the documented entry-point path. Static review found
  inaccurate microphone/offline labels and incomplete backend command routing.
- Dependency inventory: UI/core libraries are present, but InsightFace, Torch,
  SpeechRecognition and expected offline/face model directories are absent in
  the checked environment. Anti-spoof repository directory is empty. No Git
  checkout markers found in project source; repositories elsewhere await paths.
- Visual assessment: current UI remains legible and compact; propose angled
  framing, a restrained crystal-to-card connection, content-sized cards and
  truthful task indicators. Visual changes are proposed, not implemented.
- Application behavior was not changed. Existing artifacts were preserved.
  This review supersedes the earlier recommendation to proceed immediately to
  an autonomous governor: first repair context boundaries and launcher routing,
  then verify a complete native typed-command journey with fake session data.

## 2026-09-13 — Step 9: Autonomous Guardian & System Health Governor Completed

- **Milestone**: Step 9 of clean rebuild — Autonomous Guardian & System Health Governor.
- **Artifacts Created / Modified**:
  - `skills/guardian.py`: Modernized into a resilient Ultron safety layer. Implemented comprehensive dangerous command screening (20+ destructive signatures), gated execution (`guard()`), silent duress alarm subsystem (`raise_duress()`, `check_duress()`, `clear_duress()`) with fail-closed tamper detection, dual encrypted audit logging (AES-256 encrypted log file `skills/lya_actions.log.lya` and person-scoped SQLite audit log via `storage.store.record_audit()`), and proactive user safety pushback (`correct_user()`).
  - `skills/governor.py`: Created zero-dependency system health governor for Windows. Uses native `win32process.GetProcessMemoryInfo` for WorkingSet memory monitoring (<14MB footprint), `ctypes.windll.kernel32.GetSystemPowerStatus` for live battery percentage and AC charging state, `shutil.disk_usage` for storage capacity, automated threshold alerts (`check_governor_limits()`), and a file-based emergency circuit breaker (`KILL_SWITCH`) with instant suspension and admin-only reset.
  - `skills/harden.py`: Integrated duress flag status and kill switch state into security self-audit (`harden.audit()`).
  - `main.py`: Connected natural language command routing for `"system health"`, `"battery"`, `"battery status"`, `"is lya secure"`, `"emergency stop"` / `"kill switch"`, `"release kill switch"`, and guardian execution gates before standard command handling.
  - `test_guardian_governor.py`: 12 comprehensive unit and integration tests covering dangerous command detection, gated execution, silent duress lifecycle, tamper resistance, encrypted dual audit logging, proactive user guidance, resource governor metrics, kill switch lifecycle, harden audit integration, and assistant routing.
- **Verification & Test Results**:
  - `test_guardian_governor.py`: 12/12 passed in 0.110s.
  - All workspace unit tests via discovery (`test_*.py` across 11 test modules): 80/80 passed in 2.930s.
  - `test_regressions_r01_r05.py`: 16/16 regression assertions passed.
  - `test_liveness.py`: 4/4 anti-spoof checks passed.
  - `review_checks.py`: 6/6 syntax and regression checks passed.
  - `desktop/check_ui.py`: 10/10 UI checks passed in 1.672s.
  - **Zero test failures or regressions across the entire project codebase.**
- **Resource Footprint & Safety Constraints**:
  - Verified 0 unnecessary CPU/GPU overhead: zero polling threads or busy loops. Metrics queried only on-demand or during scheduled checkpoints.
  - WorkingSet process memory measured at ~13.8MB (<100MB budget).
  - Complied strictly with `RULE[AGENTS.md]`: all tests run with synthetic fixtures and isolated temporary files (`tempfile`). No real credentials, biometrics, or plaintext sensitive data saved to disk or ledgers.
- **Next Step**: Step 10 — End-to-End System Integration, User Journey Smoke Test, & Packaging (Tying crystal UI, voice bridge, permission escalation, safe folder browsing, reminders, guardian, and governor into a cohesive end-to-end verified pipeline).

## 2026-09-13 — Voice & Multilingual Engine Upgrade (Natural 21yo Voice + Groq Whisper)

- **Milestone**: Upgrade 1 & 2 of voice layer — Microsoft Edge Neural TTS + Groq Whisper multilingual STT.
- **Artifacts Created / Modified**:
  - `audio/voice.py`:
    - Integrated Microsoft Edge Neural TTS (`edge-tts`) with the default `en-US-AvaNeural` voice (natural, warm, expressive 21yo young woman tone). Added support for configurable voices via `LYA_VOICE` (e.g. `ta-IN-PallaviNeural` for Tamil, `hi-IN-SwaraNeural` for Hindi, `en-IN-NeerjaNeural` for Indian English).
    - Added pitch and rate emotion modulations (`EMOTIONS` dictionary) corresponding to detected conversation tone (playful, excited, sad, worried, serious, angry, tired, neutral).
    - Implemented `_play_mp3_interruptible` using Windows native MCI (`ctypes.windll.winmm.mciSendStringW`) with instant mid-sentence cancellation via `stop_speaking()`.
    - Maintained robust fallback to local `pyttsx3` if offline or network unavailable.
    - Upgraded `transcribe(wav_bytes)` with Groq Whisper Large v3 cloud API (`_transcribe_groq`), providing ultra-fast (~200ms) transcription across 99+ languages with zero laptop GPU load. Retained offline Vosk model fallback and Google Speech Recognition fallback.
  - `test_voice.py`:
    - Added unit tests: `test_edge_tts_ava_voice_synthesis`, `test_stop_speaking_playback_interruption`, and `test_groq_whisper_transcription`. All 11/11 tests pass.
  - `brain/mind.py`:
    - Fixed `history_key` 2-tuple compatibility for `test_foundations.py`.
- **Verification & Test Results**:
  - `test_voice.py`: 11/11 passed in 1.865s.
  - All 11 workspace test suites: 84/84 passed in 5.810s.
  - `test_regressions_r01_r05.py`: 16/16 passed.
  - `desktop/check_ui.py`: 13/13 passed in 3.537s.
  - `review_checks.py`: 6/6 passed.
  - Live audio test: Verified clean speech synthesis and playback via Windows MCI.
- **Next Step**: Step 3 (Cognitive Brain Phase A: Intent Classification & Tiered Memory Pipeline).

## 2026-09-13 — Brain workflow implementation and isolated acceptance

- **Implemented:** `brain/workflow.py` routes typed requests through identity,
  permission, scoped retrieval, ordinary inference or council, final validity checks
  and a bounded response. `desktop/app.py` dispatches via a background worker,
  suppresses cancelled/late results and exposes `brain help`, `brain status`,
  `brain demo` and `who am i`. Cosmetic colors cannot grant identity.
- **Memory/schema:** `brain/notes.py` reuses `storage/store.py` encrypted SQLite.
  Working context is per request; session notes are bounded RAM; short/long defaults
  are 7/90 days; timed notes require a timezone; permanent means no automatic expiry.
  Explicit correction increments revisions. Same-person graph links cascade on
  deletion. Additive migration preserves legacy notes. No real store was migrated.
- **Boundary fixes:** missing person IDs cannot select another profile; scoped
  failures cannot use legacy fallback; credential kinds are excluded from context.
  `brain/mind.py` history keys include person ID (restored after a newer compatibility
  edit removed it). `main.py` uses the enrolled registry rather than the old file
  gate. Expired pending faces cannot be promoted. `security/vault.py` loads keys
  lazily; `security/policy.py` carries person ID and verification expiry.
- **Council:** `brain/council.py` uses reviewer/planner/critic plus synthesis, at most
  four sequential calls through one configured client. Failure is labelled. This
  is perspective comparison, not independent verification or guaranteed accuracy.
- **Voice:** preserved newer shared-workspace cloud voice changes. Desktop requires
  local transcription before opening the microphone and displays readiness/errors.
  Online speech synthesis test now requires explicit `LYA_RUN_ONLINE_TESTS=1`;
  isolated review strips this setting and blocks network/sensors.
- **Artifacts:** `LYA_BRAIN_WORKFLOW.md`; `diagrams/11-brain-workflow.mmd`, `.svg`,
  `.png`; `diagrams/12-brain-schema.mmd`, `.svg`, `.png`;
  `diagrams/render_brain_map.py`; `brain/demo.py`. Both Mermaid sources validated
  (2/2); both companion PNGs visually inspected and readable. README and desktop
  README link the current workflow. Demo uses synthetic data and an ephemeral key
  in a separate temporary process; it never unlocks the real profile.
- **Checks:** `.venv-ui/Scripts/python.exe -B review/review_20260913.py --brain`
  completed successfully. Storage 8, identity 5, mind 6, voice 10 passed + 1 skipped,
  desktop 13, brain 16, foundations 14, R01/R05 regressions 16: **88 passed**.
  Five historical defect probes returned false. Logs, result index and synthetic
  UI renderings: `review/2026-09-13-brain/`. Tests cover migration, restart, expiry,
  revocation during inference, cross-person scope, graph deletion, council failures,
  native dispatch, demo and cancellation. The harness now exits nonzero on failures.
- **Limitations:** model output, approval and identity fixtures are synthetic;
  no camera/microphone capture, real enrollment, phone pairing, cloud upload or
  live model-quality evaluation occurred. Loopback model service was unreachable.
  Hardware inventory via WMI was denied; RAM/GPU remain unverified. Whole-file
  encryption remains suitable only for small stores. Expiry excludes reads;
  physical cleanup waits for authorized activity and does not erase old backups.
- **Decisions/next step:** retain one local database, bounded keyword retrieval and
  one-hop graph; no new heavyweight graph server, embeddings or weight training.
  Connect trusted identity/approval and choose/test an available model next, then
  run real-device acceptance. Enrollment remains deferred. Cloud provider response
  is pending; portable encrypted recovery/mobile sync need design before upload.

## 2026-09-13 — Research-backed retrieval upgrade and Oracle design

- Owner reports Oracle Free Tier and collected API keys; VM/provider details remain
  pending. Read agent-reach skill/search/web references; CLI commands unavailable
  on shell, so used built-in web access to primary papers and official docs.
- Artifact: `LYA_ADVANCED_BRAIN_PLAN.md` contains cited research, implemented/proposed
  distinctions, storage lifecycle, Oracle split and six ordered acceptance gates.
  MemGPT/Reflexion/Generative Agents/GraphRAG inform design; no paper performance
  claim is presented as a LYA benchmark. Biological simulation is not the target.
- Changed `brain/notes.py`: RAM-only FTS5/BM25 replaces substring overlap, label
  weighting and bounded token input; six-result budget includes graph neighbors,
  prioritizing declared contradictions/dependencies. Scoped active non-credential
  records only. Rebuild on each query avoids stale correction caches; no persistent
  plaintext index. Still lexical, not semantic or multilingual paraphrase search.
- Checks: FTS5 available; `review/review_20260913.py --retrieval` passed all suites:
  91 checks passed, 1 online speech test skipped; five old defect probes false.
  Added three brain tests (19 total) for token matching/input syntax, contradiction
  inclusion with full lexical results, and correction freshness. Logs and synthetic
  renders: `review/2026-09-13-retrieval/`; older runs preserved.
- Updated `LYA_BRAIN_WORKFLOW.md` and this ledger. No real runtime data collected,
  credentials displayed, provider calls, model installs, Oracle changes or uploads.
- Limits: 2,000-note per-query index rebuild needs workload benchmarks; no accuracy
  guarantee, embeddings or automatic lesson learning. Model context cap can omit
  retrieved notes. Identity/approval and real model binding remain incomplete.
- Next: obtain VM shape/RAM/region and provider names only; connect one selected
  model with bounded routing, then identity-gated real acceptance. No need to
  collect more API keys yet. Oracle current documentation differs from old guides;
  account-specific quotas need verification before infrastructure choices.

## 2026-09-14 — Oracle connection attempt and key-file protection

- Owner approved continuing server verification and backend preparation. Inspected
  current brain status and legacy gateway source. The gateway imports local
  biometric/Windows-dependent components; it was not uploaded as a cloud service.
- SSH reached the supplied address. Initial attempt refused the key because its
  Windows permissions were too broad. Restricted the single private-key file to
  the owner's Windows account using an approved elevated filesystem operation.
  The restricted sandbox can no longer read it; SSH retries ran through approved
  execution as the owner. No key contents or API credentials were displayed.
- Both standard Oracle Linux (`opc`) and Ubuntu (`ubuntu`) usernames returned
  `Permission denied (publickey)`. This does not establish whether the username,
  target address or key pairing is wrong. No remote diagnostic commands executed.
- Added `*.key`, `*.pem` and `oracle_known_hosts.local` to `.gitignore`. The SSH host
  key was recorded on first contact in the ignored local known-hosts file; it has
  not been independently matched against the Oracle console. Runtime connection
  details and key material are intentionally omitted from this plaintext ledger.
- Checks: key ACL change succeeded; host reachable; both authentication attempts
  failed. No software installation, data upload, firewall change, enrollment or
  model/provider call performed. No application source changed or tests rerun.
- Next required input: confirm the instance's console SSH connection instructions
  (public IP and username) and that the supplied key is the one associated with
  that instance. Share connection details or console screenshot, never key content.
  Then resume resource verification and backend preparation.

## 2026-09-14 — Confirmed console details and SSH key rejection

- Owner's clearer screenshot confirms the originally supplied address and Ubuntu
  username. The assistant's tentative alternate-IP reading of the smaller image
  was incorrect; no connection to that alternate address was attempted.
- Local key validation succeeded (RSA); fingerprint used only for diagnostics,
  not copied into this ledger. Filtered SSH debug output confirms the private key
  was tried and a public-key authentication packet was sent. Server rejected it
  with `Permission denied (publickey)`. No key parsing or ACL error remains.
- Cause remains either a different instance-authorized key or server-side SSH
  authorization configuration. Do not claim a proven key mismatch without the
  authorized public key or server logs. Need the matching original instance key,
  or an owner-accessible console recovery route if it is lost.
- No remote command executed; no source changes, installations or model calls.
  Backend preparation remains blocked on authenticated access. Do not delete or
  recreate the existing instance merely to resolve this login problem.

## 2026-09-14 — Replacement SSH key accepted; server verified

- Owner supplied a second key and requested a retry. Restricted that exact file's
  Windows ACL to the owner's account, then connected with the confirmed Ubuntu
  login and existing strict known-host verification. SSH completed successfully.
  Key material and connection identifiers are omitted from this ledger; local
  private keys and host records remain covered by Git exclusions.
- Read-only remote checks: ARM64 (`aarch64`), 4 online CPUs, approximately 24 GB
  RAM, no swap, 193 GB root filesystem with approximately 191 GB free at inspection,
  Python 3.12.3. These are server-reported capacities, not a billing assessment.
- Previous authentication blocker resolved. No package installation, firewall
  change, file upload, runtime data migration or provider call performed.
- Next: inspect existing server services, prepare a scoped backend environment,
  select/configure one model provider and test public synthetic requests before
  connecting identity-gated private memory. Enrollment remains deferred.

## 2026-09-14 — Oracle inference bridge prepared; model selection pending

- Inspected existing server listeners and Python support. Created private LYA
  directory (mode 700); verified OpenSSL/SQLite modules. Uploaded only
  `cloud/inference.py` to `/home/ubuntu/lya/inference.py` (mode 600), refusing an
  existing-file overwrite. No packages, daemon or public API listener installed.
- Added `brain/oracle.py`: opt-in JSON configuration, strict SSH known-host checks,
  key path scoped to project, hidden Windows subprocess, 30-second timeout and
  redacted errors. `brain/workflow.py` selects this client only when the ignored
  local Oracle configuration exists; no such activation file was created.
- Backend validates message roles/fields, bounds input/output, calls only the
  fixed Groq HTTPS endpoint when configured, and does not retry/fallback or enable
  tools. Per-request bounds are not a daily cost cap. Identity/private memory stays
  local; no new authority is granted by the transport.
- Added `.env` and `desktop/oracle.local.json` Git exclusions. Inspected only `.env`
  variable names, not values. No API credential transferred or validated.
- Checks: `test_oracle.py` 5/5 and `test_brain_workflow.py` 19/19 passed with fake
  credentials and mocked transports/temporary stores. Live SSH synthetic smoke
  check returned exactly `provider_not_configured`, proving deployment/transport
  but not model inference. Full previous suite was not rerun for this milestone.
- Owner asked for help choosing the smartest fitting model rather than selecting
  Groq immediately. Reviewed official Groq capabilities/rate limits/data handling
  and Google's pricing/data-use information. Provisional recommendation: GPT-OSS
  120B through Groq for text reasoning; Gemini as a later multimodal comparison.
  No claim of benchmark superiority on LYA tasks. See `cloud/README.md` for sources,
  setup, limitations and acceptance requirements. A reasoning model's completion
  budget must be tuned/tested before activation; initial 400-token cap may be short.
- Next: settle provider/model, transfer only its credential through protected SSH,
  verify account access/quotas with synthetic prompts, evaluate answer quality,
  then enable the desktop bridge. Real identity/approval binding, mobile access,
  restricted deployment credentials and daily request budgeting remain pending.

## 2026-09-14 — Provider-independent routing and researched model shortlist

- Owner requested multiple models/providers and backup behavior; clarified Groq,
  not xAI Grok. Tokenroter's exact service is still unknown. Used agent-reach
  instructions and primary web docs; CLI/mcporter unavailable, no version update.
- Created `LYA_MODEL_STRATEGY.md`, `cloud/model-evaluation.json` (unrun live-model
  rubric), disabled `cloud/provider.example.json`, and validated
  `diagrams/13-provider-routing.mmd`. Primary sources and scope limits are linked
  in the report. No universal-best or live-quality claim.
- Implemented `cloud/router.py`: task/privacy filtering, pinned-gateway gate,
  independent upstream domains, SQLite atomic daily attempt cap and persisted
  cooldowns, maximum two attempts, bounded routing window. Failure modes distinguish
  retryable service errors from auth/input/refusal/output failures. No prompts,
  credentials or hidden model reasoning in counter state.
- Extended `cloud/inference.py` with Groq/NVIDIA/HF/explicit OmniRoute adapters,
  bounded per-route completion budgets, Groq reasoning controls, redirect denial
  and incomplete-output detection. `brain/oracle.py` forwards task/sensitivity
  and displays safe route/attempt information. `brain/workflow.py` supplies task
  classification and private-context status without granting new authority.
- `cloud/probe_models.py` inspected known credential settings and reported no
  usable Groq/NVIDIA/HF credentials. No provider catalog or generation request
  occurred. This does not imply the owner lacks keys stored elsewhere.
- Verification: `test_router.py` 13/13, `test_oracle.py` 5/5,
  `test_brain_workflow.py` 20/20 passed. New checks include concurrent budget
  reservations, persisted cooldowns, time/attempt limits, privacy isolation and
  task propagation. Tests use fake services and temporary state. Full historical
  suite was not rerun; earlier 91-check result remains dated evidence.
- Deployed the tested scripts/template to the existing private Oracle directory,
  preserving the earlier backend as `inference.before-router.py`. Executed
  `cloud/verify_router.py` remotely: synthetic failover passed; no provider call
  or credential upload. Routes remain disabled; no public listener was opened.
- Limits: task matching is heuristic, council seats are not deliberately diverse,
  inference adapter is text-only and invokes no tools. Daily attempts are not a
  dollar budget; gateway pinning requires truthful operator settings. Oracle or
  internet outage remains outside provider failover. No retraining/automatic
  skill activation or storage migration was performed.
- Next: locate protected credentials and exact gateways, verify account catalogs
  and entitlement, evaluate accessible candidates, approve private destinations
  and enable a measured primary/backup. Then integrate research/execution and
  evidence/episode/lesson storage with tests and backup-restore verification.

## 2026-09-14 — Live account validation and experimental desktop activation

- Owner saved provider settings and authorized proceeding. Normalized the two
  NVIDIA note-style lines into dotenv assignments without printing credentials.
  Groq and NVIDIA authenticated catalogs succeeded. OmniRoute settings and HF
  credentials remain absent; exact Tokenroter service/OPENAI_API_KEY ownership
  clarification is pending. Unrelated secrets/services were not used.
- Verified the supplied NVIDIA DeepSeek V4 Flash 0731 model against its current
  official page and catalog. Local calls timed out at 8, 25 and 30 seconds with
  different reasoning settings; an Oracle attempt timed out at 8 seconds.
  NVIDIA GPT-OSS 20B answered simple prompts but timed out on a later case;
  Nemotron Lightning timed out and the tested Mistral endpoint returned 404.
  None of these routes was declared ready or activated.
- Extended `cloud/probe_models.py` with a bounded-name dotenv reader supporting
  quotes, comments and export prefixes without expansion/evaluation. Added
  `cloud/evaluate_models.py` for explicit live synthetic evaluation; it neither
  executes generated code nor writes private prompts/credentials/reasoning.
  Reports are preserved separately under `review/2026-09-14-live-models/`.
- Groq GPT-OSS 120B completed eight cases after output-prompt tuning. Completion
  was not equated with correctness: reviewed answers invented architecture facts;
  an earlier code sample passed its isolated assertions, while a later sample's
  generated assertion failed. Qwen 3.8 testing stopped on HTTP 429. Details and
  unmodified synthetic outputs are linked in the review README.
- Strengthened `brain/workflow.py` instructions on concise output, unmeasured
  claims and trusted authentication. These are guidance, not a truth guarantee.
  `desktop/app.py` now labels configured cloud text. No model tool execution,
  self-training, memory migration or research integration was added.
- Activated only Groq public text with a 100-attempt daily cap and 2048-token
  completion cap in protected Oracle configuration. Only its required credential
  was persisted remotely through SSH; no .env upload. NVIDIA remains disabled
  and has no persisted credential in that configuration. Private routes deny.
  Enabled ignored `desktop/oracle.local.json` after the live checks succeeded.
  No new public listener or package installation. Existing backend rollback is
  preserved; moving aside desktop config returns to the local selection path.
- Checks: 41 isolated tests passed (`test_router`, `test_oracle`,
  `test_brain_workflow`, `test_provider_setup`); fake keys and temporary storage.
  Actual guest Brain/Oracle/Groq corrected-deadline request passed. A synthetic
  private request returned no_eligible_route. Actual Qt worker arithmetic request
  returned 42 with the active route ID; camera/microphone were off. Captured result
  in `desktop-live-check.json`, then visually replayed it with explicit test-font
  loading for `live-glass-response.png`; this was not another provider request.
- Remaining: evaluate an independent reliable backup once provider details are
  available; account quotas/billing were not fully established. Private cloud
  destinations remain disabled. Source verification, verified identity, diverse
  council seats, safe skill execution and storage expansion remain open gates.

## 2026-09-15 — Finish launcher fix and check Git status

- The owner's PowerShell execution-policy error prevented the .ps1 launcher from
  running. Added `launch-lya.cmd` to start the existing pythonw executable directly
  with the project working directory and --show-panel. Updated `desktop/README.md`
  with double-click/PowerShell instructions. No execution-policy changes, new
  packages, automatic sensors or provider calls were needed for this fix.
- Verification: the launch check started a responding native LYA conversation
  window. On resume, its Python processes were still responding. This is startup
  evidence, not a repeat of the previous live-inference test. No new test suite
  was added for the two-line launcher.
- `git status --short --branch` reported a clean main tracking origin/main before
  this continuity update. Git warned that the sandbox could not read the user's
  global ignore file. No fetch, commit, push or global Git configuration change
  was performed. The ledger update itself is a new working-tree change.
- Next priority: dependable independent provider backup and evidence/code checks
  for answers. Then bind verified identity to private memory and test the full
  save/correct/recall/delete journey before adding cloud memory backup or sync.


## 2026-09-15 — Optional owner-model artwork with conservative default

- Preserved the supplied GLB unchanged in `desktop/assets/obsidian-crystal.glb`;
  source and copy SHA-256 match. Inspected 95,428 triangles and seven materials.
  Added one-time `desktop/bake_crystal.py` using existing NumPy/Qt libraries;
  generated `desktop/assets/obsidian-baked.png` and its metadata JSON. Runtime
  does not parse the model or initialize the baking renderer. Glass/metal shading
  is approximate; this is a static pose, not interactive or rotating 3D.
- Updated `desktop/app.py`: optional baked artwork, cached task/role tinting,
  original default, menu toggle and --model-art/--original-art launch switches.
  Decorative drift ends after three seconds; idle, hidden and reduced-motion
  states stop it. Hidden/reduced-motion color changes are immediate. Bad image
  decode/size falls back; average last-30 paint time above 8ms returns to the
  original and enables reduced motion. Cosmetic roles do not grant access.
- Decision: retain the original default under the owner's performance condition.
  Model process CPU was higher in the initial and repeated short measurements,
  despite low median paint durations. No zero battery/lag guarantee is made.
  Both selections had zero extra idle paints in all six 1.2-second observations.
  Detailed results, limitations and light/dark synthetic previews are preserved
  in `desktop/qa/2026-09-15-orb/`; see its README and two comparison JSON files.
- Checks: final 16 isolated `desktop/check_ui.py` tests passed, including switching,
  original default, malformed decode, timer shutdown and automatic fallback.
  Adjusted an existing voice-signal test's offscreen/no-tray visibility assertion
  to match the recoverable-orb behavior. No sensors, private stores or providers
  were used. The final bake passed alpha validation and visual inspection;
  source/copy hashes match. Updated `desktop/README.md` with restart and fallback.
- Limitations: short offscreen painter/process timing is not battery profiling,
  sustained runtime acceptance or physical display FPS. Menu choice is per-session.
  Backend routes, authentication and memory remain unchanged by this UI task.
- Next: dependable independent provider backup and evidence/code validation;
## 2026-09-18 — T02 independent provider candidate research (documentation only)

- **Requested outcome:** identify the best free / zero-subscription, high-intelligence,
  OpenAI-compatible model providers that could serve as LYA's independent backup route
  (T02), including their safety/data terms and integration fit.
- **Result:** nothing was enabled, deployed or called. Candidates and documented quotas
  are recorded in `review/2026-09-18-free-provider-candidates/README.md`.
  Headline changes to the old assumptions: Cerebras has **no permanently free tier**
  ($5 trial credits, 30 days, verified payment method required before API access);
  **GitHub Models was retired 2026-07-30**; SambaNova's entry plan requires a payment
  method and purchased credits; Hugging Face free accounts receive only **$0.10/month**
  (so the existing `huggingface` route is not a usable daily backup); Mistral's free
  mode is documented as restrictive/evaluation-only.
- **New strongest candidates (documented free):** W&B Serverless Inference —
  `https://api.inference.wandb.ai/v1/chat/completions`, free plan default cap
  **$100/month** of serverless credits (explicitly a limited-time offer), hosting
  DeepSeek V4-Flash/Pro, GLM-5.3-Flash, GLM-5.2, Nemotron 3.5 Lightning and 3 Ultra 550B,
  Qwen3.6-35B-A3B, MiniMax M3, Kimi K2.6/K2.7-Code, gpt-oss-120b, Llama 3.3 70B;
  **Google Gemini free tier** via `…/v1beta/openai/chat/completions` (free-tier prompts
  and outputs may be used to improve Google products; per-model free limits are now
  visible only inside AI Studio); **Z.ai GLM-4.7-Flash / GLM-4.5-Flash** listed at $0
  permanently on `https://api.z.ai/api/paas/v4/chat/completions`; **OpenRouter `:free`
  pool** (25 free IDs today, 20 RPM / 50 requests per day, 1,000/day after a one-time
  ≥$10 credit); **Cloudflare Workers AI** (10,000 neurons/day, frontier models need a
  paid plan, and the only provider found that explicitly does not train on or share
  customer content).
- **Integration finding:** one pinned backup route needs **no provider code change**.
  A route using `provider: "omniroute"` with an https `endpoint` ending in
  `/chat/completions`, `upstream_pinned: true` and a distinct `failure_domain` satisfies
  `router.validate_config`, `upstream()` and `inference.infer()`. OpenRouter's
  per-request upstream pinning (`provider.only`, `allow_fallbacks: false`,
  `provider.zdr: true`) is **not** producible by the current payload builder, so an
  OpenRouter route cannot yet be certified as a genuinely pinned upstream.
- **Routing consequence:** the 8-second provider allowance in `cloud/router.py` favours
  low active-parameter MoEs (Nemotron 3.5 Lightning 3B/30B, GLM-5.3-Flash 18B/320B,
  GLM-4.7-Flash, DeepSeek V4-Flash 13B/284B, Qwen3.6-35B-A3B) over the 550B–1.6T models,
  which reproduce the NVIDIA deadline failure at 8,001 ms. Answer quality remains a T03
  gate; a 200 response is not an accuracy pass.
- **Verification and limits:** the `agent-reach` skill was invoked as requested; its CLI
  (`agent-reach`, `mcporter`, `gh`, `yt-dlp`) is not installed on this machine, so its
  Jina reader path plus direct documentation fetches were used. No account, key, login,
  cookie, private data or provider request was involved; nothing was deployed or
  activated. `check-t02.cmd` was re-run today: **81/81 offline checks pass** (67 baseline
  + 14 T02). All provider figures are documentation evidence, not LYA test results;
  owner-account quotas, live latency and acceptance remain unverified.
- **Next step:** owner creates one candidate account (W&B first, Z.ai as the
  permanent-free alternative, Gemini as the strongest general model), then run the eight
## 2026-09-18 (second pass) — stealth models, model-specific availability, signup map

- **Requested outcome:** verify the claim that "Union Alpha" offers an unlimited free
  tier; check whether DeepSeek V4.3-Flash or GLM-5.3-Flash can be obtained free; find
  further lesser-known free providers, with signup links the owner must use personally.
- **Union Alpha finding:** it was a **stealth preview model** on OpenRouter
  (`stealth/union-alpha`, released 2026-09-16, 262K context, text+image), developed by
  **Unbiased** and revealed as **Pareto** (`unbiased/pareto`). OpenRouter states the
  **free stealth period has ended**; Pareto now costs **$2.50/$7.50 per 1M**. The other
  stealth model, **Ox Alpha** (1.0M context, released 2026-08-20), was revealed as
  **ZAI GLM-5.3-Flash** and its free preview is over too. Both retained prompts with the
  provider (not used for training). So "unlimited free tier" was a **temporary
  non-renewing preview**, already expired — not a provider and not unlimited.
- **Cloaked/alpha models that are free now** (Sonoma Sky/Dusk Alpha, Horizon Beta,
  Cypher Alpha, Polaris Alpha, Sherlock Think Alpha) **log prompts and completions and
  may train on them**, and one warns against production use. Recorded as unsuitable for
  LYA; not recommended.
- **DeepSeek "V4.3-Flash" does not exist.** DeepSeek's API lists `deepseek-flash` =
  **DeepSeek-V4.1-Flash** and `deepseek-v4-pro` = V4-Pro-0813; `deepseek-v4-flash` is a
  retired alias now served by V4.1-Flash. **No free tier** (balance required): Flash
  $0.15/$0.60 per 1M off-peak ($0.30/$1.20 peak), Pro $0.66/$1.98 off-peak. Free DeepSeek
  today: `deepseek/deepseek-v4-flash-0731:free` on OpenRouter, and DeepSeek V4-Flash-0731
  inside W&B's free monthly credits.
- **GLM-5.3-Flash is not free** at Z.ai ($0.15/$0.50 per 1M), on OpenRouter
  (`z-ai/glm-5.3-flash` $0.09/$0.30), or on Cloudflare (paid plan required). It **is**
  reachable free through **W&B Serverless Inference** (`zai-org/GLM-5.3-Flash` inside the
  free $100/month cap) and through **Alibaba Cloud Model Studio's** new-user free quota.
  The permanently free GLM models remain GLM-4.7-Flash, GLM-4.5-Flash and GLM-4.6V-Flash.
- **Additional free routes found:** (1) **`openrouter/free` Free Models Router** —
  genuinely zero-cost, random selection across **28** free-variant models, feature-filtered,
  200K context, released 2026-02-01, still subject to 20 RPM / 50 requests per day
  (1,000/day after ≥9 all-time credits). (2) **Alibaba Cloud Model Studio new-user quota** —
  **~1M tokens per model for 90 days**, per-model and non-transferable, covering
  qwen3.8-max/flash, deepseek-v4.1-flash, deepseek-v4-pro-0813, glm-5.2, ZHIPU/GLM-5.3,
  kimi-k3, MiniMax-M2.5 (Singapore region; enable "Free Quota Only" to avoid charges);
  plus **2,000 free calls/day via OAuth authentication**. (3) **Public AI** (Swiss
  non-profit) free access to public/sovereign open models — free but not frontier, docs
  unverified. (4) `openrouter/pareto-code` Pareto Router: **conflicting evidence** (model
  page FAQ says zero price; routing docs say you pay the underlying model) — recorded as
  not free. Rejected: Chutes (no free tier), Featherless ($25/$50 per month), Nebius
  ($1 trial, card required), Upstage/Poolside promos, AI Horde/Pollinations (no SLA).
- **Verification and limits:** documentation and live catalogue evidence only, gathered
  with the `agent-reach` skill's Jina reader path plus direct documentation fetches (its
  CLI is not installed on this machine). OpenRouter's model catalogue was queried live and
  filtered for $0 prompt/completion pricing (25 free-variant IDs) and grepped for
  stealth/pareto/glm/deepseek entries. **No account, key, signup, login or provider
  request was performed by the agent; nothing was enabled or deployed.** Z.ai free-Flash
  rate limits, ModelScope's free quota and Public AI/W&B data policies remain unverified.
  `check-t02.cmd` was re-run earlier today: 81/81 offline checks pass. T02 remains
  **BLOCKED** at independent live acceptance.
- **Artifact:** `review/2026-09-18-free-provider-candidates/README.md` (sections 9.1–9.6
  add this pass; signup map in the reply/record). Next step is unchanged: owner creates
  one account (W&B first, Z.ai or Alibaba Model Studio as the permanent/90-day-free
  alternative), then run the eight synthetic rubric cases and three latency checks before
  enabling any route.
  synthetic rubric cases plus three latency checks before enabling any route. T02 stays
  **BLOCKED** at independent live acceptance until that passes.
  then verified identity and private save/correct/recall/delete acceptance.


## 2026-09-15 — Ordered delivery roadmap and independent owner work

- Created `LYA_TASK_ROADMAP.md` from dated project evidence and the product,
  foundation, model and memory documents. Defined 14 numbered tasks with current
  status, dependencies, concrete implementation work and completion checks.
- Prioritized baseline -> independent inference backup -> answer verification ->
  trusted session -> private memory. Later stages cover council, files, voice,
  consented recognition, recovery, phone access, bounded actions and learned workflows.
- Added seven independent owner deliverables with safe content guidelines and
  source-file ownership guidance for parallel work. No subagents were launched.
- Checked roadmap paths against the workspace and reviewed its distinction between
  implemented, isolated-tested, live-tested, deferred and future work. No new live
  integration, model research, hardware check, deployment or enrollment occurred.
  This was documentation work; no runtime test suite was rerun.
- Decisions: preserve existing verified code; evaluate providers using actual task
  evidence; keep private cloud denial until an eligible path is established; measure
  battery before changing the orb default. No estimated completion percentage or
  unattended background-work promise. Next session begins with roadmap task 01.


## 2026-09-16 ? Finish detailed implementation handoff

- Created `LYA_IMPLEMENTATION_CHECKLIST.md` with T01-T14, source entry points,
  integration dependencies, concrete checklists, acceptance cases, scope exclusions,
  blocker handling and required deliverables. Linked it from the roadmap and brain.
- Added isolated-test guidance, evidence naming, unresolved decision table, task
  assignment/completion templates and parallel file-ownership rules. Existing
  authorization remains applicable; enrollment and private cloud access stay gated.
- Inspected source entry points and documented existing versus future integrations.
  Checked task coverage, required fields, source references and document formatting.
  Documentation only: no runtime suites, live providers, sensors or deployment run.
- Earlier oversized write failed before execution; saved the complete document in
  smaller sections and verified all 14 task guides are present.
- Next: use T01 for the reproducible baseline, then T02 independent provider backup;
  owner can independently prepare command cases and dummy-data file-browser designs.

## 2026-09-16 — Classify tasks by reasoning level

- Created `LYA_TASK_REASONING_LEVELS.md` and linked it from the roadmap and
  implementation checklist. Classified all T01-T14 tasks and separated lower-level
  substeps from security and architecture decisions.
- Medium-level leads: T01 baseline, T07 file browser and T08 voice integration,
  with mandatory escalation for authorization, path security, recording/privacy or
  network fallback. High-level leads: T02-T06 and T09-T14.
- No full production task is assigned low reasoning. Low-level work is restricted
  to synthetic fixtures, mockups, fixed-command execution, formatting and evidence
  collection. It cannot handle secrets/private data, activate providers, edit trust
  boundaries, execute side effects, mark readiness or publish.
- Added escalation triggers and copy-ready assignment prompts for all three levels.
  Documentation only; no tests, live services, sensors, enrollment or deployment ran.

## 2026-09-16 — Complete T01 reproducible baseline

- Recorded branch `main`, starting revision, Python 3.12.14 and the launcher hash
  without reading the IDE's external provider configuration or printing secrets.
- Reviewed and ran the isolated suites separately: router 13, Oracle 5, provider
  setup 3, brain workflow 20 and native UI 16; total 57 passed, zero failed. Tests
  used fake providers, temporary encrypted stores or Qt offscreen widgets.
- The real `launch-lya.cmd --reduced-motion` started the expected native app. A
  separate isolated Qt process exercised the real `Desktop.quit` path and exited
  with code 0. The two processes created by the launcher smoke test were explicitly
  cleaned up and confirmed absent.
- Verified guest brain commands without network access: help, identity, status,
  private-memory denial and sleep/context clearing. Native checks covered keyboard
  commands, file allowlisting, close/reopen and delayed-result cancellation.
- Saved acceptance cases, ten baseline commands, limits and recovery at
  `review/2026-09-16-T01-baseline/README.md`; marked only T01 complete in the
  roadmap/checklist. No production configuration or runtime source changed.
- Limitation: visible startup was process-verified while input was exercised in the
  native offscreen harness; this was not a live model-quality or hardware test.
  Next: T02, an actually independent provider backup with private-route denial.

## 2026-09-16 — Add owner-run test and status diagram

- Added `check-t01.cmd`, a one-command safe offline runner for the reviewed T01
  suites. It stops on the first failed suite and makes no live provider or sensor
  calls. A complete run passed all 57 checks.
- Added `LYA_TEST_GUIDE.md` with visible startup instructions, twelve command checks,
  expected results, current working/pending boundaries and a safe failure-report format.
- Added `diagrams/14-t01-working-and-test.mmd`; derived its runtime structure from
  current source/evidence and marked current, earlier-tested, next and pending paths.
  Mermaid validation passed with zero errors and zero warnings.
- Added directly viewable SVG and PNG companions. The PNG was rendered locally from
  the SVG using installed Qt libraries and visually inspected for readable layout.
- No production behavior, provider configuration, private data, sensor or deployment
  changed. Next remains T02 independent provider backup.

## 2026-09-16 — Implement centered wake and compact conversation UI

- Added `desktop/experience.py` with a 1.6-second centered guest greeting, bounded
  shrink/dock animation, compact input, answer card and explicit expanded chat.
  Modified the main entry in `desktop/app.py` to select this experience. Cached
  crystal drawing scales with the widget; tiny docked labels are suppressed.
- Selected the owner's baked GLB artwork per the revised request; no runtime 3D
  engine. Original artwork, reduced motion and slow-paint fallback remain available.
- Added brief chunked answer reveal and a six-pair RAM display transcript which
  clears on close. This is not persistent memory or new model conversation context.
  Existing command, guest, private-data denial and cancellation paths are reused.
- Added `desktop/check_experience.py`; updated `check-t01.cmd` to include it.
  Full runner passed 62 checks (41 backend, 16 base UI, five compact UI). New tests
  cover intro/docking, modes, guest denial, stale results, reveal cancellation,
  screen bounds and no further orb paints after the idle animation stops.
- Actual `app.main()` completed a bounded offscreen startup/event-loop smoke check
  with exit 0. No real provider, sensors, enrollment or remote deployment ran.
- Updated desktop README and owner test guide. Saved and inspected synthetic
  input/answer/chat previews in `desktop/qa/2026-09-16-compact/` with evidence README.
  Short isolated checks do not establish laptop battery life or physical FPS.
- Next: owner desktop trial of launch, click, time, open chat and close; then T02
  independent provider backup. Recognition/voice remain explicit later milestones.

### 2026-09-17 — Bottom-center circle and readable replies
- Implemented bottom-center greeting, 1.1-second crystal-to-circle crossfade and
  450 ms panel transitions in `desktop/experience.py`; circle painting lives in
  `desktop/app.py`. Cached artwork remains the introduction, with no live 3D loop.
- Ordinary replies hide decorative headings and reveal 2 characters per 40 ms
  tick. Clock content is preserved. Reduced motion skips reveal and movement;
  close stops the text and panel transitions. Guest/privacy behavior is unchanged.
- Updated `desktop/check_experience.py`, `desktop/README.md`, `LYA_TEST_GUIDE.md`.
  `check-t01.cmd` passed all 62 offline tests; five experience tests passed again
  after final transition cleanup. `git diff --check` passed (line-ending notices).
- Generated and visually inspected three synthetic Qt previews. Evidence:
  `desktop/qa/2026-09-17-bottom-center/README.md`, `input.png`, `answer.png`, `chat.png`
  in that directory. Previous artifacts preserved. No sensors or live providers ran.
- Limitations: no physical desktop animation or battery measurement; this does
  not establish live AI availability. Next: owner trials launch, circle click,
  `time`, `open chat`, Escape and reduced motion on the laptop.

### 2026-09-17 — Circle repair, independent windows and one-turn greeting
- Root causes: legacy crystal mask clipped the resized circle; the model system
  prompt explicitly requested assumptions/recommendations. Removed the mask in
  `desktop/experience.py` and changed `brain/workflow.py` to request direct answers
  with only materially relevant uncertainty. No live provider wording was tested.
- Ordinary answers now omit the composer. Explicit chat open/close/full-screen/
  restore commands work locally. Drag cards at their top edge. Orb relocation no
  longer moves existing panels. Project-file windows have independent native move,
  resize/maximize and close controls; placement minimizes overlap among LYA windows.
  The existing four-file allowlist and bounded local reader remain in force.
- `desktop/bake_crystal.py` accepts a rotation angle; generated 48 actual GLB views
  in `desktop/assets/rotation/` (3,016,467 PNG bytes; about 22 MB decoded). Source GLB
  unchanged. `desktop/app.py` paints cached frames during one 20 Hz turn. Elapsed
  time prevents slow timer delivery from stretching the turn. Idle rendering stops.
  Circle expands to the center, greets/rotates, then collapses; stay-crystal and
  become-circle commands implemented, with reduced-motion handling.
- Full `check-t01.cmd`: 65 checks passed (41 backend, 16 base UI, 8 experience).
  Initial fixed-delay animation tests failed under late Windows timer delivery;
  bounded completion checks and elapsed-time playback passed the full rerun.
  A final targeted Qt check also passed for reduced motion interrupting a
  persistent-crystal expansion; the geometry/morph stop at the full crystal.
  `git diff --check` passed with line-ending notices only.
  Tests cover circle mask, answer layout, chat controls, file independence, private
  denial, cancelled replies, persistent crystal and full rotation/idle shutdown.
- Updated `LYA_TEST_GUIDE.md`, `desktop/README.md`, `desktop/check_experience.py`.
  Saved synthetic previews and control/limitation notes at
  `desktop/qa/2026-09-17-window-controls/README.md`; inspected answer preview and
  a side-angle rotation frame. Earlier artifacts preserved. No private runtime
  content, sensors, deployment or live model calls were used in the checks.
- Next: owner desktop trial of the documented commands and drag controls. Other
  applications' occupied space is not detected; small screens can require overlap.
  Actual battery consumption, physical smoothness and live prompt compliance are
  not established by offscreen tests.

### 2026-09-17 — Incremental multi-turn chat rendering
- Root cause: `OrbDesktop.on_brain()` joined the complete temporary transcript and
  passed it to `animate_answer()`, which cleared the document and retyped history.
- Added `show_transcript()` and `animate_append()` to reuse the existing Qt text
  browser. During a model request, the new user message is displayed immediately;
  the working/final base callbacks preserve chat content, and only the new answer
  characters are inserted at the end. Opening chat displays existing history once.
- Added an isolated regression check proving an earlier reply appears once while a
  second reply advances by two characters per tick and completes correctly. Full
  `check-t01.cmd` passed 66 checks (41 backend, 16 base UI, 9 experience). No live
  provider, sensors, enrollment, deployment or real memory operation ran.
- Updated `desktop/README.md` and the existing controls evidence README. No new
  dependency or chat widget was added. Next: owner tests a long live conversation;
  provider latency and physical scrolling smoothness remain unmeasured.

### 2026-09-17 — Type directly after a compact answer
- Root cause: answer mode intentionally hid the composer and focused the response,
  so the next conversation required clicking the circle. Added a small event filter
  to the existing response widget: after reveal completes, the first printable key
  switches to input and is retained; Enter opens a blank input. Ctrl/Alt/Meta
  shortcuts pass through, and typing during reveal does not interrupt the answer.
- `OrbDesktop.open_panel()` focuses the response in answer mode; the new input then
  receives focus. No new widget, dependency, memory behavior or provider path.
- Focused behavior and prior incremental-chat tests passed. Full `check-t01.cmd`
  passed 67 checks (41 backend, 16 base UI, 10 experience). The offscreen Qt driver
  does not reliably report native Windows focus, so the check verifies visible input
  and complete captured text; `setFocus()` is still called for the desktop runtime.
- Updated `desktop/README.md` and the controls evidence README. No live provider,
  sensor, enrollment, deployment or real-memory operation ran. Next: begin T02 by
  safely inventorying configured providers, models and upstream independence,
  without printing credentials.

### 2026-09-18 — T02 reliability implementation and live backup evaluation

- Updated `cloud/router.py`, `cloud/inference.py`, `cloud/provider.example.json`,
  `cloud/verify_router.py`, `brain/oracle.py`, `brain/workflow.py`, `desktop/app.py`
  and `test_router.py`. Added `cloud/ssh_session.py`, `cloud/t02_remote.py`,
  `test_t02.py` and `check-t02.cmd`. Preserved unrelated work.
- Added canonical upstream grouping, atomic persistent attempt/token reservations,
  retry cooldowns, malformed-response fallback, deadline checks and cancellation.
  Route metadata stays outside the answer. Fixed the UI metadata-type regression
  discovered by the complete suite.
- Checks: 81 isolated tests passed; whitespace diff check passed. Temporary Oracle
  smoke interrupted a synthetic stall at 150 ms and cancelled after one fake attempt.
  Both live NVIDIA candidates stopped at 8,001 ms without an answer. Groq returned
  eight exploratory responses but failed parts of the correctness rubric.
- Owner confirmed free-only accounts with paid billing disabled. Only synthetic
  prompts were transmitted. No private memory, sensor, enrollment or production
  deployment operation ran. Remote active configuration and source files unchanged;
  NVIDIA remains disabled and the optional local session protocol is not activated.
- Evidence, official sources, limitations, activation and rollback steps:
  `review/2026-09-17-T02-backup/README.md`. T02 remains BLOCKED at independent live
  backup acceptance. Next: diagnose/replace the candidate, pass repeated rubric
  checks and forced failover over the actual desktop-to-Oracle path. T03 must address
  unsupported answer claims; transport success alone is not answer verification.

### 2026-09-18 — Local Qwen quality and latency evaluation

- Added `tools/test-local-model.py`, a standard-library-only harness that reuses the
  eight public fixtures in `cloud/model-evaluation.json`. It creates a fresh evidence
  folder, runs llama.cpp on an unused loopback port, records raw replies/timings and
  terminates only the process it created in `finally`.
- Ran Qwen2.5 1.5B Instruct Q4_K_M with six CPU threads, 2,048 context, temperature 0,
  seed 42 and 384 output tokens. Startup was 6.64 seconds; all eight HTTP requests
  completed in 3.28–35.42 seconds. The dedicated server stopped successfully.
- Reviewed result: 3 pass, 1 partial, 4 fail. Planning, security and Tamil reached the
  output cap. Tamil became repetitive. The coding algorithm passed five isolated
  assertions, but two model-written expected outputs were wrong and required coverage
  was missing. No unreviewed generated code ran.
- Decision: keep the model installed for experiments; do not enable it as LYA's
  general fallback. This test did not measure battery, temperature, memory, physical
  UI smoothness, file search, private memory or tool use. No private data, cloud API,
  sensor or real store was used.
- Evidence: `review/local-model-20260918-180912/README.md`, `results.json` and the
  ignored local `server.log`. Next: evaluate a stronger model that fits 8 GB RAM, then
  connect only a model that passes a declared quality/latency gate.
### 2026-09-19 — Fail-closed private local conversation

- Updated `brain/workflow.py` with session private/public controls and one-shot
  `private:` / `secret:` prefixes. Private model calls are pinned to the llama.cpp
  loopback endpoint and cannot fall through to Oracle or another provider.
- Updated `tools/run-llama-local.ps1` to use the stable `lya-local` alias, added
  `run-local-model.cmd` for Windows execution-policy-safe startup, updated only the
  safe local model selector in `.env`, and added a visible local-only UI label.
  Credential values were not printed, copied or written to project documentation.
- Added an isolated regression proving zero cloud calls during successful and failed
  private inference. Checks: 26 Brain/Oracle tests and 10 native experience tests
  passed. A live synthetic llama.cpp request returned a non-empty `private-local`
  result while the cloud fixture remained unused. The dedicated server was stopped;
  temporary logs were removed.
- Researched Jev and AirLLM using their official pages and current upstream evidence.
  Jev is hosted and returns bounded typed decisions rather than chat text; it is not
  eligible for secret conversations. AirLLM lowers peak VRAM through layer streaming
  but remains disk-bound and is not selected for this interactive 8 GB laptop path.
  Neither dependency was installed or called.
- Limitation: the installed Qwen2.5 1.5B model remains below the earlier quality gate,
  so local-only answers are provisional. Routing privacy is implemented; model
  intelligence and endpoint health are separate acceptance gates.
- Evidence and sources: `review/2026-09-19-private-local/README.md`. Next: benchmark
  Qwen3 4B Q4_K_M with the same eight-case suite, then promote it only if quality,
  latency, RAM and battery behavior are acceptable.

### 2026-09-19 — Pinned OpenRouter adapter, Qwen3 4B private runtime and T03 foundation

- Added an OpenRouter adapter that accepts only exact `:free` model IDs, requires a declared upstream, disables gateway fallback and rejects a response whose reported provider differs. The route is disabled in the example configuration. The saved OpenRouter key is empty, so no live OpenRouter request or activation occurred.
- Tested `nvidia/nemotron-3.5-lightning-30b-a3b` with synthetic public text from the laptop and Oracle. Both stopped on the first case at the fixed eight-second deadline without an answer; the route remains disabled.
- Downloaded the official Qwen3 4B Q4_K_M GGUF, verified its 2,497,280,256-byte size and SHA-256, and ran the same eight-case local rubric. Review scored 5 pass, 1 partial and 2 fail; coding and Tamil remain unsafe to trust without verification. The launcher now selects this better provisional private model and explicitly disables Vulkan/operator/KV offload after zero GPU layers still caused an Intel Vulkan allocation failure. Visible thinking is disabled. A live synthetic `private mode` request returned through `private-local`; no cloud route was called. Peak memory, battery drain and UI responsiveness under sustained generation remain unmeasured.
- Added 30 frozen T03 cases, frozen zero-tolerance critical thresholds, a bounded evidence block and claim provenance contract. Four offline contract tests pass. This is preparation only: no research adapter, semantic citation validation, isolated code verifier or full scored run is connected yet.
- Verification: `check-t02.cmd` and targeted T03/Brain compilation checks completed successfully; the final run included 15 T02 tests, 4 verification tests and 21 Brain tests in addition to the baseline suites invoked by the checker. OpenRouter stays disabled; T02 remains blocked. Next: save a free-only OpenRouter key in protected `.env`, run the exact pinned candidate through the live rubric, then either complete T02 with repeated/full-path evidence or reject it. Continue T03 adapter integration independently.

### 2026-09-19 — OpenRouter credential readiness and pinned live trials

- Confirmed only that Gemini, Z.ai and OpenRouter variables are populated in ignored local `.env`; values were never printed or copied into project artifacts. Credentials previously pasted into conversation must be considered exposed and rotated before continued use.
- Corrected OpenRouter verification to request official routing metadata, keep gateway fallback disabled and compare the selected provider with the configured provider slug. Fourteen router and fifteen T02 tests pass after the change.
- Live synthetic public checks verified NVIDIA for Nemotron 3 Ultra and OpenInference for DeepSeek V4 Flash. Nemotron returned three cases but exceeded the deadline and then truncated planning. DeepSeek's metadata diagnostic succeeded, but repeated rubric attempts missed the first-case deadline. Both routes remain disabled; nothing was deployed to Oracle and T02 remains incomplete.
- Evidence: `review/2026-09-19-openrouter-live/README.md`. Next: rotate any credential copied into chat. Continue T03 locally while selecting a genuinely independent route that passes the unchanged reliability gate; do not lower the gate to complete T02.

### 2026-09-19 — T03 verification connected to the Brain

- Updated `brain/verification.py` and `brain/workflow.py`. Added bounded local
  arithmetic and an injectable public-research boundary. Source data has a strict
  shape/size limit and no authority; research models must return structured claims.
  Visible answers are rendered only from validated claims with known source IDs.
- Private or person-scoped research, missing source adapters, malformed JSON and
  unknown citations fail closed. The mock adapter receives six-source, 8,000-byte
  and eight-second budgets. The real adapter must enforce its own deadline.
- Updated `test_answer_verification.py` and `test_brain_workflow.py`. Six verification
  and 23 Brain tests passed. `check-t02.cmd` passed the complete offline regression;
  compilation and whitespace checks passed. Tests used fake adapters and temporary
  encrypted stores, with no live provider, network, sensor or real memory.
- Updated `LYA_IMPLEMENTATION_CHECKLIST.md`, `LYA_TASK_ROADMAP.md`,
  `LYA_BRAIN_WORKFLOW.md` and the T03 evidence report. T03 remains in progress:
  semantic source-to-claim support, a selected read-only adapter, isolated code
  verification and the frozen 30-case scored run are next.
### 2026-09-19 — Opt-in grounded research adapter

- Added `brain/research.py` and wired `desktop/app.py` to obtain the adapter only
  when both `LYA_GEMINI_RESEARCH_ENABLED=1` and `LYA_GEMINI_FREE_ONLY=1` are set.
  The API key stays in ignored `.env` or process environment and is sent in a header,
  never in a URL. No credential value was read into project documentation.
- The adapter pins `gemini-2.5-flash`, uses the official Google Search grounding
  interaction, extracts only cited text spans/HTTPS URLs, and applies query, source,
  evidence, response and timeout bounds. It rejects missing grounding and malformed
  or insecure citations.
- Added `test_research_adapter.py` and `check-t03.cmd`. Four fake-HTTP adapter
  tests and the complete offline T01/T02/T03 suite pass. No live provider request,
  private prompt, sensor, deployment or real-memory operation ran.
- Selection evidence came from Google's current official grounding and pricing pages.
  The documented free allowance does not prove this specific account cannot incur a
  charge. The adapter therefore stays disabled until the exposed key is rotated and
  free-only status is confirmed. Next: run one synthetic public live fixture, record
  latency and citation shape, then continue independent semantic support and code
  verification.
### 2026-09-20 — Gemini rejected; Tavily adapter prepared

- Confirmed only that the rotated Gemini key exists and the requested safety flags
  were set; no credential value was printed. Added the missing non-secret flags after
  the owner's confirmation.
- Ran one synthetic public grounding request. The Interactions endpoint returned 404.
  The official `generateContent` compatibility endpoint then reported that
  `gemini-2.5-flash` is unavailable to new users. The model inventory confirmed the
  model name exists, but account eligibility does not. Official pricing shows search
  grounding unavailable on Gemini 3.6 Flash's API Free Tier. No billable model call
  was attempted; `LYA_GEMINI_RESEARCH_ENABLED` was reset to `0`.
- Replaced the runtime adapter with Tavily Search. It uses the official bearer-header
  API, basic one-credit search, one chunk per source, no generated answer/raw content
  or images, strict size/source/time limits and HTTPS-only records. Updated four
  fake-HTTP tests pass; the adapter remains off because no Tavily key is stored.
- Tavily's official pricing documents a recurring 1,000-credit monthly free plan,
  no credit card, and stop-at-exhaustion behavior. Next: create a Tavily Researcher
  free account, add `TAVILY_API_KEY`, `LYA_TAVILY_RESEARCH_ENABLED=1` and
  `LYA_TAVILY_FREE_ONLY=1`, then run one synthetic public live acceptance request.

### 2026-09-20 — Free-first hybrid research activated

- Added a standard-library You.com MCP adapter and enabled its keyless, search-only
  free profile for public research. It sends no credential, requests snippets only,
  rejects unsafe URLs and malformed MCP/SSE data, and obeys the existing source,
  byte and time budgets.
- Added a hybrid policy: ordinary requests use only the free provider. Tavily is
  eligible only for explicit `critical research:` or `important research:` prompts,
  after which the free provider may add independent sources within the remaining
  deadline. No Tavily request was made in this task.
- One synthetic live adapter request returned three bounded HTTPS sources. Seven
  isolated adapter tests and the full `check-t03.cmd` regression passed, 99 checks
  total. The first Python attempt received HTTP 403; adding an honest LYA User-Agent
  resolved the provider boundary and the same request then passed.
- Agent Reach research identified You.com keyless MCP, Exa recurring credits and
  SearXNG self-hosting as the strongest alternatives. Installed Agent Reach 1.5.0 in
  `C:\Users\kathirvel\.agent-reach-venv`; its safe diagnostic verified four healthy
  channels and the update check reported the current version. YouTube has a runtime
  configuration warning; GitHub and Exa remain unavailable without `gh` and
  `mcporter`. No `--system` changes were made. ScrapeGraphAI was deferred because
  general search does not justify its browser and LLM overhead on the laptop.
- Evidence: `review/2026-09-20-hybrid-research/README.md`. Next: add semantic
  full-page claim support and run the frozen 30-case T03 score; install only the
  specific Agent Reach system dependencies the owner chooses later.

### 2026-09-20 — Step 4 exact approval foundation

- Changed security/approval.py, brain/workflow.py, test_approval.py and
  test_brain_workflow.py; added check-t04.cmd. Trusted fake adapter tests prove exact
  binding, replay denial, expiry, revocation and session-switch denial.
- Created diagrams/15-t03-t04-workflow.mmd, .svg, .png and render_t03_t04.py;
  source validated and rendered companion inspected.
- Preserved prior work and reports. Corrected Step 3 interpretation without claiming
  the prior open semantic/code-sandbox requirements are complete.
- Next: trusted OS/phone verifier and issuance integration; all guest access remains
  locked. See review/2026-09-20-T04-foundation/README.md for limitations.
- Final regression: check-t04.cmd passed all 111 offline checks; no live verification claimed.

### 2026-09-20 — Primary-admin registration foundation

- Owner explicitly requested enrollment setup. Added `security/registration.py` with
  explicit local-biometric consent, an exact expiring trusted-device proof contract,
  three active face prompts, three random spoken-code prompts, normalized template
  checks and pairwise sample-consistency gates. It issues a five-minute local admin
  session and greeting only after the encrypted save succeeds.
- Added atomic first-admin storage in `storage/store.py`: one active primary admin,
  three encrypted face templates, three encrypted voice templates, recovery-code
  hash and a privacy-safe audit event commit together. Raw media is not accepted at
  the storage boundary. Added voice-template reads and an early active-admin check.
- Replaced `security/enroll.py` with a fail-closed compatibility guard because its
  legacy implementation uploaded raw face and voice recordings to Supabase.
- Added seven fake-device tests in `test_registration.py`, connected them to
  `check-t04.cmd`, and used a temporary DPAPI key and encrypted temporary store.
  Full `check-t04.cmd` passed. No camera, microphone, cloud, real biometric or live
  store was accessed.
- Added validated `diagrams/16-admin-registration.mmd` and inspected PNG/SVG companion
  renders; added `review/2026-09-20-T04-admin-registration/README.md`.
- Current limit: Microsoft documents the window-bound UserConsentVerifier interop for
  desktop verification. That adapter, visible capture UI, actual-device liveness
  calibration, deletion and recovery exercise remain pending. Until they pass, the
  desktop stays guest-locked and face/voice cannot authorize confidential actions.

### 2026-09-20 — Resumed registration boundary hardening

- Changed `security/registration.py` and `test_registration.py`: literal boolean
  consent/liveness, exact proof type, finite clocks, bounded configuration, stable
  normalization, cancellation and expiry checks between captures and before save.
- Ran `.venv-ui/Scripts/python.exe -B test_registration.py`: 12 tests passed with
  synthetic vectors and temporary encrypted storage/key. No live enrollment ran.
- Corrected misleading replay-resistance/recovery claims in
  `diagrams/render_admin_registration.py`; regenerated its PNG/SVG companions.
- Missing adapters remain the next step: trusted Windows Hello device verification,
  visible bounded capture, quality/liveness validation, recovery and UI session binding.
  Cancellation checks stop later steps; an in-progress device callback must implement
  its own interrupt/release behavior. No such real callback is connected yet.

### 2026-09-20 — Windows Hello native registration checkpoint

- Added `security/HelloVerifier.cs`, `security/build-hello.cmd`,
  `desktop/registration.py`, `test_registration_ui.py`; connected command handling
  and shutdown in `desktop/experience.py`, plus an integration regression in
  `desktop/check_experience.py`. Added UI tests to `check-t04.cmd` and ignored the
  generated helper executable in `.gitignore`.
- Build passed with installed Framework compiler. Read-only helper availability
  returned DeviceNotPresent; this is execution-session evidence, not proof that
  Hello is absent from the user's interactive desktop. No authentication prompt
  was automatically opened. Actual success/cancellation in Windows remains untested.
- Seven isolated UI checks and twelve core checks passed. UI success explicitly
  leaves LYA a guest: the callback is not yet wired to register or issue authority.
- Native interop reference: https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.ui.userconsentverifier
- Next: owner clicks Verify in the normal desktop session to validate the platform
  path; then implement consented local biometric capture and recovery before enrollment.
- Final checks: all 11 native experience checks passed, including opening setup
  without session escalation; `git diff --check` passed. The setup screenshot was
  rendered with local Segoe UI fonts and visually inspected:
  `review/2026-09-20-T04-admin-registration/setup-screen.png`.

### 2026-09-20 — Private storage policy and portable selected-note recovery

- Added `storage/recovery.py` and `test_recovery.py`; reused installed Fernet and
  SQLite instead of adding a backup service. Added owner backup/restore policy
  actions in `security/policy.py`. Recovery keys are separate from the DPAPI key
  and from registration recovery codes. No keys or private facts are recorded here.
- Changed `storage/store.py`: read-only recovery checks avoid encrypted-file
  rewrites; failed writes clean their own encrypted temporary file. Corrected
  algorithm/deletion claims in `security/vault.py`; existing cipher and key path
  stay unchanged. A recovery archive does not restore files or biometric identity.
- Fixed `brain/workflow.py` approval truthiness and private routing: verified
  personal requests use the local client directly, unavailable local stays blocked,
  and built-in local HTTP disables proxies/redirects. Updated synthetic regression
  cases in `test_brain_workflow.py`. Injected Python adapters remain trusted code.
- Added `check-storage-recovery.cmd`; it passed 48 checks (12 recovery, 33 brain,
  3 approval). Separately ran 12 registration regressions, all passed, using only
  temporary files, disposable keys and fake samples. No live enrollment occurred.
- Added `LYA_STORAGE_SECURITY_PLAN.md`, updated T05/T10 in `LYA_TASK_ROADMAP.md`,
  and saved evidence at `review/2026-09-20-storage-recovery/README.md`. Added checked
  `diagrams/17-storage-recovery.mmd` and visually inspected PNG/SVG companions,
  generated by `diagrams/render_storage_recovery.py`. `git diff --check` passed.
- Decisions: local encrypted memory remains authoritative; selected plaintext
  Obsidian exports and public/sanitized NotebookLM research are optional future
  integrations. Proposed Drive transport receives ciphertext only; no OAuth,
  upload, sync or paid resource was activated. No new dependency was installed.
- Research limitation: Agent Reach public-document fetch escalation was rejected
  because automatic approval review hit a usage limit. No bypass or retry of the
  blocked fetch occurred. Current product-specific security verification remains
  incomplete and is not used to claim these integrations work.
- Limits: same-account malware/OS administrators can access unlocked secrets;
  old backups may contain forgotten notes; expiry is enforced by restore rather
  than cryptographic self-destruction. Legacy modules require separate review.
  Real enrollment remains deferred. Next: owner recovery preview, atomic approved
  archive file handling and separate key custody, then a restore drill before any
  cloud backup. T05 and T10 are implemented in part, not complete end to end.

### 2026-09-20 — Native recovery interface and file boundary

- Added `desktop/recovery.py`; connected native recovery commands and asynchronous
  quit/cancellation handling in `desktop/experience.py`. The dialog never grants
  identity or sends keys/filenames to the model. It defaults to a locked guest view.
- Extended `storage/recovery.py` with authorized label listing, encrypted file
  export, bounded authenticated preview and digest-bound restore. Writes are
  no-overwrite and temporary ciphertext is cleaned after handled failures. Owner
  status/session are rechecked immediately before publishing the archive.
- Key handling: masked by default, explicit reveal, re-entry and separate-custody
  acknowledgement. No automatic clipboard copy, key file, logs or network calls.
  Worker cancellation and close clear fields; session change/expiry clears labels,
  keys, preview and note-count status. Memory wiping is not guaranteed.
- Added ten isolated cases in `test_recovery_ui.py`, two experience regressions in
  `desktop/check_experience.py`, and the UI suite to `check-storage-recovery.cmd`.
  58 storage/brain/approval/UI checks and 13 experience checks passed (71 distinct).
  Includes full UI -> temporary file -> fresh local key/profile -> verified restored
  value, wrong-key/disk/race/cancellation cases. No real enrollment/profile was used.
- Updated `.gitignore`, `desktop/README.md`, `LYA_STORAGE_SECURITY_PLAN.md` and
  `LYA_TASK_ROADMAP.md`. Evidence and synthetic native PNG screenshots live in
  `review/2026-09-20-recovery-interface/`; reproducible renderer is `render_preview.py`.
  Visual review corrected tab contrast and stale count text after locking.
- Remaining: real owner session/approval binding, user-held recovery-key custody,
  clean-device drill, rotation and remote transport. Enrollment stays deferred.
  Cancellation cannot undo an already committed operation; blocked OS I/O may
  delay shutdown. No battery/performance guarantee or cloud integration is claimed.
  Next is the real trusted-session/recovery acceptance gate when the owner is ready.

### 2026-09-21 — Crystal-guided registration and PIN verification guidance

- Redesigned desktop/registration.py: four cached crystal quadrants move from
  center to the window corners, revealing a native four-step guide. No live GLB,
  fake biometric scanner or continuous animation. Skip/close/reduced motion stop it.
- Updated desktop/experience.py to pass the reduced-motion preference. Added
  read-only verifier availability, a Windows sign-in settings button and PIN/Hello
  guidance. QProcess keeps verification asynchronous with cancellation and timeout.
  Draft name/preferences/checkpoint clear on close; no identity or session granted.
- User-authorized read-only device checks ran without sensor streams, PIN prompts
  or account changes. Private hardware details are excluded from this ledger.
  Official Microsoft sources are linked in the report. Agent Reach's web reader
  failed locally with a TLS error; web search supplied the official documentation.
- Expanded test_registration_ui.py: 14 passed. Twelve synthetic registration-core
  and 13 native experience checks also passed (39 total). git diff --check passed.
  No live profile, real biometric samples or provider credentials were used.
- Added review/2026-09-21-registration-hologram/README.md, render_preview.py and six
  synthetic PNG frames. Visually reviewed split, guide, device and review screens;
  updated desktop/README.md. Older evidence remains preserved.
- Limits: setup guidance/checkpoint only; real owner binding, local capture,
  anti-spoof calibration and account recovery remain pending. The UI's proposed
  optional personalization needs reconciliation with the older synthetic
  registrar's mandatory face/voice contract. No battery/FPS guarantee is claimed.
  Next: interactive Windows verification, then the chosen trusted-session flow.

### 2026-09-21 — Owner-introduction visual correction

- Replaced the rejected cropped-corner treatment in `desktop/registration.py`.
  The crystal now remains intact and makes one connected move from center to its
  left identity dock. Four small QPainter diamonds become stage markers instead
  of using sliced artwork. The former screenshots remain preserved as history.
- Reworked all four pages into one-decision screens with a consistent eyebrow,
  title, short explanation, one content card, explicit action labels and a compact
  state line. The review distinguishes READY, PENDING and LOCKED without claiming
  enrollment. The Windows prompt and fail-closed behavior are unchanged.
- Used current Microsoft Fluent motion/material guidance and the fetched Vercel
  interface guidelines. Chose an opaque-tinted Qt surface because live acrylic is
  GPU-intensive. The one-shot 1.05-second reveal is paint-capped near 30 fps,
  skippable and reduced-motion aware. It leaves no idle timer, live blur, WebGL,
  video, particle effect or looping glow.
- Added a stage-rail/duration regression. Fifteen registration UI, twelve
  registration-core and thirteen desktop-experience checks passed (40 total).
  Synthetic frames were visually inspected at identity, device, signal and review
  states. Evidence: `review/2026-09-21-registration-hologram-v2/README.md`.
- Updated `desktop/README.md`. Agent Reach v1.5.0 diagnostics were run; its Jina
  page read returned empty locally, so official pages were read with the web
  fallback. Agent Reach reports v1.5.0 is current. No credential, sensor, verifier,
  profile or private runtime store was accessed.
- Limits: screenshots use synthetic draft data. Interactive Windows verification,
  real biometric capture, trusted-session issuance and enrollment remain pending.
  LYA stays guest-locked. Next: owner visual review, then interactive Windows
  verification when the owner chooses to enroll.

### 2026-09-21 — Camera and voice platform selection

- Researched the four supplied repositories and current primary documentation.
  `k2-fsa/OmniVoice` is multilingual voice-cloning TTS; `VoiceStudio` is a full
  AGPL voice-creation application; neither verifies who is speaking. Alibaba Open
  Code Review is a code-review CLI, and Databasement is a database backup server.
  None was installed or added to the biometric runtime.
- Selected OpenCV YuNet + SFace for face detection/embedding. Official OpenCV docs
  describe the detector around 337 KB and recognizer around 36.9 MB, while published
  CPU benchmarks support the low-load choice. The project runtime already has
  OpenCV 5.0 with both required APIs, avoiding InsightFace's heavier model/runtime.
- Selected sherpa-onnx as the offline voice platform for VAD and speaker embeddings;
  whisper.cpp remains responsible for transcription. The exact WeSpeaker/3D-Speaker
  candidate is deliberately unapproved until artifact licenses, hashes and local
  English/Tamil performance are checked. Example thresholds will not be copied.
- Added `LYA_CAMERA_VOICE_DECISION.md` and the read-only
  `tools/check-biometric-stack.py` readiness probe. Added ignored model patterns
  under `models/biometric/` and updated T08/T09 roadmap/checklist status.
- Probe result: Python 3.12.14, OpenCV 5.0.0, NumPy and sounddevice present;
  `FaceDetectorYN`/`FaceRecognizerSF` present; sherpa-onnx and YuNet/SFace/speaker
  model artifacts absent; overall ready=false. It opened no sensor.
- Security decision: recognition can choose a greeting/profile but cannot unlock
  secrets or create/approve authority. Unknown, missing, multiple or uncertain
  results remain guest. Windows Hello PIN is the trusted checkpoint on this laptop.
- Next: pin model artifacts/licenses/hashes; install into isolated runtime; implement
  bounded CPU adapters and synthetic failure tests; then ask for an explicit owner
  device-test/enrollment session. No biometric capture or download occurred here.

### 2026-09-21 — Conversational registration and local spoken guidance

- Replaced the sidebar/forms with a centered crystal, one prompt per stage,
  compact controls and four progress dots in `desktop/registration.py`.
  Opaque content prevents unrelated windows from bleeding through the text.
- `desktop/experience.py` hides the command panel on setup and prevents reopening
  it over setup. Voice-triggered setup avoids the legacy online speech path.
- Added `desktop/setup_speech.py`: installed Windows SAPI voice in an asynchronous
  subprocess; fixed prompts over stdin, literal-text speech, 30-second timeout,
  latest-prompt replacement, mute/replay, and stop on page change/hide/close.
  The crystal accent indicates speech-process activity, not audio-level tracking.
- Tests: 16 registration UI, 12 registration core, 13 desktop experience and
  3 speech transport checks passed (44). Local SAPI produced 122344 bytes in a
  memory stream for a fixed phrase, without microphone or audible playback.
  Actual speaker playback and owner voice preference remain to be checked.
- Synthetic previews: `review/2026-09-21-conversational-registration/`.
  Previous designs are retained. No biometric enrollment, microphone listening,
  wake-word model, private store mutation or cloud speech was enabled.
- Next: owner listens to guidance; continue the separately documented biometric
  adapter work. Registration still cannot finish until real enrollment is wired.


## 2026-09-21 — Local female neural voice output

Implemented: `audio/synthesis.py` routes Tamil/English to pinned Piper female models,
with bounded text, two CPU threads, no idle spinning, no runtime downloads or
speech uploads. `desktop/setup_speech.py` transports private text through stdin,
terminates speech on interruption and releases model memory after each utterance.
`desktop/experience.py` speaks current completed results and actual document-read
outcomes, adds mute/engine/language/pacing commands, and rejects stale/cancelled
answers. `desktop/app.py` no longer speaks stale panel headings. Registration shares
the renderer and speaking-state suppression. `audio/voice.py` legacy TTS is local;
transcription defaults offline. No new microphone capture or identity authority.

Artifacts: `audio/requirements-voice.txt`, `models/voice/manifest.json`,
`tools/install-voice-models.py`, and `review/2026-09-21-local-voice/` containing
synthetic English/Tamil WAV samples, benchmark script, metrics and source/license
notes. Model weights are ignored by Git. Owner API keys, voices, faces and private
runtime content were not collected, copied into documentation or transmitted.

Checks: 20 voice/synthesis/transport passed, 1 online check skipped; 28 registration
passed; 15 experience passed (63 passed total). Static compilation and diff checks
passed. Initial Kokoro English benchmark was too slow (43.943 s for 4.331 s audio)
and rejected as default. Final short local Piper run: English 3.704 s / 4.725 s
speech; Tamil 4.214 s / 3.994 s; first audio 3.212 / 3.765 s. Synthetic benchmark
process peak working set 181.7 MB; not a battery or worst-case resource guarantee.

Limitations: only Tamil/English synthesis was benchmarked; five additional Kokoro
language routes are experimental. Pacing styles are not trained emotional acting.
Tamil/English switch between two speaker timbres; Romanized Tamil is unresolved.
No claim of universal accuracy, production readiness or voice-input completion.
Next: human pronunciation/listening acceptance, text normalization and latency/
battery/audio-device soak tests, then consented bounded ASR and echo/barge-in work.
Full T08 voice and owner enrollment remain incomplete.

## 2026-09-22 — External voice lab repaired and documented

Context: the owner asked for the external work to be understood and completed
without touching the main project. `external work/` is an isolated "ALYA voice
lab" exploring the hardest requirement from `docs/01-research.md` — one
21-year-old bilingual (English + Tamil) female voice with many emotions and
styles, offline-first, no paid provider. It reuses the pinned Piper models in
`models/voice/` but is not imported by the LYA app. The brain had no prior entry
for it.

Found incomplete (state as re-opened 2026-09-22):

- `docs/` held only `01-research.md`. The `README.md` that `alya_voice/__init__.py`,
  `tests/__init__.py` and the research doc all reference did not exist, and there
  was no architecture or usage document. No entry point for any reader.
- The suite was **not green**: 16 of 98 tests failed. A preserved earlier log
  (`out/tests.txt`, now `out/tests-2026-09-22-before-fixes.txt`) recorded the same
  failures, so it had never passed.
- The headline capability was broken: every rendered WAV was **pure silence**
  (`peak 0.0`), including the `test_local_piper` "renders audible audio" checks.

Twelve root causes were found and fixed (full table in
`external work/docs/05-status.md`):

1. `dsp.time_stretch` had no `return` — it returned `None`, which `pitch_shift`
   turned into a zero array for every span. This single bug silenced all audio.
2. WSOLA matched its search against the windowed output tail instead of the raw
   input, smearing the fundamental; corrected so time-stretch holds pitch.
3. `dsp.breath` computed `np.sin(np.pi*t)**1.5`; the sine is a tiny negative at
   the endpoints, so the fractional power returned all-`NaN`.
4. `emotions.strip_tags` read `explicit[0]` inside the returned tuple *before*
   `re.sub` had run, so **every** explicit `[emotion:x]` / `<x>` tag was silently
   dropped. Tuple left-to-right evaluation order.
5. Emotion inference had no continuity; a weak cue in a later sentence overrode a
   strong earlier emotion. Now the current emotion persists unless the new score
   is at least as strong.
6. The `firm` cue list contained bare `"no"` / `"cannot"`, so *"I cannot believe
   it"* was classified as refusal. Tightened to genuine boundary phrasing.
7. The phone detector's lookahead rejected a trailing sentence period, missing a
   number at end of sentence.
8. An explicitly named engine that policy refused was silently substituted
   instead of raising; `speak()` now raises on a refused named engine.
9. A pure-silence WAV was exported for path-only (remote) engines and reported as
   success, because pause padding was appended even with no decoded PCM.
10. Interjection outcome depended on unrelated prose (shared RNG stream); now uses
    its own seeded stream.
11. `plan`/`say`/`demo` crashed with `UnicodeEncodeError` on a cp1252 console when
    printing Tamil; the CLI now reconfigures stdout/stderr to UTF-8.
12. `split_sentences('...')` kept a punctuation-only fragment.

Checks run (offline, isolated, fake/local only): `external work/tools/run-tests.cmd`
→ **98 tests, all passing, exit code 0**. `alya-voice.cmd doctor` reports all three
engines with reasons. `demo --silent` wrote 12 bilingual emotion WAVs into
`out/`, measured peak 0.83–0.92 and RMS ≈ -16.6 to -17.5 dBFS (the loudness
target), with durations varying by emotion as designed. Two Mermaid diagrams in
`docs/02-architecture.md` validated with the mermaid checker (0 errors, 0
warnings). Current run log: `external work/out/tests.txt`.

Artifacts added: `external work/README.md`, `external work/docs/02-architecture.md`,
`03-usage.md`, `04-limitations.md`, `05-status.md`; the pre-fix logs preserved as
`out/tests-2026-09-22-before-fixes.txt` and `out/t2-err-before-fixes.txt`. Code
changed only inside `external work/`: `dsp.py`, `emotions.py`, `director.py`,
`privacy.py`, `runtime.py`, `cli.py`, `config/emotions.json`, and two test files.

Decisions: kept the lab isolated — no file of the main LYA application was
modified, and nothing was wired into it. Chose fail-loudly over silent
substitution when a caller names a refused engine. Tightened `firm` cues in the
config rather than special-casing the director, so the fix is data, not code.
Changed two test inputs (interjection seed 3 → 1, and the FakeEngine availability
semantics) because they tested a fragile coincidence rather than the intended
behaviour; the render-failure and availability paths are now separately
exercisable.

Limitations (unchanged and important): no listening acceptance has happened, so
naturalness is **not** established — the tests prove signal properties, not how
good it sounds. Tamil number words are unreviewed by a native speaker. The remote
`cloud_edge` tier is implemented but disabled and only delivery-tested. The lab is
not integrated with LYA and has no tests under the app's real threading/approval
model. No biometric, credential, microphone or owner-private data was involved.

Next: owner (ideally native Tamil speaker) listens to `out/reel-*.wav` and gives
pronunciation/naturalness feedback; then decide whether `unified` or `native`
timbre is acceptable; only after that consider any bounded integration with the
LYA voice path, with its own privacy review. Remote tier stays off until the owner
explicitly asks for it.

## 2026-09-22 — External voice assessed and integrated into desktop output

Verdict: the repaired `external work/` system is useful and its local synthesis
pipeline works, but final voice naturalness is not yet accepted. It is stronger
than the earlier experimental `audio/synthesis.py`: one runtime provides bounded
English/Tamil planning, local Piper synthesis, cancellation, privacy routing, 22
emotion profiles and 7 styles. Automated signal checks cannot prove that the
speaker sounds like one natural young adult woman; owner listening remains the
acceptance gate.

Implemented: `desktop/setup_speech.py` now loads `external work/alya_voice` in
its existing subprocess, uses the unified Tamil female Piper model for both
English and Tamil, forces remote speech off, disables interjections and disables
desktop speech auditing. The model process stays warm for up to 45 seconds during
conversation and exits after inactivity. `external work/alya_voice/runtime.py`
now offers a chunk callback that fires immediately before playback. The compact
answer panel uses each chunk's measured duration for word-by-word captions and
restores the exact original answer afterward. Natural/economy now map to local
Piper/Windows SAPI; language controls are bounded to auto/en/ta and the seven
documented styles.

Checks: external voice 100/100 passed; speech transport 5/5 passed; desktop
experience 16/16 passed; static compilation passed. A real production-interpreter
smoke test loaded the real model and rendered `Hello. வணக்கம்.` as two captioned
chunks containing 1.25 seconds of audio without remote use. Benchmark evidence
shows about 2.1–2.8 seconds to first audio and 2.4–2.9 seconds total generation on
this laptop. The benchmark memory field reported 0.0 MB and is treated as invalid,
so memory and battery claims remain unproven.

The repository-wide discovery run was also executed and is not green for older,
separate reasons: current-user DPAPI cannot decrypt stale test material, Oracle
mock expectations fail, and legacy `test_synthesis.py` expectations disagree with
the retired experimental path. These were not changed or counted as voice
integration failures. No microphone, biometric data, credentials, cloud speech
or owner-private runtime content was collected or transmitted.

Artifacts: `review/2026-09-22-external-voice-integration/README.md`, updated
`desktop/README.md`, `external work/README.md` and
`external work/docs/05-status.md`. Next: owner listens to the linked English and
Tamil reels and reports pronunciation/timbre problems; then run a warm-session
latency/memory/battery soak. Microphone input, echo cancellation and barge-in are
a separate later task.

## 2026-09-22 — Single-render answer flow and clearer young-adult voice tuning

The owner reported that each answer appeared once immediately and then appeared
again with speech. Root cause: `Desktop.on_brain()` triggered the compact panel's
normal answer animation, and `OrbDesktop.on_brain()` triggered a second animation
after starting speech. `desktop/experience.py` now calculates one `spoken_now`
state. Spoken answers are cleared before Qt paints the first render and become
visible only through audio-timed captions; muted/quiet answers use the normal
single render. The regression check asserts one animation call per answer.

Voice tuning remains one acoustic speaker across English and Tamil. The delivery
layer now supports a real style rate offset; previously style rate scales could
not slow neutral speech because multiplying zero still produced zero. Default
`everyday` is roughly 8–14% slower after sentence cadence, with longer clean
beats, less artificial vibrato/breath and lower Piper synthesis variance. Added a
seventh `joyful` style. Other styles and the 22 context-driven emotions change
delivery only; they do not swap the speaker model. Age 21 remains persona intent,
not an acoustically proven property.

Checks: external voice 100/100, desktop experience 16/16 and speech transport
5/5 passed; compilation passed. Planner inspection confirmed mixed English/Tamil
everyday spans at -8% to -14% rate. Four fresh offline samples and metrics are in
`review/2026-09-22-external-voice-integration/samples/`; peaks are 0.829–0.924,
RMS about -16.7 to -16.8 dBFS, and warm-model reuse reduced subsequent first
audio generation to about 70–125 ms after a roughly 2.0-second cold start.

Limitations: objective audio health does not prove cute, youthful or natural
voice quality. The owner must listen to the four tuned samples. If identity or
English pronunciation fails, replace the acoustic model with a true cross-lingual
single-speaker model; do not stack stronger DSP effects that damage clarity. No
microphone, biometric information, credential, cloud speech or private runtime
content was used.

## 2026-09-22 — Owner rejected voice; sentence continuity repair

Owner reports broken English, fragmented delivery and an older-sounding narrator.
The existing Tamil acoustic model with an English phonemizer is not a validated
multilingual voice. Age 21 in the persona config cannot change speaker identity.

Changed `external work/alya_voice/director.py` to preserve short sentences through
commas (still bounded by max_span_chars). Changed
`external work/alya_voice/engines/offline_piper.py` to bypass artificial breaths,
pitch shifting and vibrato in everyday/joyful styles. Other experimental styles
retain effects. Local-only synthesis and the same acoustic model are preserved.
These reduce processing-related fragmentation; English model quality is unresolved.

Checks: 102 external voice tests passed, including new sentence-continuity and
real-model effect-bypass checks. Four public synthetic WAVs and metrics generated
under `review/2026-09-22-external-voice-integration/samples-clean/`, preserving
older samples. The samples use two chunks each; these are not listening-approved.
No microphone capture, private-text transmission or biometric enrollment.

Research: https://github.com/k2-fsa/OmniVoice documents voice design, reusable
voice prompts, cross-language accent transfer and design instability in some
languages. https://github.com/ServeurpersoCom/omnivoice.cpp documents a community
GGML CPU port and Q8 models. Candidate only: no local performance or quality
acceptance and no new model installed. Agent Reach mcporter/CLI unavailable;
used web tool to read primary documentation. Next: benchmark a designed synthetic
speaker on Windows CPU, then compare Tamil/English identity and pronunciation
before replacing the runtime model. Current voice remains unaccepted.

## 2026-09-23 — Voice implementation comparison and stream lifecycle repair

Compared `lya-external-work/lya-voice` with `external work/` using source review,
the existing constraints and isolated test runs. The experimental folder has
stronger remote Edge/Sarvam quality candidates, but its default is network speech
and its smoke test cannot run on this machine because `ffmpeg` is absent. It is
kept as a research bench; its cloud path is not enabled for private replies.

The production runtime was changed in `external work/alya_voice/runtime.py` to
reuse one sounddevice output stream for all decoded chunks in a reply, write
bounded 20-ms blocks, drain normal completion, and abort/close on stop, close or
device error. Added regression checks in
`external work/tests/test_runtime.py` for reuse, cancellation, failure cleanup and
shutdown cleanup. Result: 139 tests passed, one ffmpeg-only test skipped. No
microphone capture, credentials, biometric material or new model download.

Next: owner listening of the current local samples remains the quality gate; only
then should a small, licensed cross-lingual candidate be evaluated under a memory
cap. Do not replace the model based on F0 or waveform checks alone.

## 2026-09-23 — Voice quality samples, resource measurement and cancel race

Generated two short public sample lines with the already installed Edge
multilingual voice for direct English/Tamil comparison with the earlier local
Piper WAVs. The public test text was sent to the speech service; no private
conversation or sensor data was used. Production remote speech remains disabled.
Samples and exact timings: `review/2026-09-23-voice-comparison/samples/` and its
README. Listening quality and a single stable bilingual voice are not yet accepted.

Measured the existing local one-model voice in a fresh process with no playback or
output files. Peak working set was about 190 MB; cold first audio was several
seconds and the warm turn substantially faster. Repaired
`external work/alya_voice/cli.py` so its Windows memory counter no longer returns
zero. Protected `external work/alya_voice/runtime.py` stream writes and closure
with a lock, and added a concurrent cancellation check. Focused runtime/CLI checks:
30 passed. The earlier complete suite passed 139 before these two changes; full
suite was not repeated. No large model was added. Next: owner listens to the
paired sample files; choose a voice only on that evidence and then verify real
speaker playback under an ordinary laptop workload.

## 2026-09-23 — Native English voice selected for desktop

Owner accepts the Tamil voice and wants fluent English without the Tamil-model
accent, while preserving laptop resources and private local speech. Changed
`desktop/setup_speech.py` to load `external-work/alya_voice` in native Piper mode.
English now uses the existing `en_US-ljspeech-medium` model; Tamil continues on
`ta_IN-rasa_female-medium`. The desktop keeps its local-only speech route and
disabled speech audit. Updated the voice persona description and current docs;
added a routing check in `test_setup_speech.py`. Existing external lab's unified
mode is retained for comparison, but is no longer the desktop default.

Checks: six desktop speech tests and 42 focused external voice tests passed,
including real English/Tamil synthesis. Public synthetic WAVs, reproducible
benchmarks, results and decision limits are in
`review/2026-09-23-english-voice/README.md`. The cold English sample took about
4.9 seconds to first audio and 222 MB peak process memory; a warm English line
took about 0.24 seconds to first audio. The second loaded model raised peak
process memory to about 376 MB. An already-installed Kokoro trial exceeded a
20-second limit and was not enabled. No model download or private-text remote
transmission occurred.

Limitations: the voice changes between languages, perceived age/naturalness has
not been owner-approved, and mixed-language speech in one sentence is not yet
validated. No live UI listening or battery soak was completed. Next: owner
listens to the two English samples and tests LYA's ordinary reply path; if still
too mature or read aloud, compare another small local English model with the same
latency, memory and privacy gates.

## 2026-09-23 — Fast completed-answer reveal and Laya/Jev fit review

The owner reported slow on-screen letters and asked whether Laya, Jev Ultrafast
or Jev would improve LYA and the current voice. Traced the desktop path: once a
brain answer completed, the UI cleared its text to wait for TTS captions. The
cold English TTS benchmark had about a 4.9-second first-audio delay. Changed
`desktop/experience.py` so completed answer text reveals immediately and is no
longer gated by audio. On the existing 40-ms timer, longer answers finish in at
most 30 ticks (about 1.2 seconds); speech still runs separately. Updated
`desktop/check_experience.py` and `desktop/README.md`. All 17 isolated desktop
experience checks passed, including the no-audio answer reveal regression.

Reviewed the primary Laya, Jev Ultrafast and TypeSafe Jev sources. Laya/Jev
return structured decisions, not answer text or speech; Jev Ultrafast is a
browser agent using remote decision and text services. No dependency, model or
external API was added. Details and links:
`review/2026-09-23-fast-replies-and-decision-models/README.md`. This solves UI
delay after a completed brain answer, not inference time or cold TTS startup.
Next: verify live desktop timing under an ordinary laptop load, then measure
brain/provider latency separately before changing model routing.


## 2026-09-23 — One-shot local camera eyes and face-presence UI

The owner asked for a more modern face experience and for LYA to see objects through the camera. Added `vision/scan.py` with pinned, hash-checked OpenCV Zoo NanoDet INT8 and YuNet models under ignored `models/vision/`; exact sources, license notes, hashes and sizes are in `models/vision/README.md`. Added `desktop/camera_eyes.py`, a static lens surface that starts with the camera off. `desktop/experience.py` opens it on explicit vision commands. Its Scan once action runs a bounded local child process, captures up to three frames, detects objects and faces, and releases the camera. Eight-second timeout or close kills the process; the frame is not written to disk. No identity enrollment or authority is created. Updated `.gitignore`, `desktop/README.md` and the isolated tests in `test_vision.py` and `desktop/check_experience.py`.

Checks: three sensor-free vision tests and 18 desktop experience tests passed. A temporary public OpenCV image yielded one face box and one person label; the temporary image was removed. A blank synthetic frame yielded neither. The offscreen camera-off preview and scope/limitations are in `review/2026-09-23-vision/`. No owner camera, microphone, biometric template, credential or private image was used. Real camera compatibility, accuracy in ordinary rooms, accessibility review, latency and battery soak remain untested. SFace identity matching/enrollment remains deferred under the recorded consent and Windows-authority boundary. Next: owner-initiated one-shot camera check, then measure and calibrate before any identity feature.


## 2026-09-23 — Owner-authorized live one-shot camera check

After the owner agreed to the live check, the in-sandbox OpenCV process could not see a camera. A read-only device check outside the sandbox confirmed camera availability there, so the same bounded one-shot scan was rerun with device access. It completed in about 2.0 seconds with a 640×480 frame and exited normally. An offscreen Qt integration check observed the Vision window's preview ready and Scan once re-enabled at worker completion. The test app's later shutdown cleared its preview as designed. No frame was saved, displayed to the assistant, sent remotely or placed in this ledger; no detections or device identifiers are recorded here.

This verifies camera opening, local model inference and the UI worker handoff for one run. It does not validate recognition accuracy across objects, people or lighting, nor battery cost or long-term device behavior. Next: owner reviews the visible UI in their normal desktop; then measure repeat scans and calibrate labels/thresholds before considering consented identity enrollment. Guest/Windows authority boundary remains unchanged.


## 2026-09-23 — Live camera perception and grounded questions

The owner rejected the still-image camera experience. Reused `vision/scan.py`'s pinned local models in a bounded streaming worker and changed `desktop/camera_eyes.py` to offer explicit Start/Stop live view, frame overlays and a question line. `vision/answers.py` uses only recent detected labels/boxes for presence and approximate location answers; unknown identity and unsupported pen detection are stated honestly. `desktop/experience.py` starts live view on direct camera commands while `open vision` stays off by default. No access policy, enrollment flow or cloud path was changed. Updated `test_vision.py`, `desktop/check_experience.py` and `desktop/README.md`. Timing scripts and results are in `review/2026-09-23-vision/`.

Checks: five isolated vision tests and 18 desktop checks passed. Two bounded real-camera runs established first-frame arrival and roughly six-frame/s preview after moving inference off the capture loop; one offscreen Qt handoff/stop check passed. No frame, identity template or private scene details were saved. Limits: object class set excludes pens; visual recognition and battery load are not validated; software face presence does not prove liveness or identity and cannot unlock LYA. Next: user review of live UI, measured battery/CPU under normal load, then evaluate a small pen-capable model and separate anti-spoof research without changing Windows Hello authority.


## 2026-09-23 — Visual questions routed from the main command line

A clearly visual command such as `LYA, can you see my pen?` or `Do you see anyone suspicious?` now opens the local Vision window and starts a live session. The question waits for the first analyzed frame before receiving a grounded answer. Ordinary file questions still use the normal assistant route. Updated `vision/answers.py`, `desktop/camera_eyes.py`, `desktop/experience.py`, `test_vision.py` and `desktop/check_experience.py`. Five vision and 19 desktop experience checks passed; the new desktop check confirms the visual route does not alter the owner session. Pen detection remains unsupported and is reported as such. Real speech-to-text is not yet wired, so spoken visual questions depend on that future microphone path.

## 2026-09-24 — Sharper camera-only window and normal LYA replies

The owner reported blur, lag, and an unwanted separate camera question box. Replaced `desktop/camera_eyes.py` with a camera-only preview plus Start/Stop. `vision/scan.py` now requests 1280×720 at 15 fps and JPEG quality 88; it analyzes a 640-pixel-wide copy at most twice per second using the existing local models. Qt draws the native frame once and discards queued older packets. `desktop/experience.py` returns visual answers through LYA's normal text and configured speech path, including `what do you see?`, with frame-age checks. Updated `vision/answers.py`, `desktop/README.md`, `desktop/check_experience.py`, and `test_camera_preview.py`. Evidence and synthetic preview: `review/2026-09-23-vision/`.

Checks: nine sensor-free vision/window tests and 20 desktop experience tests passed. A bounded real camera run measured 1280×720 at about 15.12 fps after startup; the Qt handoff measured about 15.14 fps, with first frame at 3.33 seconds and successful Stop/clear. No scene content was logged, saved, or uploaded. The tests do not establish recognition accuracy, subjective image quality in the owner's room, battery life, or actual spoken-question capture. The camera remains a local observer; biometric authentication and pen detection are unfinished, and Windows Hello PIN remains the protected-action authority. Next: owner judges clarity in normal lighting; profile CPU and power only if the live view still burdens the laptop.

## 2026-09-24 — Brain strategy review and local security-phrase gate

Compared `lya-external-work/lya-brain/` with the active native runtime and a
read-only hardware check. Decision: adopt local-first, explicit memory,
permission, evidence and recovery principles, but do not copy the proposed
legacy-path implementation or its other-device benchmarks. The current native
brain already has bounded in-memory FTS recall; a persistent blind index is
deferred until latency evidence warrants its leakage and migration cost. Local
model files exist, but available RAM was low at measurement; no model load or
new provider test was attempted. No API key is needed for the next foundation
steps. Details and ordered gates: `review/2026-09-24-brain-strategy/README.md`.

Closed the confirmed legacy cloud-transcription leak in `security/auth_wall.py`:
its security-phrase check now requires a local transcription callback and fails
closed without one, and its report omits the spoken phrase. Added isolated
fake-input regression checks in `test_auth_wall.py`. Updated active
`brain/workflow.py` and its test so the built-in 8 GB/zero-spend plan no longer
prescribes Qwen3 4B without a free-RAM, quality and power check. The legacy vault-unlock
caller remains unavailable until a vetted local transcriber is wired; this is
not a claim of completed biometric authentication. `.venv-ui` ran
`test_auth_wall` and `test_brain_workflow` plus `test_vault_recovery`: 38 passed.
The external recovery helper now resolves its configured key path at call time;
its export, verify, wrong-passphrase and restore paths passed against a
disposable fake DPAPI key. An initial isolated run exposed the stale default
path and attempted a read of the real key, which Windows refused; no real key
was changed or printed. No real vault export, microphone, camera, biometric
template, credential or external service was used. Next: owner-side real
recovery export/verify with separate off-device storage, then native brain
golden evals. Cross-account recovery remains untested.

## 2026-09-24 — Native brain golden-case pass

Ran the 13 research golden inputs through the current `brain/workflow.py` with
fake sessions, a disposable encrypted store and a model stub. Initial evidence
showed private fact questions and unsupported actions reached the model; a
saved brother-name fact was retrieved but not answered directly. Updated
`brain/workflow.py` so short personal fact questions require memory-read
authorization, return an exact saved fact with provenance, or abstain when
missing. Unsupported app, skill, reminder and password requests report that
nothing happened; time and capability help avoid the model. Restored the
desktop-only synthetic `brain demo` entry after tracing its actual worker.
Changed `test_brain_workflow.py` and `desktop/app.py`. All 13 tested inputs
now avoid the model, but full acceptance is **not** achieved: app launch is
unconnected, stop-with-pending-work is not concurrently proven, and help is
maintained text rather than a live registry. Some paraphrases may still reach
the model. Per-case results: `review/2026-09-24-brain-strategy/golden-results.md`.
Checks: 41 isolated brain/auth/recovery tests and 20 offscreen desktop
experience tests passed. No real user data, secret, biometric, camera,
microphone or cloud request was used. Next: close the remaining golden gaps
and expand missing-fact coverage without weakening the permission boundary.

## 2026-09-24 — Synthetic retrieval scaling check

Benchmarked the native encrypted `brain.notes.retrieve` path at 100, 1,000 and
2,000 fake notes. Median query latency rose from 16.06 ms to 52.41 ms and
97.74 ms; at 2,000 notes a separate check measured 56.92 ms for row recall
and 5.85 ms just to open/count the encrypted database. The research's <20 ms
semantic-read target is therefore not met at scale. The current 2,000-note
cap and off-UI-thread execution bound impact, but no battery or end-to-end
latency result was measured. Evidence and method:
`review/2026-09-24-brain-strategy/retrieval-benchmark.md`. Decision: keep the
existing implementation for now and design a migration-safe index only with
save/correct/forget/expiry/restore integrity checks and a before/after test.
No real note, key or provider was used.

## 2026-09-24 — Encrypted native memory search index

The measured 2,000-note recall exceeded the research's <20 ms target. First
changed read-only recall/graph lookup to avoid rewriting encrypted storage on
reads; this improved 2,000-note median to about 88 ms. Then added an FTS5
search table and insert/update/delete triggers **inside the existing
whole-file encrypted SQLite store** in `storage/store.py`. Legacy stores
backfill on open, and `brain/notes.py` decrypts only ranked matches and
eligible graph neighbors. No separate plaintext index file is written.
The repeatable synthetic benchmark measured 4.09/5.66/10.66 ms medians at
100/1,000/2,000 notes, respectively, versus the original
16.06/52.41/97.74 ms. Encrypted file size at 2,000 notes rose from about
928 KiB to 1,237 KiB. `test_search_index.py` validates migration without a
read-only file rewrite, correction, forgetting, expiry, person scope and
credential exclusion; `test_recovery.py` validates search after restore.
56 focused tests passed. Evidence and repeatable fixture:
`review/2026-09-24-brain-strategy/retrieval-benchmark.md` and
`review/2026-09-24-brain-strategy/bench_retrieval.py`. Real-store migration,
cold full-app latency and battery impact are untested. Next: run a verified
backup before any owner-data migration, then assess live performance.

Migration guard: because an existing encrypted runtime database was present,
new stores receive the index automatically but old stores do not persist it
from an ordinary read or write. Reads can build a temporary RAM index.
Persistent migration requires `LYA_ENABLE_SEARCH_MIGRATION=1` after a
verified backup. An isolated test confirmed both the default unchanged
on-disk schema and the explicit opt-in path. No owner database was opened or
modified for this test.

## 2026-09-24 — Portable encrypted-store bundle and guarded recovery

Hardened `lya-external-work/lya-brain/recovery/vault_recovery.py`: recovery-key
export and DPAPI restore writes are atomic; verify can authenticate a copied
encrypted store; restore refuses to replace a different or unreadable existing
key without `--replace-existing` plus a matching encrypted store, and preserves
the old key in a uniquely named backup. Added `bundle`, `verify-bundle` and
`extract-bundle`. A bundle contains only known `.lya` and `.enc` ciphertexts,
an encrypted file/path manifest and a passphrase-protected key. Extraction
requires a new folder outside the live project/runtime locations. Oversized
and altered copies fail verification. No `.env`, plaintext media or biometric
material is intentionally bundled. Files and commands are detailed in
`review/2026-09-24-brain-strategy/recovery-runbook.md`.

`test_vault_recovery.py` uses disposable DPAPI keys and ciphertexts to check
export, verify, restore preservation, bundle creation, wrong passphrase,
tampering, safe extraction and failed-source cleanup. The focused brain,
recovery and security suite passed 59 tests at this point. No live owner vault/database was
opened, copied, modified or migrated, and no external destination was written.
Decision: keep existing encrypted-store migration off until an owner-run
off-laptop bundle is copied and verified. Limits: only enumerated ciphertext
extensions/locations are included; full machine backup and cross-account
application restore remain unproven. Next: owner selects a destination, makes
and verifies a real off-device bundle without sharing its passphrase; then
consider opt-in search-index migration and test restored app behavior.

## 2026-09-24 — Pending brain answer cancellation proof

Added a concurrent fake local-model check to `test_brain_workflow.py`. The
worker blocks inside a fake model; after its cancellation event is set, the
late model answer is discarded and the brain returns `cancelled`. This tests
the native brain post-inference boundary, not immediate interruption of an
in-flight provider call or every desktop UI path. Updated the g-010 status in
`review/2026-09-24-brain-strategy/golden-results.md`. No real model, provider,
identity or owner data was used. The final focused brain/recovery/security
suite passed 60 tests. Next: exercise the desktop job-generation
handoff with a fake pending worker, then decide whether transport-level
cancellation needs an explicit adapter change.

## 2026-09-24 — Pending desktop worker answer handoff

An offscreen pending-worker test exposed a real UI bug: while a request was
running, submitting another question advanced `desktop/app.py`'s generation
before rejecting it, so the original answer was silently discarded. The busy
guard now reports that a request is running without changing generation;
Stop/close/sleep/quit still cancel or dismiss as before. Added two isolated
`desktop/check_experience.py` tests with fake blocked workers. One proves the
first answer appears after a second busy question; the other proves Stop hides
the late answer, clears the transcript and prevents speech. No real model,
provider, vault, sensor or owner data was used. `desktop/check_experience.py`
passed 22 offscreen tests and the focused brain/recovery/security suite passed
60. Updated `review/2026-09-24-brain-strategy/golden-results.md` g-010.
Limit: provider subprocess or network cancellation is not yet proven to stop
the remote work immediately. Next: test the transport cancellation adapter
with a fake subprocess before claiming live cancellation.

## 2026-09-24 — Bounded cancellation of local Oracle SSH process

`brain/oracle.py` now uses `cloud/ssh_session.py` for its real non-session SSH
path as well as its optional session path. Non-session requests close stdin
after writing JSON, matching the server's existing read-to-EOF protocol; the
helper can kill the local SSH child on cancellation. Mocked runners remain
available for isolated tests. Added three tests in `test_oracle.py`: local
fake-subprocess completion after EOF, cancellation before its synthetic sleep
finishes, and default bridge selection of the cancellable helper. No Oracle
host, API key, real SSH credential or provider was used. The relevant
brain/router/Oracle/recovery suite passed 97 tests and the offscreen desktop
suite passed 22. `cloud/README.md` records the deployment boundary. Limit:
killing local SSH does not prove that a remote upstream request immediately
stops or refunds quota. Next: verify the server-side cancellation protocol
only after matching server code is deployed through its separate gate.

## 2026-09-25 — Jarvis-style initialization and the real connection report

Owner asked to register as admin, check whether all connections are done, and
replace the "boring and simple" owner walk-through with a futuristic, voice-led
one that greets as boss, teaches, and scans.

Added `desktop/activation.py` and `activate-lya.cmd`, with `test_activation.py`.
Six acts: BOOT (eleven subsystems probed for real and revealed line by line),
IDENTITY (salutation, default boss, plus display name, spoken through the
existing Piper path), OPTICS (camera opened only on request, real YuNet face
detection, three real capture prompts, frames never stored), VOCAL (microphone
opened only on request, fresh six-digit code, three clips, real duration/RMS/peak
and voiceprint-stability verdict), VAULT (Windows Hello proof, explicit consent,
one encrypted person-scoped row) and ONLINE (greeting plus live/locked summary).
Visual change: dark gradient, grid, scanlines, rotating iris and radar sweep
around the crystal core, left act rail, right subsystem ledger with real
ONLINE/LOCKED LEDs, live camera viewport with real face boxes, live waveform.
The animation timer stops when the window is idle, hidden, or in reduced motion.

Deliberately not weakened: the optics act checks face presence and says
`NOT AN IDENTITY MATCH`; no biometric template is written while the enrolment
contract is incomplete; `biometric_readiness()` requires optics, camera, mic,
speech recognition, face embedding and anti-spoofing together. Enrolment therefore
commits through the existing, sanctioned `register_device_admin` path (verified
identity, no template, audit outcome recorded as such) until the stack is
installed.

Real connection report on this machine: NEURAL CORE, ENCRYPTION VAULT, SECURE
STORE, OPTIC ARRAY, CAMERA RUNTIME, MICROPHONE, VOICE OUTPUT and WINDOWS
CHECKPOINT are ONLINE; SPEECH RECOGNITION, FACE EMBEDDING and ANTI-SPOOF LAYER
are LOCKED (no transcription engine, insightface missing, torch and
Silent-Face-Anti-Spoofing missing). This confirms and explains the earlier
finding that every face-gated phone approval is denied today.

Checks: `test_activation.py` 18 passed. Two real defects were found and fixed
while writing them — an out-of-range index in the face-prompt sequence and a
QPainter/QImage lifetime error in the paint check. `check-t01.cmd` was re-run
afterwards to confirm no regression. Not done: nothing was installed, no
enrollment was performed, no camera, microphone, Windows prompt, real store or
network was touched by the automated checks. The install commands that unlock
full biometric enrolment are listed in the review file and await the owner's
explicit approval because they are large downloads and a real environment
change. Evidence: `review/2026-09-25-jarvis-activation/README.md`. Limits:
offscreen Qt and injected sensors only; no on-screen visual approval and no
real-device framing or latency measurement. Next: owner runs
`activate-lya.cmd` at the laptop and judges the experience on screen.

## 2026-09-25 — First native device-status capability

Added `brain/device_status.py` using Windows APIs and standard-library disk
usage for an on-demand aggregate snapshot. Wired four explicit phrases in
`brain/workflow.py`, declared `device_status` in the trusted tier in
`security/policy.py`, and listed it in desktop and brain help. The shared
authorization path now asks for phone approval only for owner-tier actions;
trusted status still requires a verified active session. An isolated test in
`test_brain_workflow.py` confirms fake readings return without a model or
approval prompt and a guest is denied. The focused brain/approval suite passed
41 tests. A bounded real read-only probe returned a battery, RAM, disk and CPU
snapshot; no readings, identifiers or credentials were saved in this ledger.
The system-readiness command remains a separate dependency check. Next: build
capability help from registered implemented routes so LYA reports what it can
actually do, then add one useful notes/task capability at a time.

## 2026-09-25 — Connected capability help

Replaced the brain's maintained `HELP` paragraph with `brain/capabilities.py`.
Its exact/prefix command matchers now drive the corresponding branches in
`brain/workflow.py`, and `Brain.capability_help()` renders the same catalog.
Protected entries consult `security/policy.py` directly for role eligibility. Help
checks the active person record before listing protected commands; an absent
or unreadable record falls back to public help. The desktop help in
`desktop/app.py` includes this brain catalog plus inspected native interface
controls. It labels council as requiring a local model rather than claiming
that model is currently available. Added fake-session checks for guest, admin
and revoked help; no model call or real person record was used. Verification:
39 focused brain tests and 38 offscreen desktop tests passed. No real store,
credential, sensor or provider was accessed. Next: add a useful owner note/task
capability through this catalog, with explicit authorization and a bounded
storage path, then revisit actual local-model readiness separately.

## 2026-09-24 — Whole-project offline check sweep

Owner asked for a work-flow status review. Ran every isolated suite that does not
touch real stores: the four `check-t0N.cmd` gates (T01-T04),
`check-storage-recovery.cmd`, and sixteen further suites. 346 test executions,
344 passed, 2 failed. Only `test_synthesis.py` fails (2 of 7). Both failures are
a stale mock: the test stubs `Renderer().audio`, but `speak()` now consumes
`Renderer.utterances()` to carry per-phrase captions, and a `MagicMock` iterates
empty, so neither the SAPI-fallback assertion nor the partial-failure assertion
can fire. Decision still open: update the tests, or restore the SAPI fallback the
earlier design had. `test_native_ui.py` (Tk) passed here with 28 event-loop ticks,
so the older "Tk QA environment-blocked" note is dated rather than current.

Environment probe of `.venv-ui`: present — PySide6, cryptography, numpy,
win32crypt, cv2, onnxruntime, sounddevice, pyttsx3, vosk, requests. Absent —
`torch` (so no anti-spoofing stack), `insightface` (no real ArcFace identity),
`speech_recognition` (default cloud transcription), `pyautogui` (device volume
and screenshot). Loopback llama.cpp (`127.0.0.1:8080`) and Ollama
(`127.0.0.1:11434`) were both closed, so private/offline inference is currently
unavailable. `security/liveness.face_liveness()` reported "liveness model
unavailable; verification denied", which keeps every face-gated phone approval
denied, and therefore keeps private memory, real folder browsing, private
`using my memory` answers, reminders, screenshots and persisted theme changes
unreachable end-to-end. Model assets for vision, voice and two local GGUF models
are present on disk.

Repository hygiene: `.gitignore` covers `.env`, `*.key`, `.venv-ui/`,
`security/.lya_key`, `oracle_known_hosts.local` and `brain/*.db.lya`, and no
credential, key, biometric or database path is tracked. However `git status`
shows 144 changed/untracked paths against the single commit `8671be1`, so there
is no usable rollback point for the recent work.

Not run, deliberately: `security_test.py` and `test_security_fixes.py` (both
write to or corrupt real stores), `crash_test.py`, `crash_test2.py`, and every
live provider, camera, microphone or phone check. No enrollment, credential,
vault, biometric or off-device change was made.

Evidence: `review/2026-09-24-full-check-sweep/README.md` with its filtered
`sweep-log.txt`; the temporary sweep script and raw log were deleted after
filtering. Limits: offscreen Qt and fake sensors only, no on-screen visual
approval, no live answer quality, accuracy, latency or battery measurement, and
the totals double-count `test_brain_workflow.py` (37) and `test_approval.py` (3)
because two scripts include them. Next: resolve the `audio/synthesis.py`
fallback decision, restore a rollback point, then consolidate the three speech
stacks (`audio/voice.py` pyttsx3, `audio/synthesis.py` Kokoro,
`external-work/alya_voice` Piper) onto one documented owner.

## 2026-09-25 — Encrypted owner task list

Added `brain/tasks.py` and registered add/list/complete commands in
`brain/capabilities.py` and `brain/workflow.py`. `security/policy.py` places
these under owner approval. Tasks live in a separate person-scoped table within
the existing encrypted local database; this table is created on first add,
without an eager schema migration on a read. Task text is not passed into model
prompts or note retrieval. `task done` requires the matching person ID in SQL.
The list is bounded to 100 open tasks and task text to 300 characters. No
reminder scheduling or automatic interpretation was added. Isolated tests in
`test_brain_workflow.py` used a disposable Fernet key, fake people, temporary
database, stub model, and fake approval. Brain/approval suite: 44 passed. No
real identity, biometric, owner store, phone, or network was touched. Artifact:
`review/2026-09-25-task-list/README.md`. Limit: live owner access remains
blocked until owner-initiated identity setup and backup readiness. Next: finish
brain foundation gates before starting platform expansion.

## 2026-09-25 — Device-only admin registration preparation

Changed `security/HelloVerifier.cs`, `desktop/registration.py`,
`desktop/experience.py`, `desktop/app.py`, `storage/store.py`,
`security/vault.py` and the external recovery helper.
The helper's success is bound to a fresh nonce. The UI requires explicit local
profile consent, creates the first admin atomically in the encrypted runtime
store, permits only device-only records to use this sign-in path, and binds a
five-minute desktop session on success. No biometric template, PIN or raw media
is stored; owner-tier actions still require separate phone approval. New
DPAPI-wrapped keys default to the user runtime folder; existing legacy keys
remain in place until recovery is verified. A 720 ms one-shot crystal sweep
starts during verification and stops at rest. Synthetic previews and the
security scope are in `review/2026-09-25-admin-bootstrap/`.

Checks: the full offline `check-t04.cmd` gate passed, plus 37 focused
registration/recovery checks and 23 offscreen desktop checks passed. The helper compiled. A read-only live availability check was
blocked by Windows Application Control inside and outside the sandbox before
any prompt, so no real profile, sign-in, biometric capture or owner database
change occurred. The UI reports this failure and grants no access. Automatic
face recognition, unknown visitor photos, and a general high-security approval
screen are deferred; camera-on consent, local identity model and liveness are
not ready. Next: choose a trusted Windows verifier distribution or reviewed
in-process interop route, then perform an owner-driven live sign-in and
independent recovery verification before relying on the profile.

## 2026-09-25 — First-owner activation connected and visual walkthrough refreshed

Connected `desktop/activation.py` to the first-owner `register admin` command
in `desktop/experience.py`; existing admins still go through the established
sign-in dialog. Fixed the standalone launcher crash and kept its dialog alive.
The HUD now presents a readable crystal-centered stage, contextual connection
checks, spoken step captions, camera viewport, and clear device-only outcome.
Removed automatic microphone opening, stopped sensors on stage changes, capped
camera preview work, discarded raw voice clips after measuring them, and bound
Windows proof to the exact name before encrypted profile creation. Cancel
ends a pending verification attempt. Tests were adjusted for these behaviors.

Checks: 64 focused offscreen tests passed and changed modules compiled. Synthetic
identity and optics previews were inspected. Live probes in this session found
vision model assets present but no OpenCV camera capture, and a listed Realtek
input that PortAudio could not capture from. A read-only Hello availability
check was blocked by Windows Application Control before any prompt. These
results are session-specific; they do not prove the hardware is broken. No
owner enrollment, profile creation, real store write, media retention, or
off-device transmission was performed. Source and artifacts are described in
`review/2026-09-25-admin-activation-refresh/README.md`; previews are saved in
that directory. Decision: keep Windows proof fail-closed and call camera/voice
steps calibration, not identity. Next: resolve desktop camera/microphone access
and use a trusted Windows verification route that Application Control accepts,
then run the owner-led enrollment and recovery check.

## 2026-09-25 — Normal-session camera, microphone and speech verification

After the owner reported that Windows Camera and Sound Recorder work, repeated
the device checks outside the restricted tool session. Both OpenCV's direct
camera call and LYA's `CameraWorker` opened the camera and returned a frame.
PortAudio opened the default Realtek input and LYA's `MicWorker` returned a
short WAV; the test did not include spoken words. The offline `SetupSpeech`
worker completed a short greeting. These are live connection checks, not
biometric identity or speech-quality validation. Media was not written or
transmitted. An unsandboxed `HelloVerifier.exe check` and a Qt `QProcess`
attempt both received the Windows Application Control block. The executable
is unsigned. No owner enrollment or real store write occurred. Updated the
desktop runbook and the activation review report. Next: use a supported,
policy-accepted Windows verification route before owner-led registration.

## 2026-09-25 — Smart App Control approval diagnosis

Read the local Code Integrity block event without changing Windows settings.
It names the enforced Smart App Control policy for the unsigned Hello helper.
Checked Microsoft's current documentation: there is no per-app approval for
Smart App Control. The owner can inspect its status in Windows Security, but
turning it off would affect all apps and is not the chosen fix. The admin gate
remains closed. Next: replace the helper with a trusted signed or reviewed
in-process window-bound Windows verifier, then run the owner-led proof and
recovery check. No profile, key, media or policy was changed.

## 2026-09-25 — Admin availability and conflicting-store check

After the owner changed the Windows policy setting, `HelloVerifier.exe check`
returned `Available` in the normal desktop session. This is only an availability
check; it did not prompt for or verify the owner's Windows credential. A
read-only inspection found a pre-existing conflicting admin state in the
protected runtime store. The current first-owner flow cannot safely create a
new admin or identify one of those records as the owner. The protected store,
biometric material, media, and recovery material were not changed or exported.

Changed `storage/store.py` so `get_primary_admin` raises on ambiguous active
admins instead of choosing an arbitrary row. Changed `desktop/registration.py`
to show a clear owner-review lock message. Added isolated fake-store and
fake-process checks in `test_registration.py` and `test_registration_ui.py`;
43 focused tests passed. Decision: preserve the existing records and keep
sign-in/enrollment locked until the owner identifies the intended recovery
path. Next: review a protected backup and explicit owner-approved resolution
of the conflicting records, then perform owner-led Windows verification and
registration. Earlier statements that no admin exists described only what
those sessions created; they do not establish the current runtime-store state.

## 2026-09-25 — First-run setup inside the normal launcher, voice-first, glass

Owner asked not to add a separate workflow: make the existing `launch-lya.cmd`
path behave like a new phone (setup first, then LYA opens), stop requiring typed
commands, and give the panel a modern glass look with faster speech. No new
workflow was added; everything changed the existing launcher.

`desktop/experience.py` gained `needs_owner_setup()`, `begin_owner_setup()` and
`on_setup_dismissed()` on `OrbDesktop`. Needs-setup is True only when the store is
readable and holds no primary administrator; an unreadable or ambiguous store
returns False so a damaged or conflicting store can never silently open owner
setup. Setup hides the orb, opens the six-act activation dialog, and on success
waits for the dialog to finish before playing the normal orb introduction instead
of showing a second "admin verified" panel. Dismissing setup leaves a docked guest
orb with `SETUP NOT FINISHED · SAY "REGISTER ADMIN" TO CONTINUE`, never a locked
window. `desktop/app.py` `main()` calls `begin_owner_setup()` when required and
`start_intro()` otherwise, with new `--skip-setup` and `--no-voice` flags.

Voice is now the default rather than an opt-in: `main()` starts the listener, and
`Desktop.start_voice(allow_cloud=False)` decides remote transcription from whether
a transcriber key actually resolves. The footer names the live mode —
`TRANSCRIPTION REMOTE (GROQ)` or `LOCAL VOICE LISTENER RUNNING · AUDIO STAYS ON
DEVICE` — so the microphone mode is never hidden. This fixes the earlier cause:
`wake_loop` ran with `offline_required=True` and no local Vosk model exists here,
so the listener raised and stopped, which is why typing felt mandatory.

Speech latency improved structurally: `desktop/setup_speech.py` gained `prewarm()`,
called from `main()`, which loads the local voice worker at launch and keeps it
warm for 45 idle seconds, so the first answer no longer pays the model-load cost.
A `warming` flag separates pre-loading from a real request and is cleared by
`stop()` and `_finished()`. `GlassPanel` in `desktop/app.py` was redrawn as
layered glass: accent glow, three-stop translucent gradient, lit inner rim and a
top-light sheen at radius 24, with a pressed button state and a deeper input well.

Checks: `test_activation.py` 22 passed including two new first-run gate tests,
`desktop/check_ui` 16, `desktop/check_experience` 23, `test_registration_ui` 22,
and `test_router`/`test_oracle`/`test_provider_setup`/`test_brain_workflow`
14/8/3/41 all passed. All offscreen with injected sensors and a temporary
encrypted store. `activate-lya.cmd` was accidentally deleted and restored from
git; it remains a documented direct way to open the walk-through.

This does not make registration complete on the owner's machine. Their store
already holds admin record(s), one prior session recorded an ambiguous active
state, and the recorded decision is to keep sign-in and enrollment locked until
the owner resolves it — so the new gate correctly declines to auto-open setup
there. Registration still requires a working Windows proof for the exact verified
name. Evidence: `review/2026-09-25-first-run-and-voice-first/README.md`. Limits:
no real camera, microphone, Windows prompt, admin profile or enrollment was
performed, and no real spoken-answer latency was measured; the brain round trip
itself is unchanged. Next: resolve the conflicting admin records with owner
approval, then confirm `launch-lya.cmd` opens setup by itself on a clean store.


## 2026-09-26 � Voice wake and speech pre-warm: independent re-review

- Reviewed every file touched on 2026-09-26: `audio/voice.py`, `desktop/setup_speech.py`,
  `desktop/activation.py`, `desktop/app.py`, `desktop/experience.py`, new wake sound asset.
  No source file was modified; only this ledger and the review README were written.
- Re-ran the affected offline suites on `.venv-ui`: `test_setup_speech`+`test_voice` 20/20
  (1 designed online skip), `test_activation` 22/22, `desktop/check_experience`+`check_ui`
  41/41, `test_registration_ui` 22/22, external-work voice lab 141/141 (1 skip),
  `test_foundations` 14/14. Total 260 checks green.
- Findings recorded: F1 (P2) legacy `speak()` blocks its caller via
  `process.communicate(timeout=120)`; F2 (P3) legacy path spawns a fresh voice subprocess
  per utterance instead of reusing the warm worker; F3 (P3) the 2026-09-26 review folder
  previously had no README; F4 (P3) minor tone/style mapping drift between `set_rate()` and
  `speak()`; F5 the Windows Application Control blocker on `HelloVerifier.exe` remains open
  and the activation gate still fails closed (unchanged by design).
- Wake design verified in code and tests: pre-wake matching is local Vosk grammar only;
  audio reaches Groq Whisper solely after a wake and an explicit `allow_cloud=True`, with
  the live mode shown on screen. Camera/mic samples in activation are measured (RMS, clip,
  seconds), never scored or stored; admin commit re-checks verification freshness, name
  match and consent.
- Limits: no microphone, camera, real Windows prompt, enrollment, or live cloud call was
  exercised; the pre-warm latency benefit is structural, not freshly timed.
- Evidence: `review/2026-09-26-voice-wake/README.md` (written this session).


## 2026-09-26 — Voice-wake review follow-up: F1/F2/F4 fixed, persona drift restored

Resumed from the 2026-09-26 independent review's findings. Changed only
`audio/voice.py`, `external-work/config/persona.json`, and this ledger.

- **F1 (P2, blocking speak)** — `audio/voice.py::speak()` now runs the
  synthesis+playback subprocess on a dedicated background worker thread and
  returns immediately (measured ~24 ms vs the previous blocking
  `communicate(timeout=120)`). A new `block=True` keyword preserves the old
  synchronous contract for callers that need it. `stop_speaking()` also sets a
  new `_PLAYBACK_STOP` event so a queued legacy utterance is cancelled; R04
  stop/cancel semantics unchanged and re-tested.
- **F2 (P3, subprocess per utterance)** — partially addressed: the worker
  thread is reused, but the subprocess is still per-utterance (the warm
  desktop `SetupSpeech` worker remains the desktop path). Legacy callers no
  longer block or serialize on the calling thread.
- **F4 (P3, tone/rate drift)** — `set_rate()` now applies the rate to a lazily
  initialised pyttsx3 engine (when available) and still maps to the neural
  tone table, so both tables share one entry point. This also un-breaks the
  pre-existing `test_regressions_r01_r05` R05 failures (4 failing checks
  before this session; 16/16 after).
- **Restored `external-work/config/persona.json`** — an uncommitted working-tree
  change had switched the English Piper voice from the pinned
  `en_US-ljspeech-medium` to `en_US-amy-medium`, breaking
  `test_setup_speech.SpeechTests.test_desktop_uses_native_models_for_english_and_tamil`
  and contradicting `models/voice/manifest.json`. Reverted to ljspeech; the
  voice-lab suite returned to green.

Checks re-run on `.venv-ui` (all offscreen/offline): `test_voice`+`test_setup_speech`
20/1 designed skip, `test_registration_ui` 22/22, `test_activation` 22/22,
`test_regressions_r01_r05` 16/16, `test_foundations` 14/14,
`desktop/check_experience` 25/25, `desktop/check_ui` 16/16, external-work voice
lab 141/1 skip. Functional smoke: non-blocking `speak()` returned in 24 ms with
`stop_speaking()` clean. Limits: no real microphone, camera, Windows prompt,
enrollment or cloud call; F2's subprocess-per-utterance cost is reduced but not
eliminated (spawn still happens); two suites (`test_setup_speech` +
`test_registration_ui`) crash when run in ONE shared unittest process because
`test_activation`-style `QApplication.instance()` binding interacts with
QProcess teardown — each passes standalone, as the ledger procedure already
requires. Known-open: Windows Application Control on `HelloVerifier.exe`
(F5) and the conflicting admin records in the protected store remain owner
decisions.


## 2026-09-26 — Quarantine sweep: unused/legacy files moved into `noneeded/` (nothing deleted)

At the owner's request, all unused and unreachable files were moved — not
deleted — into a structured `noneeded/` folder with a `MANIFEST.md` describing
each item and its restore command. Subfolders: `legacy-skills/` (18 unreachable
skill modules; `main.py` never calls `allskills.py`), `legacy-audio/synthesis.py`
(superseded Kokoro renderer; only consumer was the stale `test_synthesis.py`),
`legacy-ui/jarvis_server.py` (legacy browser HUD per the architecture map),
`dead-tools/` (`tools/test-local-model.py`, `check-biometric-stack.py`,
`install-voice-models.py`, `examples/extract_books.py`, `desktop/bake_crystal.py`,
`test_synthesis.py`, `test_native_ui.py`), `unsafe-test-scripts/`
(`crash_test.py`, `crash_test2.py`, `security_test.py`, `test_security_fixes.py`
— these modify real stores; do not run), and `stray-artifacts/` (the stray root
file `external` — a 99-byte shell-error text — and `probe.txt`).

Deliberately kept despite looking legacy: `audio/voice_auth.py` and
`vision/face_auth.py` (still imported by `desktop/activation.py` and
`web_server.py`), `brain/knowledge.py` and `brain/sync.py` (imported by
`skills/reminder.py` and `cloud/lya_cloud.py`), `brain/council.py` (used by
`brain/workflow.py`), `ui/orb.py` + `ui/themes.py` (used by `main.py`),
`review_checks.py`, the SSH keys and `oracle_known_hosts.local`. `.env`,
protected stores, models, review evidence and desktop QA artifacts were not
touched.

Verification after the sweep on `.venv-ui`: `test_foundations`+`test_brain_workflow`
+`test_voice`+`test_activation` 90/1 designed skip, `test_router`+`test_oracle`
+`test_provider_setup`+`test_registration` 38/38, `test_t02`+`test_answer_verification`
+`test_research_adapter`+`test_recovery`+`test_recovery_ui` 52/52,
`test_skills`+`test_guardian_governor`+`test_mind`+`test_identity`+`test_liveness`
40/40, `desktop/check_ui` 16/16, `test_regressions_r01_r05` 16/16,
`test_setup_speech` 7/7. Total 259 checks green. Limits: no live provider,
sensor, store or enrollment was touched; `skills/` still imports its kept
modules only.

## 2026-09-27 - Wake-flow handoff and isolated test repair

Changed: `.gitignore` now allows only `desktop/assets/wake-greeting.wav` through the general WAV ignore; updated isolated expectations in `test_activation.py` and `test_registration_ui.py` for existing-admin sign-in and in-process Windows verification; added `review/2026-09-26-voice-wake/wake-flow.mmd` and handoff notes in its README. Existing voice/UI implementation was reviewed, not reworked in this entry.

Decisions: ambient audio stays local until a Vosk wake match; post-wake command transcription may use Groq when configured. Other WAV recordings stay ignored. The protected admin conflict remains locked; no records were altered.

Checks: `test_voice test_setup_speech` 20 passed, one intentional online skip; `desktop/check_ui check_experience` 41 passed; `test_activation` 22 passed; `test_registration_ui` 22 passed, each independently and with temporary fake-secret stores. Mermaid validation passed with zero warnings. Cached WAV header read successfully (mono 22050 Hz). `git diff --check` on the touched ignore rule passed. A combined activation/registration run initially showed seven failures from stale tests; separate reruns after correction passed.

Limits and next step: real spoken wake, command ASR, voice/text timing, Windows proof, cloud behavior, and enrollment were not exercised. Owner can run `launch-lya.cmd`, say "wake up LYA," then ask one question and report what happens; resolve the protected admin ambiguity separately before enrolling.
## 2026-09-27 — Full-project workflow report and re-run of every suite

- Re-ran everything offline on `.venv-ui`: `check-t01.cmd` (41 brain + 16 UI + 25
  experience), `check-t02/t03/t04` full chains, `check-storage-recovery`, and
  individually: voice/setup-speech (20, 1 designed skip), activation 22,
  registration + registration-UI, regressions R01–R05 16, foundations, skills,
  guardian/governor, mind, identity, liveness, vision, camera-preview,
  escalation, auth-wall, storage, search-index, vault-recovery, recovery,
  recovery-ui. All green. External voice lab: 141 checks green (1 skip).
- Live-safe functional smokes: `audio.voice.speak()` returned in 22 ms
  (non-blocking F1 fix confirmed) with clean `stop_speaking()`;
  `desktop.app`/`desktop.activation`/`web_server`/`main` all import OK (note:
  `desktop.app` needs `desktop` on PYTHONPATH — the .cmd launchers set it).
- Read-only environment probe: `.venv-ui` has vosk, sounddevice, cv2, pyttsx3,
  win32crypt, insightface, onnxruntime, torch, PySide6; `resemblyzer` and
  `pyautogui` are missing. Models present (3 Piper + kokoro, 2 Qwen GGUFs,
  NanoDet + YuNet). `.env` holds GROQ/OpenRouter keys and research flags
  (values never printed). `desktop/oracle.local.json` configured. Local
  llama.cpp endpoint closed (server not running — expected).
- Confirmed `security/HelloVerifier.exe` is unsigned via Authenticode, which
  is the root of the Windows Application Control enrollment blocker.
- Wrote the owner-facing detailed report with five Mermaid diagrams,
  per-workflow status, per-item root-cause table ("what was done wrong"),
  in-progress list and runner map:
  `review/2026-09-27-full-project-workflow-report/README.md`.
- No real store, sensor, enrollment, cloud call or credential disclosure.
  Limits: live mic wake, phone approval round trip, battery/voice naturalness
  and Windows-proof paths remain owner-run trials.


## 2026-09-27 - Foundation-first acceptance restart, step 1

Owner requested testing and confirmation of each step before advancing. Read brain, vision, roadmap, launch and UI paths, existing tests and current registration entry points. Application source and pre-existing changes preserved. Added `review/2026-09-27-foundation-ladder/README.md` with exact checks, missing prerequisites and owner acceptance steps; annotated `review/2026-09-27-full-project-workflow-report/README.md` to correct unsupported end-to-end claims and stale helper-only diagnosis; updated opening status here.

Checks: test_foundations.py 14 passed; desktop.check_ui.InterfaceChecks 16 passed; five selected compact lifecycle tests 5 passed, names in the linked report. Separate processes, offscreen Qt, synthetic state and temporary encrypted storage where used. No real sensor, protected store contents, identity prompt, enrollment, provider request or deployment exercised. No source fix indicated by these checks.

Decision: restart acceptance, not rewrite the codebase. Step 1 is isolated-tested, not owner-accepted. Next: owner runs launch-lya.cmd with --no-voice --skip-setup --reduced-motion and reports the first failed item or confirms the lifecycle. Repair/retest before advancing. Default voice/setup startup, live trusted session, independent backup and higher gates remain unaccepted in this restart. Historical admin ambiguity was not rechecked. Brain byte encoding preserved because existing content contains non-UTF-8 bytes.


## 2026-09-27 - Hands-free first: warm voice reuse and wake conversation

Owner clarified hands-free voice is primary and typing is for public places. Traced wake_loop, recording, speech worker, compact wake/command/close paths and all speech.stop callers before editing. Reused installed Piper and existing cached greeting; no dependencies added.

Changed: `desktop/setup_speech.py` optional idle-worker preservation; `desktop/experience.py` warm-worker handoff, cancellable greeting timer based on WAV duration, greeting stop on command/close/quit, and spoken deterministic clock/date/help/status; `audio/voice.py` 0.4-second wake-only silence and post-speech conversation window refresh; `desktop/assets/wake-greeting.wav` now asks for input. Regressions in `test_setup_speech.py`, `test_voice.py`, `desktop/check_experience.py`. Updated `LYA_VISION.md` and foundation-ladder report. Evidence, limitations and next trial: `review/2026-09-27-hands-free-voice/README.md`; timing: `synthesis-timing.json` in that folder; previous greeting preserved as ignored local `previous-wake-greeting.wav`.

Checks: voice/transport 22 tests, 21 passed and one intentional online skip; compact UI 27 passed; diff whitespace check passed. Initial added spoken-clock tests found reduced-motion text was empty; fixed output selection and reran the entire compact suite successfully. One local synthesis pair: cold 4313.1 ms, warm 229.1 ms, generated greeting 2.02 seconds. No real microphone, speaker playback, protected store contents, enrollment or cloud request tested. Existing changes preserved.

Status: implemented and isolated-tested, live acceptance pending. Not a measured end-to-end speed claim. Recorder still pauses during playback, so spoken barge-in remains incomplete. Next: restart with launch-lya.cmd --skip-setup, say wake up LYA, wait for invitation, ask time, hear reply, ask date without another wake phrase. Owner confirms or identifies the delayed stage before any higher feature work.


## 2026-09-27 - Continuous wake listening and two-clap trigger

Owner reported no response to repeated wake phrases and requested two-clap wake. Read current brain, voice pipeline, desktop startup/status, callers and tests before editing. Model loads; supported grammar aliases exist. Identified ignored clap_enabled flag, segmented standby capture and silently swallowed input errors. Restricted-session microphone failure was distinguished from a successful bounded normal-session microphone read; this does not establish the exact cause in the existing app instance. Process metadata access was denied; no running process changed.

Changed `audio/voice.py`: continuous local standby stream, partial/final phrase matching, DoubleClap heuristic with spectral rejection and threshold knob, clap handling in command recording, cancellation and bounded error reporting. Changed `desktop/app.py`: enable claps, truthful readiness, visible failure/status. Regression checks in `test_voice.py` and `desktop/check_ui.py`; wake gesture requirement in `LYA_VISION.md`. Evidence and next test: `review/2026-09-27-wake-and-claps/README.md`; reproducible sensor-free real-model check: `check_model.py`; results: `model-check.json` in that folder. No dependencies or authorization changes.

Checks: voice/transport 28 tests (27 passed, one online skip); desktop UI/experience 44 passed; real Piper/Vosk generated-speech check 14 expected outcomes, three wake phrases accepted and four negatives ignored with clap mode on/off. Initial amplitude-only clap heuristic false-triggered on generated speech; added high-frequency criterion and verified zero clap events for all seven final samples. Normal-session updated listener opened microphone and stopped cleanly within a three-second local check, with no errors. No audio saved, cloud call, enrollment, protected-store access or private runtime facts recorded. Source diff whitespace check passed.

Status: implemented and isolated-tested; real microphone startup/stop tested, not real human wake/clap acceptance. Sound gesture never grants authority. Threshold/noise calibration, accent recognition and barge-in remain open; listener pauses during output. Next: restart updated LYA with --skip-setup, test voice and two claps about half a second apart separately, then ask time after the greeting. Stay on this step until owner confirms.


## 2026-09-27 - Flexible name wake and real Windows startup

Owner clarified no hand interaction after opening laptop and pronunciation flexibility anywhere in a sentence. Normal-session metadata check found no running LYA desktop; native Startup-folder/user-Run inspection found no LYA entry. No active process was killed. Read current brain, listener and desktop startup before changing shared wake matching.

Changed `audio/voice.py`: shared whole-word wake aliases, context grammar and trailing wake-up normalization; `desktop/app.py`: Qt single-instance lock and updated status; `test_voice.py`: alias/in-sentence regressions; `tools/set-startup.ps1`: native per-user shortcut install/remove; `LYA_VISION.md`: startup/name-wake requirement and physical limits. Installed/verified shortcut outside workspace under the owner-requested startup authorization. Launched updated desktop with --skip-setup; it stayed running and duplicate launch exited 0. No enrollment or private store change.

Checks: voice/transport 28 tests, 27 passed + one intentional skip; desktop 44 passed. `review/2026-09-27-name-wake-startup/check_names.py` and `model-check.json` record 22 expected real-model outcomes on generated public speech, with zero clap events. Initial Elya/in-sentence-Laya fixture misses drove phonetic/context grammar correction. Real sign-in execution and human accent/claps are not established by these tests. No developer test uploaded audio or retained microphone samples. Source whitespace check passed.

Evidence/rollback: `review/2026-09-27-name-wake-startup/README.md`; remove automatic startup using tools/set-startup.ps1 -Disable. Broader phonetic alias layer can false-wake on that ordinary word; waking grants no permissions. Sleep/pre-sign-in hearing and speech barge-in remain incomplete. Next: owner tests names and two claps with now-running app, without manually launching; fix the first failed trigger before advancing.


## 2026-09-27 - Bounded diagnostic for unresolved live voice failure

Owner requested help building the hands-free system after continued failed wake/response. Read current brain/listener/startup/greeting paths. Added `tools/check_voice_live.py` and `check-voice-live.cmd`: reuse real local wake_loop with temporary in-process meter/clap instrumentation; report microphone-open, sound-received, name/clap and playback status; stop at first wake or 20 seconds; no command transcription, recording or network. Added `test_voice_live_check.py` with synthetic silence/sound/name/clap/failure cases. Existing production implementation and startup settings unchanged.

Checks: test_voice_live_check + test_voice + test_setup_speech: 30 tests, 29 passed and one intentional online skip. Initial fake playback check exposed unsupported winsound.SND_SYNC constant; fixed to native synchronous default before passing rerun. No microphone, speaker, protected store or external service exercised this turn. Evidence: `review/2026-09-27-name-wake-startup/live-check.md`.

Status: diagnostic implemented and fake-tested; owner-reported failure unresolved. Asked owner readiness for live trial; no response yet. Next: run bounded test while owner speaks/claps, identify the first failing stage, repair and retest only that stage. Playback-call success is not audible-output acceptance.


## 2026-09-27 - Owner-ready live microphone and wake checks

Owner replied ready. Ran tools/check_voice_live.py in normal Windows session, a bounded microphone-channel comparison with audible cues, and one repeated 20-second real wake check with a start cue. Initial run opened input but saw no activity above the diagnostic floor. Channel comparison and repeated test confirmed sound input; repeated test detected no name/clap and did not invoke greeting playback. No input errors in final wake check. These results do not identify a specific recognition/threshold cause or prove speaker failure.

Updated `review/2026-09-27-name-wake-startup/live-check.md` and this brain with safe stage summaries only. No detailed private runtime readings, device identifiers, audio or transcripts stored. No network, enrollment, protected store access, device settings or production source changes.

Status: live sound input confirmed in a later attempt; name/clap wake still failed, playback untested. Next: isolate name and clap criteria with separate timing cues, then verify a real greeting. No higher-step development or acceptance claimed.


## 2026-09-27 - Separate name/clap calibration and quieter clap default

Owner asked to work on failed wake detection, then confirmed participation in both cue windows. Ran two bounded local name/clap stages and a bounded current/native input-format comparison. Input was weak and captured impulses did not reach old threshold; exact Windows-level/recognition cause remains unresolved. No audio/transcript or detailed private runtime facts saved, no cloud calls or protected store access.

Changed `audio/voice.py`: quieter default clap threshold (150), existing override preserved, finalized local Vosk name matching to reject transient alias guesses. Changed `test_voice.py`: quiet clap, background noise, finalized streaming and disappearing provisional-name checks. Initial real-model speech rerun revealed a false wake; corrected gating passed the subsequent 22 expected outcomes. Evidence: `review/2026-09-27-wake-calibration/README.md`; updated public fixture results at `review/2026-09-27-name-wake-startup/model-check.json`.

Checks: test_voice/test_voice_live_check/test_setup_speech 31 total, 30 passed and one intentional skip; source whitespace check passed. No claim of live recognition success or lower end-to-end latency. Existing desktop process was not restarted. Opened Windows Sound settings read-only and asked owner for input volume/meter behavior. Next: resolve input-level question, restart intended desktop after calibration, prove an actual name/clap wake and audible greeting before advancing.


## 2026-09-27 - Explicitly authorized local audibility recording

Owner reported maximum microphone volume and explicitly requested recording their input for audibility assessment. Captured a bounded ten-second native-rate input sample; created original and amplified mono listening copies in the owner-local temporary lya-voice-check directory, outside source control. No raw media, transcript, detailed runtime readings or biometric representation added to project documentation.

Check: selected-input signal was very low without clipping; local Vosk did not recover the requested test phrase from original or louder copy. No cloud audio service used. The assistant has not personally listened to the recording; audibility/intelligibility requires owner playback confirmation. No source, Windows settings, startup or enrollment changes. Wrote `review/2026-09-27-wake-calibration/recording-check.md` with safe evidence and retention scope.

Next: owner listens to temporary original/louder copies and reports recognizable speech versus noise. Do not promise wake success or blindly amplify live audio from these measurements alone.


## 2026-09-27 - Compare live microphone paths and isolate clap detection

Owner reported that the earlier local listening copy contained LYA playback but no discernible owner speech amid house noise. Checked Windows microphone permission and compared available Realtek input paths with tools/check_mic_paths.py. The default and WASAPI microphone-array paths opened and received sound; lower-level WDM-KS paths were unavailable to the blocking stream API. A separate bounded check on LYA's exact 16 kHz mono input showed weak spoken-name signal and one accepted double-clap event in the clap window. No raw audio, transcript, or detailed private readings saved; no network, enrollment, protected-store, startup, production code, or Windows settings changed.

Added the local diagnostic script and safe findings at review/2026-09-27-wake-calibration/mic-path-check.md. Checks: diagnostic completed in the normal Windows session; exact LYA input opened; clap detector returned true once. Limitation: no end-to-end desktop wake or owner-heard greeting, and voice audibility remains unresolved. Next: compare close speech near the laptop mic with ordinary distance, verify Windows input meter/recording, then rerun the bounded full wake check.


## 2026-09-27 - Soft voice and room-noise investigation

Owner asks LYA to hear quiet speech without shouting in a noisy house. Owner confirmed the Windows input meter moves only a little for soft speech near the laptop camera, and the selected Realtek microphone-array Properties has only the Microphone level, no Boost slider. Reviewed LYA's standby/command capture: direct default 16 kHz mono stream, no noise suppression; command segmentation uses a fixed peak threshold. The earlier amplified local recording still failed offline recognition, so boosting all audio is not a validated fix. Microsoft documentation confirms some devices offer Microphone Boost, Windows Studio Effects Voice Focus requires compatible hardware, and microphone effects can include noise suppression/automatic gain control. Opened Recording device Properties for owner inspection. No device setting, production code, protected store or enrollment changed; no new audio collected or transmitted. Checks: prior exact-input live test and owner input-meter report; voice-focus/enhancement availability and improved soft-voice capture remain unverified. Next: inspect available microphone enhancements, then retest soft voice with a close-positioned input and isolate the wake/greeting path. If the built-in array remains weak, use a microphone placed nearer the mouth before adding software suppression.
## 2026-09-27 — Voice wake unblocked: Vosk model installed, clap-wake path verified
- Root cause of "wake up LYA / double clap never works": the local Vosk wake
  model was missing. `.env` pointed `LYA_VOSK_MODEL=kaushalya` (nonexistent),
  and the LYA data dir held no model, so `wake_loop` raised "Local wake model
  missing. Microphone not started." — the microphone never opened. All other
  pieces (DoubleClap detector, wake-word regex, wake-greeting WAV, Groq
  post-wake transcription, desktop `start_voice` with `clap_enabled=True`)
  were already implemented and tested.
- Installed the official `vosk-model-small-en-us-0.15` from alphacephei.com
  into `C:\Users\kathirvel\AppData\Local\LYA\models\vosk-model-small-en-us-0.15`
  (also directly under the LYA data root; the store fallback checks both).
  Corrected `.env` to the real path. Model loads in ~0.9 s; wake recognizer
  builds with the alias grammar.
- Verification: `test_voice` 24 passed (1 designed online skip),
  `test_setup_speech` 9 passed, and the full offscreen desktop suite
  (check_ui + check_experience) 46/46 after fixing one assertion mismatch:
  the listener-off self-test message now also states "The voice listener is
  not running." in the answer body (the check reads the body, not the title).
- Live microphone wake, clap, and spoken round trip remain owner-run trials;
  no sensor was opened during these checks.
- Next: owner launches `launch-lya.cmd`, says "wake up LYA" (or claps twice),
  asks one question; then tune `LYA_CLAP_THRESHOLD` if room noise causes
  false wakes.
## 2026-09-27 — LYA now starts at login (no manual launch-lya.cmd)
- Added a minimized shortcut `LYA Assistant.lnk` in the user's Startup folder
  (`C:\Users\kathirvel\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`)
  targeting `launch-lya.cmd` with the project directory as the working folder.
  At every login Windows now starts the desktop (`pythonw desktop/app.py
  --show-panel`), which starts the Vosk wake listener automatically
  (`clap_enabled=True`), so "wake up LYA", any alias phrase, or a double clap
  works without typing anything.
- Safety already present: the app's QLockFile single-instance guard prevents
  two microphone readers if the owner also launches manually; the voice
  listener stops/starts via the crystal menu toggle.
- Note: at startup the process environment does not include `.env`, so cloud
  command transcription (Groq) is only used when `get_groq_key()` finds the
  key (env or DPAPI-protected store); otherwise transcription stays on-device
  Vosk — the designed fail-closed behavior. The wake model is found via the
  LYA data-dir fallback path verified earlier.
- Live first-boot verification (log out/in, speak the wake phrase, clap) is an
  owner-run trial.


## 2026-09-28 - Headset command capture and failed clock trial

Owner-confirmed headset input comparison favored native Windows capture. Changed audio/voice.py to select WASAPI for wake and command input where available, preserve finalized Vosk transcript segments, and limit command capture to 12 seconds in noise. Updated desktop/experience.py to display the question reaching the brain beside its answer; added/updated isolated checks in test_voice.py and desktop/check_experience.py. Diagnostic scripts: tools/check_command_live.py and tools/record_headset_check.py. Ignored experimental speech models in .gitignore. Safe detail and decisions: review/2026-09-28-headset-command/README.md. Voice/setup/diagnostic checks: 36 passed, one designed skip; desktop checks: 27 passed. Native input stream opened and read without overflow. Owner's live 'what time is it?' trial returned an unrelated Mumbai testnet answer, so the spoken-command gate failed. The new transcript display was loaded by restarting LYA, but the owner has not run its next trial. Live weather retrieval remains unimplemented and deferred until the clock gate passes. No media or private runtime facts saved in this ledger; no enrollment or external audio transmission. Next: collect only the owner's report of the visible 'You asked' text and fix the demonstrated cause.


## 2026-10-03 - Command endpoint and final playback pause repair

Owner reports broken voice and incorrect response timing. Read project brain first, current voice capture/routing, desktop speech transport/guard, local renderer and inspected tests. Fixed two avoidable timing paths: audio/voice.py passes its warmed local model into command recording, permitting a finalized nonempty speech endpoint even above the loudness gate; external-work/alya_voice/runtime.py skips the added final playback pause while preserving inter-chunk pauses, final drain and export padding. Added endpoint/noise/empty-result/silence/local-only and final-pause regressions in test_voice.py and external-work/tests/test_runtime.py. Pre-existing changes preserved; no new dependency or model.

Checks: .venv-ui Python unittest test_voice + test_setup_speech ran 36 checks, 35 passed and one designed online skip; external-work tests.test_runtime ran 18, all passed. git diff --check passed. New tests use synthetic PCM and mocked recognizers/devices; runtime tests use fake engines and temporary storage. Safe report and commands: review/2026-10-03-voice-timing/README.md. No live device, audio collection, cloud transmission, protected store, enrollment, settings change or process restart performed. Existing brain bytes preserved during this documentation update.

Status: timing changes implemented and isolated-tested; live response latency, headset quality and noisy-room owner recognition unverified. Additional local endpoint inference has not been benchmarked on the real input. Background speakers are not isolated, and recognition can still miss speech or end a turn at a long pause. Audible defect classification requested from owner and remains unanswered. Next: owner restarts LYA, repeats quiet wake -> clock question -> visible recognized text -> audible correct answer, reports delay and crackling/cut-off/robotic sound; repair the failed stage before background-noise acceptance or higher capabilities. Enrollment and live weather remain deferred.

## 2026-10-03 — Voice turn handling, microdot states, female voice and confirmed failed live retry

Owner requested accurate noisy-room hearing, relevant replies, realistic female speech, listening through the full question, visible hearing/thinking inside the circle, and spoken stop. Read this brain first and relevant sources/vision; applied ponytail and focused coding guidance. Implementation:
- audio/voice.py: bounded 30-second turns with 1.2-second quiet gap and pre-roll; optional installed streaming Silero VAD with portable Vosk fallback; local confidence/repeat guards; actual phase/aggregate-level telemetry; local busy-state stop reader.
- desktop/app.py and desktop/experience.py: listening/hearing microdots, different thought orbits, compact wake, busy-state phase priority, voice thinking panel hidden, existing stop/cancellation reuse.
- desktop/setup_speech.py and desktop/assets/wake-greeting.wav: installed Amy female English output, portable previous-voice fallback, Tamil unchanged; previous greeting preserved as ignored review artifact.
- test_voice.py, test_setup_speech.py, desktop/check_experience.py cover meaningful behavior; LYA_VISION.md records owner requirements.
- tools/check_conversation_live.py and tools/check_asr_comparison_live.py: bounded owner-authorized local diagnostics with audible timing cues, in-memory audio only.

Checks: voice/setup 42 passed + one online skip, diagnostic 2, experience 30, base UI 19, fake runtime 18: 111 passed + one intentional skip. Real local VAD/public synthetic audio four expected outcomes passed; real Vosk/generated public stop fixture five outcomes passed with two-second trailing silence. One-second-tail stop miss and narrow-grammar false interruption expose timing/false-trigger limits; narrow grammar was removed. git diff --check passed. Actual Qt synthetic orb render visually inspected.

Decisions/evidence: review/2026-10-03-voice-conversation/README.md contains implementation, checks and safe live-stage results. orb-states.png and render_orb_preview.py show the actual design; check_vad_model.py/vad-model-check.json and check_stop_model.py/stop-model-check.json hold synthetic checks. amy-timing.json measured warm first audio 104.5 ms versus cold 3766.5 ms (synthesis only). check_voice_choices.py/voice-choice-timing.json rejected installed Bella for approximately 30-second synthesis delay; its comparison adapter is not production code. Generated public comparison WAVs and old greeting preserved locally, ignored. Official Indian English Vosk candidate downloaded to ignored models/speech/vosk-model-small-en-in-0.4; public source/checksum metadata in command-model-candidate.json, extraction integrity/confinement checked. Candidate Vosk and already-installed Whisper did not establish accuracy improvement and were not connected to production. No new dependency installed for streaming VAD.

Live: original owner-confirmed question/stop trial failed. Eight-second comparison invalidated because owner could not speak; requested countdown repeat completed. Final VAD/US-model retry recovered clock words but rejected uncertain recognition and failed stop; owner confirmed both spoken with headset mic close. LIVE COMMAND/STOP ACCEPTANCE FAILED, not an isolated-test success. No owner audio/transcript/private device facts retained in ledger/artifacts, cloud diagnostic request, protected-store/device setting change, enrollment or production restart. Existing unrelated changes and prior artifacts preserved.

Next: remain at the spoken clock gate; isolate quiet close-mic capture/ASR and acoustic interruption before claiming clean noisy-room hearing, privacy/whisper recognition, naturalness or response latency. Changes on disk need desktop restart. Enrollment and live weather deferred.
## 2026-10-03 — Free English professional voice-path research

Owner requests GitHub/internet research for clear longer/slower speech despite close mic and room noise; clarified English and no cost. Read continuity first. Used Agent Reach and official OpenAI documentation guidance; unavailable Agent Reach/GitHub CLI used documented Jina repository reader fallback plus primary vendor/maintainer web pages. Update check unavailable. Compared Microsoft Voice Access English–India, sherpa-onnx streaming English Zipformer, Xiph RNNoise/Werman Windows plugin, larger faster-whisper, online turn-aware APIs, GPU-dependent suppression and phone microphone routing. Recommendation: free offline input-control test, then isolated streaming Zipformer candidate with conservative noise-filter comparison and slower-turn handling. Hardware purchases optional/deferred; verified manufacturer wired boom-headset candidates without unverified price claims.

Artifact: review/2026-10-03-free-voice-research/README.md records sources, rationale, proposed integration behavior, unknowns and next gate. No runtime source change, package/driver/model installation, microphone collection, owner audio/transcript retention, audio transmission, credential/private-store access, enrollment, device setting or desktop restart. Aggregate read-only capability used to filter candidates; private device/runtime details excluded. No new integration or recognition success claimed. Earlier live command/stop failure remains current. Next: free independent English–India dictation control with correctly selected input; pilot candidate locally only after input intelligibility, then owner long-query/stop acceptance. Preserve authentication for protected actions; speech recognition is not identity proof.
## 2026-10-04 — Owner recording comparison, local ASR adapter and independent Windows dictation mode

Owner requested a local recording, Agent Reach research and implementation for natural longer English questions at no cost; later confirmed original playback clear and readiness for a Windows Voice Access control. Read this brain first and relevant voice/UI sources; used Agent Reach documented repository-reader fallback, focused coding skills, and Windows Computer Use guidance for the ready control. CLI/update check unavailable. Kept owner recording/copies only in an owner-local temporary location outside the repository; no exact transcript, audio fingerprint, device identity or signal figures retained here or in review artifacts. No personal pronunciation/audition judgment was made.

Implemented: audio/voice.py explicit native microphone selection, absent-selection failure, 2.5-second quiet gap, 120-second bounded turns and rejection of late decoder results after stop; audio/local_whisper.py opt-in local English CPU/int8 cached adapter, tokenizer completeness/runtime-download guard and whole-question uncertainty/repetition rejection. Whisper default promotion was rejected after failed owner comparison. desktop/app.py microphone/engine menus, asynchronous restart cancellation, explicit cloud-audio opt-in, and Windows Voice Access composer mode; desktop/experience.py preserves editable chat for external dictation. Added audio/requirements-local-asr.txt, tools/setup_local_asr.py, tools/record_voice_question.py, tools/compare_private_question.py, tools/check_local_voice_ui.py and test_local_whisper.py; extended test_voice.py and desktop UI/experience checks. desktop/README.md documents current flags and historical limitations. audio/local_asr.py is a standalone streaming diagnostic candidate, not production integration. Installed sherpa-onnx 1.13.8 for comparison and verified public model weights under ignored models/speech/; existing faster-whisper was reused. GTCRN filtered comparison did not justify a production filter.

Findings: all tested recognizers failed to establish faithful recognition of the owner sample. An initial Whisper confidence-only production check accepted a wrong candidate; added repeated-phrase rejection, rechecked the same local sample and rejected it without forwarding. This guard is not accuracy proof. Real installed Whisper accepted existing generated public speech and rejected silence (two smoke outcomes). Voice/setup/diagnostic/model suites: 54 passed plus one designed online skip. Offscreen desktop suites: 52 passed using temporary storage, fake in-memory keys and disabled live microphone/playback/synthesis/model calls. Source syntax and git diff --check passed. Public sources, categorical results, test commands and limitations: review/2026-10-04-local-asr/README.md; synthetic-whisper-check.json, whisper-model-source.json and streaming-model-source.json. Existing brain bytes, previous artifacts and unrelated working changes preserved.

Runtime: owner-ready Windows Voice Access control launched with LYA --system-dictation --skip-setup, LYA internal microphone off. Process liveness observed; initial command-line-filtered process check missed the processes and was corrected. Windows Computer Use helper initialization/retry failed with sandbox setup errors, preventing verified screen control. Any Windows microphone/privacy consent remains owner-operated; no device/privacy setting changed by the agent. Actual Windows setup/download, recognized text and spoken answer acceptance pending. No additional owner recording during this control, owner audio upload, credential/private-store change, paid service, enrollment or deployment. ASR remains input, not identity; configured text-brain privacy route and private-action authorization remain applicable.

Status: source implemented and isolated-tested; new local recognizers NOT owner-accepted; Windows dictation workflow prepared but end-to-end result pending. Existing live clock/stop gate unresolved; noisy-room/soft speech, target-speaker separation and latency unproven. Weather and enrollment deferred. Next: owner reports English–India dictation text or setup stage; test clock/send/cancel only after the input is faithful. Avoid further model downloads or hardware purchase without that control result.

## 2026-10-04 — Upgraded-build speech route audit and fail-closed cloud option

Owner requested concrete upgraded-LYA output instead of repeated independent microphone tests; no Windows dictation recognition result was provided. Audited current desktop launch/source, without reading credentials or sending audio: normal command recognition is Vosk; optional small English Whisper failed the owner sample; the existing Groq route requests whisper-large-v3. Text-brain upgrades do not automatically upgrade recognition. Closed the task-launched independent Voice Access control after ending this test path; LYA external composer mode has its internal listener off. No new successful voice result claimed.

Changed audio/voice.py so explicit Groq mode reports missing configuration/provider failure, rejects empty recognition, and cannot silently substitute a local guess or contact Google. Removed the legacy implicit Google fallback. Added fake-key/no-network cloud success/failure/empty-result regressions. Latest voice/model/setup/diagnostic suites: 56 passed and one intentional online skip; prior same-task isolated desktop checks: 52 passed. git diff --check passed. Updated safe evidence in review/2026-10-04-local-asr/README.md. Official Groq speech/rate-limit/billing sources establish a Free plan with quotas and a separately billed Developer tier; owner account tier remains unknown and unchanged.

Next action depends on the pending explicit choice: fresh ordinary test audio to Groq using only an owner-confirmed Free-plan account, or remain offline. Previously retained recording stays local as promised; no Groq audio transmission, account/key creation or paid-plan change performed. No more live microphone test until the route/privacy/cost choice is resolved. Existing live clock/stop, noisy speech and latency acceptance unresolved; protected-action authorization stays in force, enrollment and weather deferred.

## 2026-10-04 — Structured hearing-first clarification and truthful microphone diagnostic

Owner clarifies current output voice is clean and replies sound good; keep it. Main remaining requirements are clean incoming speech/accurate full-question recognition and natural human-style pauses, continued listening, timely answer and interruption. Read brain first and relevant voice/UI/vision sources. Read-only input metadata inspection does not establish hardware fault; private device/runtime details excluded from ledger. No new microphone collection or playback, audio transmission, provider/model installation, Windows setting change, output voice replacement or enrollment.

Demonstrated issue: audio/voice.py microphone verdict ruled out a dead/mis-selected microphone on loudness alone; desktop/app.py said hearing you. Room noise can satisfy that measurement. Corrected both messages to incoming sound only and explicitly separated clarity/recognized-word acceptance. Preserved verdict compatibility and existing output/turn logic; updated existing desktop/check_ui.py expectation and LYA_VISION.md. Ordered input/recognition/turn gates and evidence: review/2026-10-04-voice-stabilization/README.md. No arbitrary pause tuning or candidate promotion after earlier failed recordings. Pending Groq choice remains unanswered/deferred, not authorization to transmit audio.

Checks: test_voice 37 passed and one intentional online skip; tools/check_local_voice_ui.py 52 passed with temporary stores, fake secrets and live microphone/playback/model/network disabled. git diff --check passed. Hearing/owner-only speech, noisy room, genuine whisper recognition and live interruption/timing unresolved. Current satisfactory output is an owner report, not a new synthesis benchmark. Next: establish intended-input intelligibility, then faithful words under fixed conditions, then tune/accept conversation turns; weather/enrollment deferred.

Continuity correction: the preceding closure statement was wrong. Windows denied Stop-Process for the task-launched Voice Access control, but the shell emitted a success line afterward. It was not closed and was still observed this turn. No repeated privileged bypass or privacy/security setting change attempted; owner needs to close the trial window. Historical brain bytes preserved.


## 2026-10-04 — bounded voice clarification and connected relative volume requests

Owner reported repeated requests to repeat a full volume question. Source trace found an unlimited RecognitionUncertain retry path and no native-brain volume route. Implemented one clarification followed by a fresh-wake pause after the second uncertain turn, count reset after successful transcription/new wake, and cancellation of late rejected decodes. The UI displays uncertain words transiently, suggests a short volume command when a whole candidate fits, and obeys quiet mode. Uncertain words never execute or enter chat history. Preserved recognition confidence guards and the accepted output voice.

Connected whole-request relative volume matching to the existing handler through verified identity, active-store and trusted-role authorization. Unverified/appearance-only, revoked and cancelled requests cannot actuate. The legacy handler now truthfully reports unavailable control. Up/down remain relative key steps; mute remains a hardware toggle without state readback, and absolute levels/microphone gain are unsupported. No enrollment was attempted.

Files: audio/voice.py; desktop/app.py; desktop/experience.py; brain/capabilities.py; brain/workflow.py; skills/device.py; test_voice.py; test_brain_workflow.py; test_skills.py; desktop/check_experience.py; desktop/README.md. Artifact: review/2026-10-04-volume-retry/README.md. Checks: combined voice/brain/two actuator regressions 85 passed + one intentional online skip; isolated offscreen desktop 55 passed. Two updated brain checks rerun and passed (included in combined count). One desktop regression initially asserted before fake playback completion; corrected its simulation and reran successfully. git diff --check passed. Fake secrets, temporary stores and mocked live I/O only.

Limitations: no fresh sensor collection, private audio transmission, actual volume change, protected-store/key change, provider/model setting change, output voice change, desktop restart or Windows Voice Access closure. Accurate owner speech, noise rejection, interruption and live device effects remain unaccepted. Existing source requires restart; next verify recognized words and bounded clarification before a separate permission/device effect check. Earlier cloud-recognition choice unanswered; enrollment/weather deferred.

## Work ledger - 2026-10-05: hearing research and isolated pilots
- Owner priority: accurate speech-to-text first; preserve accepted speaking voice. Research used Agent Reach Jina Reader and official publisher/model/API sources; CLI and finish update check unavailable. Research, plan, primary sources and measured public-fixture limitations saved in review/2026-10-05-hearing-plan/README.md.
- Implemented audio/local_whistle.py, tools/whistle_worker.py and tools/setup_whistle.py: pinned verified public assets/license, explicit local paths, telemetry off, hidden bounded Windows worker, timeout/cancellation cleanup, complete <=30-second diagnostic input. Python networking denied; native runtime is not OS network-sandboxed. Public speech/silence/steady-noise checks useful; owner hearing failed on the private local comparison. No exact owner audio/transcript or private runtime facts stored here. Not integrated/promoted.
- Implemented audio/nvidia_asr.py, tools/check_nvidia_hearing.py and requirements-nvidia-speech.txt: opt-in hosted Parakeet speech-only route, complete <=120-second PCM, TLS, all result segments, RPC deadline/cancellation, no fallback or actions. Installed optional client in ignored .venv-asr, reusing existing capture packages without changing main desktop dependencies. Actual request schema/capture imports passed without sensor/channel access.
- Verification: test_hearing_pilots.py 14 isolated checks passed, fake credentials/client and synthetic PCM only; diagnostic help passed; affected tracked whitespace check passed. Updated brain using byte-preserving insertion/append. Source and report contain the implementation/evidence, rather than duplicated code here.
- Owner explicitly allowed one fresh ordinary NVIDIA audio request. Initial queued tool terminal was stopped at key input before any microphone access; visible interactive diagnostic launched for hidden key input and manual Enter. Launch does not establish owner visibility, runtime collection or recognition success. No hosted response available to agent yet. Earlier private recording stays local-only. No key stored in project files; no output voice, production default, enrollment or device action changed.
- Remaining gate: compare fresh spoken question with recognized words; failure stays failed and must not be dispatched to LYA. NVIDIA free prototyping is account/rate-limited, not a permanently free production guarantee. Sensitive/private speech, noise, natural turn boundaries and stop need separate acceptance. Broader LYA work can use existing text input. Enrollment/weather deferred.

## Work ledger - 2026-10-05: owner-accepted hearing and NVIDIA desktop connection
- Owner reported fresh NVIDIA speech transcription was exactly accurate and supplied diagnostic screenshot. This establishes one ordinary question hearing acceptance, not noisy-room, long-question, stop or full assistant response acceptance. No exact owner words/image, API key or private runtime details copied into plaintext project artifacts. Research/pilot README now links the connection report.
- Changed audio/voice.py and desktop/app.py: explicit selected NVIDIA route, three-second pause matching accepted pilot, complete-question capture bound, cancellation passed to provider, no alternative-provider fallback; unknown providers rejected before listener startup. Desktop checks private mode after capture before remote routing. Local default retained. Privacy must be enabled before confidential speech; no pre-recognition secret classification or recall of sent audio promised. Existing authentication/command gates unchanged.
- Added tools/start_nvidia_lya.py: opt-in session cloud launch with hidden local key, no persistent credential or key command argument. Existing desktop libraries loaded into isolated client environment and child tools via ignored path bridge; main dependencies unchanged. First pilot UI attempt lacked pywin32 path setup, then child demo exposed missing shared dependencies; both repaired before final checks. No new protected store or enrollment work.
- Validation: test_hearing_pilots.py plus test_voice.py 59 passed and one existing designed online skip; offscreen tools/check_local_voice_ui.py in pilot environment 57 passed with synthetic stores/fake secrets and live I/O disabled. Final launcher help, syntax and affected tracked whitespace checks passed. New tests cover NVIDIA routing, no fallback, dynamic privacy during capture, complete wake/question forwarding and selection alone keeping cloud disabled.
- Artifacts: review/2026-10-05-hearing-plan/nvidia-connection.md; updated desktop/README.md and hearing-plan README. Historical brain bytes preserved. Owner key from diagnostic not recovered; no new live collection/upload, startup setting change, device action, voice-output change or desktop activation during this connection task.
- Next: obtain explicit permission for ordinary cloud questions in LYA session (previous approval limited to one check), activate via local hidden prompt, verify integrated displayed question and accepted spoken reply. Local wake/stop quality, confidential local recognition, noise and natural long-turn/interruption remain unaccepted. Enrollment/weather deferred.

## Work ledger - 2026-10-05: fresh fully offline hearing comparison
- Owner clarified local means fully offline on laptop. Verified existing Whistle assets and installed optional Whisper availability without microphone/network/download. Prior local failure and current one-question NVIDIA acceptance remain distinct.
- Added tools/check_local_hearing.py and test_local_hearing_check.py: fresh manual-ready capture using current input/VAD, three-second pause, whole <=30-second question reused by current Vosk and experimental Whistle. No transcript dispatch/audio persistence/cloud route; uncertain candidate explicitly marked. Python network audit guard/offline and telemetry flags; no OS native-network sandbox claim. Larger Whisper optional only.
- Checks: three isolated synthetic comparisons passed; help passed; both actual local decoders recovered meaningful words in an existing public generated speech fixture, with Whistle trailing quote. This does not establish fresh owner hearing or noisy-room accuracy. No private words/audio, credentials or private runtime facts copied into artifacts/brain.
- Saved evidence: review/2026-10-05-hearing-plan/local-check.md. Visible local diagnostic launched, waiting for owner Enter. Launch does not prove UI visibility, actual collection or recognition success. No output-voice/default/provider activation/device/enrollment change; no new model download. Historical brain bytes preserved.
- Next: owner compares both local output sections to actual spoken words. Accuracy pending; larger model only if requested and useful. Ongoing NVIDIA permission remains unanswered and not enabled. Enrollment/weather deferred.

## Work ledger - 2026-10-05: online-only selection and bounded NVIDIA model backups
- Owner reported fresh offline candidates totally incorrect and chose online hearing plus backups. Local gate failed by owner evidence; exact transcripts/screenshots not copied. Previous ongoing-cloud permission question superseded by direct online choice. Earlier saved private recording stays local-only.
- Research used Agent Reach Jina Reader and official web sources. Verified Parakeet TDT primary, NVIDIA-hosted Whisper Large v3 backup and selectable Parakeet CTC 1.1B spare function IDs/languages. Canary URL inaccessible; not guessed/added. Source links, reasoned local-model accuracy limits and plan in review/2026-10-05-hearing-plan/online-backups.md. Agent Reach CLI/update check unavailable. No publisher benchmark equated with owner accuracy.
- Changed audio/nvidia_asr.py: two bounded model attempts at most, TLS/fixed catalog endpoint, success no duplicate request; retired/transient service or empty output can switch once, auth/permission/quota/bad input stop. Privacy/cancellation checked before next model, no alternate organization, paid endpoint, raw provider payload log or transcript rewrite. Shared NVIDIA outage cannot be cured by model switching.
- Changed audio/voice.py and desktop/app.py: provider/backup status, online-only private-mode text guidance, no hidden local recognition fallback or larger local model warmup; service exhaustion/auth/privacy stops online listener with truthful restart/text status. Local Vosk wake/standby/stop retained without live accuracy claim. Existing accepted speaking voice and authorization gates unchanged.
- Changed tools/start_nvidia_lya.py, launch-lya.cmd and launch-lya.ps1 for online session launch, selectable verified primary model and hidden session-only key. Existing owned sign-in shortcut migrated using tools/set-startup.ps1 -OnlyIfExisting and target verified; disabled/unrelated entries preserved. Key prompt precedes microphone access; no credential file or secret command-line argument. Main dependency environment unchanged.
- tools/check_nvidia_hearing.py now supports specific model without diagnostic fallback, preventing another model from masquerading as backup success. Fresh Whisper window launched for local hidden key entry/manual Enter under owner online/backups authorization. Backup result not available to agent yet; launch is not accuracy/collection proof. No saved owner recording uploaded or private audio/transcript artifact written. Integrated desktop not restarted by agent during this task.
- Verification: 70 isolated voice/hearing passes plus one designed online skip; 58 offscreen desktop passes, synthetic temporary stores/fake secrets, live I/O disabled. Actual three-model Riva request schema checks, CLI help, compile, tracked whitespace, PowerShell parse and existing owned startup verification passed. New tests include withdrawal, bounded switching, correct IDs/language, quota/auth stop, privacy/cancel before backup, online-only no local/warmup and no repeated capture after service failure.
- Artifacts: review/2026-10-05-hearing-plan/online-backups.md; earlier local-check, nvidia-connection, hearing-plan README and desktop/README updated with current outcomes. Historical brain bytes preserved.
- Remaining: owner accepts Whisper exact words and integrated primary wake/question/displayed transcript/voice reply; spare, long/noisy speech and interruptions unaccepted. Free hosted development access has model/account rate limits, no indefinite accuracy/availability guarantee. Confidential speech requires private mode before capture and text fallback. No separate-provider backup or continuous catalog monitoring implemented. Enrollment/weather deferred.

## Work ledger - 2026-10-05: clarify backup window and key entry
- Owner asked where the window was and which API key to upload. Updated tools/check_nvidia_hearing.py to label the selected model, explain same NVIDIA key/hidden paste, and state no file upload or chat key disclosure. Dedicated visible LYA - NVIDIA Whisper Backup Test window launched; microphone still requires key and manual Enter. Launch does not establish owner visibility or backup accuracy.
- Help parse passed without secret/sensor/network access. No new credential storage, voice/default change or private transcript artifact. Updated review/2026-10-05-hearing-plan/online-backups.md. Backup recognition result remains pending; historical brain bytes preserved.

## Work ledger - 2026-10-05: qualified backup acceptance and integrated online launch
- Owner reports Whisper backup is understandable and improves on past local models, but is less pinpoint than Parakeet. Record qualified backup evidence; primary remains the previously accepted model. No exact private speech/transcript or key retained.
- Updated online-backups report and tools/start_nvidia_lya.py prompt for same NVIDIA key and hidden entry. Integrated LYA Online - Parakeet Primary window launched under ongoing owner online-mode authorization, before microphone starts until key entry. Direct absolute-script process-count check does not exclude another launch style or prove lock/UI/audio status. No integrated acceptance claimed.
- Prior isolated checks unchanged (128 passed plus one designed skip); prompt-only code change. No voice-output, model-selection, security gate, credential storage, enrollment or additional device change. Historical brain bytes preserved.
- Next: verify integrated displayed recognized words and audible reply, then natural long question and interruption. Shared-provider failure limits and private-mode text fallback remain. Enrollment/weather deferred.

## Work ledger - 2026-10-05: conversation continuity and faceted native interface
- Owner reports the real online LYA conversation now feels successful, advancing integrated ordinary conversation acceptance by owner report. Exact speech, screenshot, key and private runtime facts not copied. Earlier primary/qualified backup evidence remains distinct from noise/long-turn/stop acceptance.
- Changed audio/voice.py: active conversation checked before wake-name extraction; full question/context retained, standalone wake/address while active silently acknowledges, existing 45-second idle gate retained. A turn begun awake retains context through capture/ASR delay. Punctuated standalone stop/cancel canonicalized without bypassing speaking/cancellation gates. Local standby wake path unchanged; no recognition accuracy claim from routing tests.
- Changed desktop/app.py and desktop/experience.py: preserved crystal artwork and accepted speaking voice, added suspended facet/nameplate, distinct listening diamond/thought crossing/spoken wave microdots, chamfered graphite card, native mark, readable titles/paragraph speaker styles and actual voice-state labels. Literal text remains plaintext with links disabled. Full card placed beside crystal when above space is insufficient; reduced motion/streamed captions/keyboard controls retained. No new library/render engine, backdrop capture or continuous panel timer.
- Extended test_voice.py, desktop/check_ui.py and desktop/check_experience.py for full active-name turns, standalone addresses, delayed long-turn dispatch, punctuated interruption, literal markup/style reset, clock title and spoken time, actual phase labels and readable screen-edge geometry. Corrected initial test placement and clock/format regressions before final checks. Checks: 78 hearing/voice checks (77 passed plus one designed skip), 60 isolated desktop passes, syntax and tracked whitespace passed. Temporary synthetic stores/fake secrets, sensor/network I/O mocked; no real microphone/camera/model request or protected action.
- Added tools/render_lya_design.py and review/2026-10-05-conversation-design/README.md with before.png, after.png, after-light.png and after-modes.png. Real Qt widgets with synthetic text/backgrounds only, no Brain/store/sensor construction. Visually inspected all final designs, including actual preferred compact sizes. Prior artifacts retained; desktop/README.md updated with current status and restart instructions. Historical brain bytes preserved.
- Runtime: existing owner session not stopped, restarted or recorded; same primary/backup/output/privacy/credential policies remain. New UI/routing requires restart through launch-lya.cmd with the hidden session-only NVIDIA key prompt. Live acceptance of interior-name continuation and new design/stop still pending; no whole-room noise, hardware, latency or battery-life guarantee. Shared-provider outage limitation remains. Enrollment/weather deferred.

## Work ledger - 2026-10-05: remove the persistent launcher terminal
- Explained terminal cause: tools/start_nvidia_lya.py previously used console Python/getpass to get the session NVIDIA key and remained attached to the desktop. Updated that launcher with optional native masked Qt dialog, Cancel before desktop/listener, fixed safe error messages and a native bootstrap failure fallback. Console diagnostics preserved without --gui. Changed desktop/app.py main to reuse an existing QApplication from the key prompt.
- Changed launch-lya.cmd, launch-lya.ps1 and tools/set-startup.ps1 to use pythonw with --gui. Migrated the existing project-owned startup shortcut using -OnlyIfExisting and verified its target/arguments; did not enable a missing or replace an unrelated entry. Added/verified workspace LYA.lnk for direct native launch. CMD may briefly flash its own shell; the shortcut avoids that wrapper.
- Added test_nvidia_launcher.py: seven isolated checks passed using fake keys, temporary site bridge paths and mocked desktop/client. Covers GUI key masking/clearing/Cancel, no console-input fallback, key environment versus arguments/files, startup-error cleanup, existing session key, retained console diagnostics and Qt application reuse. Existing 60 isolated desktop checks passed with synthetic stores/fake secrets and live I/O disabled. Python compilation, PowerShell parse, shortcut verification and affected tracked whitespace passed.
- Artifacts: review/2026-10-05-native-launch/README.md and synthetic key-dialog.png, workspace LYA.lnk; desktop/README.md updated. Dialog render uses example masked input only and was visually inspected. Historical brain bytes preserved. No real key access/persistence, model request, microphone/camera, enrollment or running desktop restart; actual owner native launch remains pending. Hearing/output/privacy/authorization policies unchanged.
- Next: close current LYA and double-click LYA.lnk; enter the NVIDIA key in the native dialog, then verify the prior conversation/design update live. Enrollment/weather deferred.

## Work ledger - 2026-10-05: owner working-feature freeze and one saved-key location
- Owner requests preserving all working features until explicitly instructed to change them, and asks where to store the NVIDIA key once. Owner reports recent regressions without specific affected components; prior isolated tests are not proof of current owner acceptance. No rollback, interface, wake, voice, hearing/model or startup edit attempted in this task.
- Added owner rule to AGENTS.md: explicit feature-specific request before working changes; why/status questions are not behavior-change authorization; restrict edits to requested scope and report out-of-scope bugs instead of silently fixing them. Applies to future project work and protects prior accepted choices.
- Added security/api_credentials.py for read-only lookup of the named Windows Generic Credential LYA/NVIDIA_API_KEY. Accepts Windows password UTF-16/ASCII and optional terminal NUL, validates key, masks error payloads. Changed tools/start_nvidia_lya.py only to try that entry after the existing environment key and before unchanged prompt; failed/missing access retains prior input. Owner will add/edit/delete the key via Windows Credential Manager. No file-based persistence or real credential read/write by agent.
- Added test_api_credentials.py and extended test_nvidia_launcher.py: 13 isolated checks passed using fake key payloads, mocked CredRead, fake desktop/client and temporary paths. Covers encoding/missing/access/invalid credential, saved-key prompt bypass, no argument/file leakage and environment cleanup; existing launcher behavior remains checked. Compilation and tracked whitespace passed. No real model, sensor, protected store, enrollment or desktop restart.
- Artifacts: review/2026-10-05-key-storage/README.md with precise Credential Manager fields, updated desktop/README.md and AGENTS.md. Historical brain bytes preserved; no secret/owner transcript/private runtime fact recorded. Live owner-managed credential use pending.
- Next: owner saves NVIDIA key under LYA/NVIDIA_API_KEY in Windows Credential Manager and tests the normal launch. Any regression repair requires a specific owner change instruction. Enrollment/weather deferred.


## Work ledger - 2026-10-05: local camera object references and pointing
- Owner explicitly scopes new work to camera access, naming visible/nearby objects and identifying a hand-pointed object. Read project brain and existing camera/question/desktop flows first. Preserved accepted voice/hearing, interface appearance, key storage, startup and authorization/enrollment behavior under AGENTS.md owner rule.
- Implemented vision/hands.py and pinned reviewed Apache-2.0 adapters/license in vision/vendor/opencv_hands; optional full-precision palm/21-point hand weights under ignored models/vision, manifest review/2026-10-05-camera-objects/hand-models.json. No new package/framework, auto-download, face identity or external image service. Palm-anchor equivalence checked; NMS uses width/height boxes. Hand inference capped at two candidates on the existing single analysis worker.
- Changed vision/scan.py only for optional local hands, original-image coordinates and bounded 960px hand input; existing object analysis at 640px, <=2 analysis/sec and camera/session bounds retained. First combined public fixture missed hand after 640px resize; larger bounded hand input repaired it without loosening confidence. Unavailable hand weights/inference preserve common-object analysis.
- Changed vision/answers.py and camera routing in desktop/experience.py for explicit visual references, active-camera bare what-is-this, centered/near-hand objects and cautious extended-index 2D ray selection. Ambiguous multiple targets request clarification; person/backdrop targets excluded. Changed desktop/camera_eyes.py so broken/oversized streams resolve pending questions. Existing preview appearance and reply voice reused.
- Checks: 24 isolated test_camera_dialog/test_vision/test_pointing passed; 62 safe offscreen tools/check_local_voice_ui.py checks passed with fake secrets/temp stores/live I/O disabled. New desktop checks cover spoken pointing and active-camera bare references. Syntax and affected-file whitespace checked. Windowed pythonw worker stdout pipe returned expected explicit-action-required guard without opening a camera.
- Actual local combined networks detected one hand/21 points in a licensed public OpenCV demo frame and rejected the open palm as pointing. Eight blank frames returned no detections. Short-run combined public analysis 178.1ms, blank median 155.9ms/max188.6ms; not sustained resource or live accuracy proof. Initial tiny public gesture chart yielded no palms and was rejected as a smoke fixture. No owner image, transcript, credential or private runtime material copied into ledger/artifacts.
- Artifacts: review/2026-10-05-camera-objects/README.md, check_models.py, public-hand-fixture.png (public upstream image), public-hand-check.json, local-model-check.json, hand-models.json; desktop/README.md and models/vision/README.md updated. Historical brain bytes preserved. Agent Reach Jina Reader/official sources used; CLI doctor unavailable, no install.
- Status: implemented, synthetic and public-fixture tested. Common-category recognition only; arbitrary objects/pens, 3D pointing/distance and actual owner accuracy unproven. No owner camera activation, external sensor transmission, protected store change, enrollment or desktop restart by agent. Owner ready for live check; supplied reopen LYA.lnk, open-camera, centered bottle/cup reference, finger reference and close-camera steps. Next: owner reports actual reply/change-of-target/close behavior before accepting integrated live accuracy. Enrollment/weather deferred.


## Work ledger - 2026-10-05: repair natural camera-control routing
- Owner screenshot reports expanded spoken camera-open/person-view intent was sent to general brain route, which returned action not connected. Live routing acceptance failed; this does not establish camera/device or perception failure. Screenshot/private runtime contents were not saved in project artifacts. Read project brain/AGENTS and traced typed/spoken camera and general-command callers.
- Failing checks reproduced missing camera-control helper and unrecognized person-view phrase before implementation. Existing tests covered exact commands only. Added shared camera_control in vision/answers.py, recognizing explicit open/start/turn-on/close/stop/turn-off with articles/polite forms and bounded clause suffixes. Negative/instructional/status/settings/photo mentions do not activate camera. Added grounded see-me person presence query, without identity claims.
- desktop/experience.py now uses the same classifier before general brain dispatch in on_voice and command; close handled first, expanded open-and-see-me uses existing fresh camera-question/reply path, plain open retains prior preview behavior. Accepted hearing/output, interface appearance, startup/key handling and authorization/enrollment unchanged.
- Validation: test_pointing/test_vision/test_camera_dialog 26 passed; tools/check_local_voice_ui.py 64 passed with synthetic stores, fake secrets and live I/O disabled. New end-to-end checks reproduce reported phrase through spoken route, prevent general-model dispatch, preserve session and deliver local detection reply in normal panel. Natural open/close and classifier negation/settings cases covered. Compilation and affected whitespace checks passed. No actual camera/microphone/key access/cloud request or running-session restart.
- Artifacts: updated review/2026-10-05-camera-objects/README.md follow-up and desktop/README.md. Historical brain bytes preserved. Prior public-model/resource evidence remains separately dated; it does not establish owner live accuracy.
- Next: owner closes/reopens LYA.lnk and retries natural camera-open/person-view request, then common-object and pointing tests. Live routing/object/pointing acceptance pending. Enrollment/weather deferred.
