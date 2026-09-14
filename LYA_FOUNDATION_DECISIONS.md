# LYA foundation decisions

Decided: 2026-09-12

Implementation update, 2026-09-12: the owner's custom crystal and compact glass UI
now runs natively through `launch-lya.ps1`. Eight isolated UI checks and rendered
light/dark contrast checks pass. This implements the presentation portion only;
the full wake/identity acceptance gate below remains pending. See `desktop/README.md`.

This document defines the first LYA product milestone. It refines the ordering in
`LYA_REBUILD_PLAN.md`: internal foundations still come first, but the first
owner-visible journey is wake, native interface, face recognition, and a
person-specific session.

## First experience we will build

1. LYA runs quietly on Windows with no browser window or local website.
2. The owner says **“wake up LYA.”**
3. Offline speech recognition detects the phrase and opens a native floating orb.
4. LYA visibly indicates camera use, captures one frame, and stops the camera.
5. A local face model compares the face with encrypted known-person templates.
6. A known admin is greeted by name and receives an admin session.
7. A known family member or friend is greeted by name and receives that person's
   own data namespace and allowed capabilities.
8. An unknown person receives a guest session with no private data. One encrypted
   review thumbnail may be kept temporarily.
9. When the admin next returns, LYA shows pending unknown thumbnails and asks
   whether to delete, ignore, or label each person.
10. Labeling creates a person record and role. Future recognition can greet that
    person and load only their namespace.

LYA must never say that the camera is off while it is active. “Silent recognition”
means LYA does not interrogate the guest; it does not mean hiding camera use from
people in the room.

## Technology choices for the first milestone

| Need | Choice | Reason |
|---|---|---|
| Runtime | Python 3.12 x64 | Best fit for the existing code and local vision/audio libraries; avoid Python 3.13 until dependencies are confirmed |
| Desktop UI | PySide6 | Native desktop windows, stronger styling/layout than the current Tk prototype, keyboard/accessibility support; no browser server |
| Wake phrase and commands | Vosk with `sounddevice` | Runs offline and one speech engine can recognize both the wake phrase and initial commands |
| Camera capture | OpenCV | Mature local webcam capture; camera opens only for the requested recognition step |
| Face recognition | InsightFace through ONNX Runtime | Local embeddings and matching; reuse only after clean dependency and hardware tests |
| Metadata | SQLite | Built into Python, transactional, sufficient for personal-scale profiles and indexes |
| Encryption | `cryptography` with one master key protected by Windows DPAPI | Keeps application data encrypted at rest and binds key access to the Windows account |
| Application data root | `%LOCALAPPDATA%\LYA` | Keeps runtime/private data outside the source tree and normal project backups |
| Tests | `unittest` plus non-private fixtures | Standard library, deterministic, and already familiar in this project |

No language model is needed for this first milestone. Wake recognition, face
matching, greetings, person selection, and storage are deterministic local tasks.

## Identity and permission model

Face recognition answers “which profile should this session probably use?” It is
not equivalent to iPhone Face ID and is not sufficient by itself for passwords,
private-file export, destructive changes, enrollment changes, or remote access.

| Recognized role | Initial access |
|---|---|
| Admin | Own greetings and low-risk local features; sensitive actions require a later stronger approval mechanism |
| Family/friend | Own profile and explicitly allowed capabilities; no admin/private-owner data |
| Unknown/uncertain | Guest help and public features only |

Enrollment and role changes require an authenticated admin workflow. The current
task defines that workflow but does not enroll real faces.

## Storage design

Runtime data will live outside the repository:

```text
%LOCALAPPDATA%\LYA\
  lya.db.enc          encrypted profiles, roles, settings and indexes
  faces\              encrypted face templates and temporary review thumbnails
  vault\              encrypted files explicitly saved for later access
  models\             local wake/face models; no personal data
  logs\               minimal audit events without private content
```

