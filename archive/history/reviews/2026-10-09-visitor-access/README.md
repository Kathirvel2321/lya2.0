# LYA consented startup recognition and visitor permissions — 2026-10-09

Implemented in source and tested with fake credentials, temporary encrypted stores, synthetic devices and an existing public image. Real owner enrollment, iPhone approval, startup camera accuracy and app launches have **not** been live-tested in this task. LYA was not restarted and no real profile, credential, recording or conversation was collected.

## What each person can do

| State | Allowed behavior | Private access |
| --- | --- | --- |
| Unknown / no usable camera result | General questions and text generation, including assignment drafts | None; no device launches or saved memory |
| Approximately recognized registered family/friend or owner face | General questions, `open calculator`, `open youtube` through Chrome guest mode | None; face matching never signs in an owner |
| Owner with a current signed iPhone session | Existing owner tools, explicit registration/removal and memory commands | Existing exact-action phone approval still protects private operations |

The implemented limited tool list is deliberately fixed. Arbitrary apps, files, terminals, URLs and the ordinary signed-in browser are not delegated. Missing Chrome fails closed; LYA does not install a browser or substitute a signed-in profile. Assignment drafting means generating text, not opening or saving somebody's files.

Ordinary general questions no longer pull private notes or prompt for memory approval simply because the owner is signed in. Ask explicitly with “using my memory …” or an existing saved-memory command when stored context is needed. Explicit private requests and serious/council work retain the existing protected route.

## Camera and temporary data

- After setup consent, LYA attempts **one brief visible local observation when a new app instance opens**. It does not repeat on every wake, question, owner sign-in or return. Disabled consent, missing owner profiles, hidden UI, active setup or an already-active camera skips the check.
- A lightweight isolated face-only worker loads the existing pinned YuNet/SFace models; it does not load the voice-enrollment model. Three device warm-up reads make one observation. Camera acquisition/analysis has a three-second deadline; the entire child has a 22-second parent timeout and a renewable cancellation lease. No retry loop or continuing monitor is used.
- Camera preparation/use is visible. The device is released before face matching; hide/sleep/quit/owner setup cancels pending work. Raw startup images and landmark observations are not saved or sent to a provider.
- A known match enables the fixed limited tools for at most five minutes. Each launch also rechecks active registration and consent. This is approximate familiarity, **not authentication**.
- An unknown usable face embedding can remain in RAM for at most ten minutes for an explicit owner registration decision. No photo is kept, no unknown person is automatically added, and no usable observation means there is nothing to register. Discard, guest/sleep or quit clears the relevant pending material.
- Temporary visitor reporting contains only request, limited-launch and blocked-action counts, each capped at 1,000. It has no transcript, recording or reliable identity attribution. Counts are RAM-only until an owner explicitly chooses to save; quit loses unsaved counts. This report does not change separately existing provider, microphone or public-question behavior.

With the camera off, LYA cannot detect somebody changing seats or the owner returning. A five-minute limited grant may therefore remain usable by another person at the laptop. No private capability is attached to that grant. A later requirement for continuous presence would need a different, explicitly consented design; it is not implemented here.

## Walkthrough

1. When ready, fully **Quit LYA from its tray**, then reopen the usual launcher. Launching twice can reuse the older running instance. Development did not perform this restart.
2. Say **“register admin”**. Follow the existing voice-guided name/recovery and iPhone passkey setup. Do not dictate credentials to ordinary online transcription. The private passkey stays with the authenticator; LYA verifies signed proof.
3. Separately accept the local face/voice profile guidance and the described future startup observation. The detailed native face stage collects three views once; voice profiles follow with the camera closed. The current detector displays its actual five landmarks, not a fake dense mesh, depth reading or liveness percentage.
4. At review say **“save my profiles”**. Saving is atomic in the existing protected encrypted store and enables the consented startup observation for a subsequent launch. Cancelling does not overwrite profiles. Existing valid profiles are reused on later owner sign-in; detailed enrollment does not run every time.
5. If profiles were saved before this consent feature, they are **not silently opted in**. Sign in with the phone, then say **“enable startup recognition”** and approve the exact operation. **“Disable startup recognition”** turns off future checks and clears current familiarity. Neither command opens the camera immediately.
6. After a later consented startup observation, a registered person can try **“open calculator”** or **“open youtube”**. Ordinary questions remain available without owner sign-in. A failed or uncertain face check keeps device tools locked.
7. To add a person, obtain their agreement to the visible local check and retained face profile. There must already be a recent unknown observation from that launch. The owner signs in and says **“register visitor NAME”** (also `register friend NAME` or `register family member NAME`). Fresh phone approval binds the name, that specific observation and the limited role. This does not turn the camera back on. If the observation expired, registration stops; no background recapture occurs. Registry capacity is 24 visitors.
8. Say **“remove visitor NAME”** with owner proof and the exact phone approval to remove that visitor's access and face template. This route cannot remove the administrator. Existing encrypted backup copies, if any, are separate from active deletion.
9. On returning, say **“I'm back”** or **“visitor review”**. LYA requests owner phone sign-in if needed, then shows the temporary count summary. Choose **Save summary** or **Discard** once. The choice never opens a camera or registers somebody. Save writes an encrypted private count summary; discard clears pending counts/unknown material. Expired or changed owner proof permits neither choice until sign-in succeeds.
10. Before leaving, **“guest mode”** clears owner binding and approximate familiarity. LYA cannot reliably infer an unobserved departure for you.

