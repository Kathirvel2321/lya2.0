# Crystal registration guide — 2026-09-21

The native setup screen in desktop/registration.py now presents the project's
cached crystal artwork at the center, separates it into four corner pieces,
and reveals a guided hologram-style panel. Open with register admin or admin setup.

Four stages: display name, Windows verification, local recognition preferences,
and review. Availability checks cannot authenticate. Verification is a checkpoint
only, never a new LYA admin/session. Face/voice preferences are unsaved drafts;
no sensors or storage are connected to them. Close clears all draft fields.

The one-shot reveal lasts 2.2 seconds, limits paint requests to roughly 30 per
second, and stops when finished, skipped, hidden or closed. Reduced motion skips
the animation. It uses baked 2D artwork from the model, not live GLB physics.
The centered window fits the available screen and scrolls on small displays.
Battery draw and real display frame performance were not measured.

## Device guidance

User-authorized read-only inventory found an ordinary camera entry and no listed
biometric-class device. The helper returned DeviceNotPresent in the agent session.
Hardware names/identifiers are intentionally not recorded here or in the ledger.
No camera/microphone stream, PIN prompt or account setting was opened or changed.

This does not establish PIN configuration on the normal desktop. Use Windows
Settings > Accounts > Sign-in options > PIN (Windows Hello), then use LYA's Check
availability and consented Verify buttons. Type the PIN only inside Windows' prompt.
An unavailable check leaves setup locked. Webcam recognition alone cannot authorize
private actions.

Official sources for the infrared-camera requirement and PIN-capable verifier:

- https://support.microsoft.com/en-us/windows/security/configure-windows-hello
- https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.ui.userconsentverifier

Agent Reach's Jina reader failed with a local Schannel credential error. Microsoft's
facts were checked through web search; no keys or personal documents were transmitted.

## Evidence

- test_registration_ui.py: 14 fake-process tests passed.
- test_registration.py: 12 synthetic core tests passed.
- desktop/check_experience.py: 13 native experience tests passed.
- Total: 39 focused checks; git diff --check passed.
- Tests cover consent, availability versus authentication, errors, timeout,
  cancellation, duplicate starts, navigation, no false enrollment, reduced motion,
  animation stopping, missing-art fallback and clearing drafts on close.
- render_preview.py generates six synthetic PNG frames: 01-center, 02-split,
  03-screen, 04-device, 05-privacy, 06-review. Split, screen, device and review
  frames were visually inspected. These are not a real person's registration.

## Remaining work

T04/T09 remain incomplete. Real trusted owner/session binding, exact-operation
approval, consented capture, sample quality, calibrated anti-spoofing and account
recovery still need implementation and interactive tests. The UI's optional
personalization preferences are a proposal; the older synthetic AdminRegistrar
requires both face and voice adapters and is not invoked here. Resolve that policy
before connecting enrollment. The transient Windows checkpoint expires after 90
seconds as checked when the review refreshes; it is not an authorization token.

Next: verify the Windows path on the owner's normal desktop, then connect the
chosen authentication and local-recognition flow. No production store, recovery
key or data format changed. Earlier registration artifacts remain preserved.