Use one encrypted database with stable random `person_id` values. Separate OS
folders for every person would duplicate schema and complicate migrations. Rows
that contain personal information include `person_id`, and every query is scoped
to the active session before decryption or presentation.

Proposed minimum records:

- `people`: `person_id`, display name, role, created date, active state;
- `face_templates`: `person_id`, encrypted embedding, model/version, quality;
- `pending_faces`: encrypted thumbnail/embedding, first seen, last seen, expiry;
- `memories`: `person_id`, kind, encrypted value, source, created/updated dates;
- `vault_items`: owner/person, encrypted file location, safe label, sync policy;
- `audit_events`: time, action type, outcome, person id when known—no image, phrase,
  secret, or file contents.

Unknown thumbnails expire automatically after seven days unless the admin labels
or deletes them sooner. Repeated sightings should update one pending record rather
than save unlimited photos. Raw camera frames are discarded after matching unless
one bounded pending-review thumbnail is required.

## Laptop, phone, internet, and offline behavior

The Windows application can work without internet for:

- wake phrase recognition after the Vosk model is installed;
- native interface;
- known-person recognition;
- local profiles and encrypted memory;
- files already stored on the laptop;
- deterministic commands and installed offline capabilities.

General web research and cloud-model answers do not work without internet unless
a suitable local model is installed later.

Remote mobile access has a physical limit:

> If the phone is far from the laptop, the laptop is offline or powered off, and
> the requested file was never copied to the phone, there is no path for the bits
> to reach the phone.

The practical design is an **Important Vault**. The owner explicitly marks selected
files as `available on my phone`. LYA encrypts them end-to-end and synchronizes
them when a connection exists. The phone keeps an encrypted local cache, so those
already-synchronized files remain available without internet. Everything else
stays laptop-only by default.

When phone and laptop are on the same local Wi-Fi, they can communicate without
the public internet. Access from elsewhere requires an internet connection or a
previously cached copy. A later native iPhone companion must keep keys in the iOS
Keychain/Secure Enclave; a relay or cloud store must see ciphertext only. The
sync protocol should be designed before choosing or building the mobile UI, and
building/signing an iPhone app ultimately requires Apple tooling.

## Build order for this experience

1. Reproducible Python 3.12 environment and readiness report.
2. Deterministic command/session core with fake input and cancellation tests.
3. PySide6 native orb opened by a test wake event.
4. Offline microphone pipeline and “wake up LYA” detection.
5. One-frame camera capture with a visible camera indicator.
6. Face matching against non-private test fixtures.
7. Encrypted person registry and strict per-person query scoping.
8. Admin/family/friend/guest session behavior.
9. Pending-unknown review, label/delete, deduplication, and expiry.
10. Real owner-device testing and only then real enrollment.
11. Read-only folders and explicit local memories.
12. Important Vault mobile sync and offline phone cache.

## Acceptance gate for the first milestone

The milestone is `working` only when all of these pass:

- no browser or HTTP server starts;
- wake recognition works locally with the network disabled;
- the orb appears and stays responsive during recognition;
- camera use is visible and the device is released after one capture;
- admin, known non-admin, unknown, no-face, multiple-face and low-confidence cases
  follow their defined access paths;
- one person's test data cannot be retrieved from another person's session;
- unknown thumbnails are encrypted, bounded, deduplicated and expired;
- cancellation works throughout wake/camera/recognition;
- restart preserves fake profiles and pending review safely;
- real-device checks pass before enrolling the owner.

## What is not in the first milestone

No autonomous skill writing, arbitrary device control, cloud brain, password
vault, continuous surveillance, emotion guessing, visitor identification from the
internet, or automatic upload of personal data. These wait until the first journey
is dependable.

## Visual map

View the rendered image at `diagrams/10-wake-identity-storage-mobile.png` (or the
scalable SVG beside it) and the validated Mermaid source at
`diagrams/10-wake-identity-storage-mobile.mmd`.