### Confidential speech

The accepted NVIDIA hearing route sends ordinary spoken questions online. Turn **“private mode on” before saying confidential content**, wait for its confirmation, and use text for confidential questions in the current NVIDIA launcher. Existing private mode blocks cloud question transcription and inference falls back to nothing if its local model is unavailable. Writing or saying a `private:` prefix after audio capture cannot undo an earlier online transcription request. This task did not replace the working speech engine.

## Storage and authority

Face references, explicit visitor registrations, recognition preference and saved count summaries use the existing encrypted local database and protected key/directory mechanism. The key remains protected through the existing Windows account/DPAPI boundary. No new public archive, Notion, spreadsheet or Oracle route receives this information. Existing public archive routing is unchanged. Independent encrypted private cloud backup/recovery is not added by this task.

Consent and grants are bound to the current unique owner passkey credential. Legacy/unapproved visitor rows are not silently recognized. A recognized face never calls owner session binding; names, persona colours, camera output and model replies cannot grant admin authority. Phone verification and existing sensitive-operation approval remain authoritative. The native owner-only summary choice rechecks current signed owner proof before an atomic save; it is a single explicit save/discard decision after sign-in, not an automatic memory write.

A normal webcam may accept a photo, replay or injected feed. The matching threshold/margin are uncalibrated on this owner/device. They protect no private data, and no Face ID or certified presentation-attack protection is claimed. NIST explains why a biometric characteristic is not an authenticator on its own in its assurance framework: [SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html).

Chrome guest mode separates browsing from existing profiles: [Google Chrome guest guidance](https://support.google.com/chrome/answer/6130773?hl=en). It is not an operating-system sandbox. Anyone already controlling the same unlocked Windows account is outside LYA's permission boundary; these controls do not secure other open Windows apps, administrator-level malware or copied backups. Existing passkey recovery/device acceptance limitations remain.

## Evidence

- `validation.json`: **152 tests passed**, zero failures/errors/skips across visitor, owner-profile, passkey, approval, desktop, legacy-retirement and brain-workflow suites. Fake keys and temporary stores only. The normal host was needed for Windows ACL checks.
- `check_visitors.py`: reproducible isolated suite. Covers failed/ambiguous/expired recognition, revoked registration/consent, owner-only enrollment/removal, denied/stale exact approvals, one-shot/cancelled fake camera, strict child protocol, fixed guest browser arguments, no face-to-owner binding, public/no-private-context questions and one-choice encrypted summaries.
- `check_snapshot.py` / `public-snapshot.json`: existing real face models on an existing public OpenCV fixture using a fake camera; 128-dimensional vector, exactly three reads, device released. Measured 0.313 s after interpreter/OpenCV import, 98.7 MiB process peak and 84.864% of one CPU core during that short operation. These are not live startup latency, idle CPU, complete LYA memory use or recognition-quality measurements.
- `render_interface.py`: four native offscreen previews using the public fixture and fake counts; wide, narrow, minimum and visitor review inspected. The offscreen plugin did not enumerate system fonts, so the renderer explicitly loads the installed Segoe UI font into its own process. No production font setting changed. A sandbox temporary-directory cleanup denial passed on the normal-host rerun; no protections were weakened.
- `face-scan-wide.png`, `face-scan-narrow.png`, `face-scan-minimum.png`, `visitor-review.png`: native previews. The photograph is the public test fixture, not an owner enrollment.
- `source-check.json`: 15-source syntax/whitespace and normal-launcher imports passed; scoped `git diff --check` passed. No dependencies installed, real device actions, provider inference, uploads, live enrollment, production-store changes or deployment performed.
- Public research used Agent Reach routing instructions; its Jina fetch failed, so official NIST/Google documentation was checked through the available web fallback.

Implemented paths: `security/visitors.py`, `security/familiar_capture.py`, `storage/visitors.py`, `storage/store.py`, `skills/limited_apps.py`, `brain/workflow.py`, `desktop/familiarity.py`, `desktop/experience.py`, `desktop/owner_setup.py`, `desktop/owner_scan.py`, `test_visitors.py`, `test_brain_workflow.py`.

Next: owner chooses when to reopen and complete/confirm consent, then live-check phone proof, brief camera closure, known/unknown tool restrictions and the owner review. Until then this is an isolated-tested implementation, not a claim of successful real-person identification.
