# Mobile voice and owner verification - 2026-10-10

Implemented and deployed to the existing private Oracle phone connection. The
owner explicitly authorized the work and copying the existing NVIDIA speech key
to their own Oracle server. Existing phone registration is preserved. The
native laptop UI, hearing, output voice, models, registration and vault were not
changed. Real iPhone voice/Stop/fresh-owner acceptance is still pending.

## Use on the iPhone

1. Keep Tailscale connected. Refresh the existing LYA private HTTPS page in
   Safari. Sign in once after the service update; do not pair/register again.
2. Enable **Allow ordinary speech to NVIDIA** and **Speak replies on this
   iPhone**. Tap **Talk**, allow Safari's microphone, speak normally, then tap
   **Finish**. Recording ends automatically at 45 seconds.
3. Check/edit the words in the question box and tap **Send**. If Safari does not
   start speech automatically, tap **Read reply**. **Stop** cancels capture,
   transcription, a pending answer and local spoken playback. This mobile
   version uses the Stop button; it does not promise spoken interruption.
4. Say/type **LYA, owner mode** to reveal guidance, then tap **Verify owner**.
   This requests a fresh signed passkey proof from the paired credential.
   iPhone controls whether its verification uses Face ID or another supported
   method. LYA neither receives the Face ID scan nor treats the spoken phrase
   as a secret/password. No camera scan is performed by this page.

Owner verification lasts at most five minutes within the existing public
session. It verifies the connection's owner; confidential files, memory,
visitor photos, notifications and device tools are still **not connected** to
the phone. Do not enter confidential material in this public cloud route.

## Behavior and limits

- Page reopen restores only an unexpired, unrevoked signed session. A status
  check never renews the server expiry or cookie. Public expiry stays 15
  minutes; Lock, expiry, credential revocation or service restart require sign-in.
- Browser recording and WAV conversion stay in RAM. Ordinary audio goes over
  private HTTPS to the Oracle worker and then NVIDIA. LYA does not persist it
  or send a transcript to the answer model until Send. This is not a promise
  about NVIDIA's retention policy or forensic erasure of browser/OS memory.
- Audio is mono 16 kHz PCM16, at most 45 seconds/1,440,044 bytes; the browser also
  limits compressed capture to 3 MB. Finish closes microphone tracks before
  decoding. Stop, page hiding, Lock, errors and the deadline release capture.
- No background wake word/locked-screen listening, local phone model, database,
  retained recording/chat, localStorage, IndexedDB or service worker was added.
  The existing secure cookie/passkey and ordinary browser state remain.
- Two shared inference/transcription jobs maximum, eight HTTP handlers, 50
  job IDs per session, and 100 valid transcription requests per UTC day across
  the app. Failed provider attempts consume that request allowance. The reused
  NVIDIA adapter can try one NVIDIA backup for eligible failures; auth/quota
  failures stop. These application bounds do not establish provider free-credit
  entitlement or promise unlimited free service. There is no paid fallback.
- Daily quota and other permission failures currently use the service's generic
  rejection message. Signing in again does not reset the daily quota; use text
  until the UTC reset. Preserve this limit when diagnosing a future rejection.
- Spoken replies use available iPhone system voices; the laptop's accepted
  voice is unchanged. Safari may require Read reply after an asynchronous answer.

## Security and deployment

`cloud/mobile.py` adds authenticated status restoration, session-bound fresh
owner ceremonies, strict WAV ingestion, bounded transcription and existing
cancellation/replay checks. `cloud/mobile.html` adds explicit foreground
capture, transcript review, local speech output and owner verification controls.
`cloud/mobile_runtime.py` invokes the fixed worker;
`cloud/mobile_speech.py` validates a protected Ubuntu-only credential and calls
the unchanged `audio/nvidia_asr.py`. The latter retains the accepted primary and
bounded backup; no desktop model/default changed.

The service account cannot read the credential. It may run only the exact
Ubuntu inference command and the exact root-owned speech entry point through
sudo. Arbitrary Python commands are rejected. The credential has Ubuntu
ownership/mode 0600 in the existing protected server credential directory;
no key is returned to the browser, put in arguments, committed or logged here.
Speech SDK 2.27.0 has a separate server venv, preserving the existing mobile
authentication environment. Camera remains disabled; microphone access is
same-origin and requires browser permission and the UI consent checkbox.
Private Tailscale HTTPS/Serve remains in use; no public endpoint/Funnel change.

`tools/update_mobile_voice.py stage` stages code and runs synthetic Linux checks.
`activate --copy-approved-speech-key` requires the owner's explicit credential
transfer authorization; it preserves the auth DB, validates exact sudoers and
has rollback for code/config changes on activation failure. This maintenance
helper is intentionally one-time for this release; do not rerun it to fix login.
The server's root-only release directory holds prior **public code/config** for
manual recovery, not an exported owner key, passkey or conversation backup.

One service restart was performed. A subsequent page-only copy required no
restart. Pairing metadata and existing inference content were preserved.

## Evidence

| Check | Result |
|---|---|
| Affected isolated regressions, fake keys/temp stores | 195 passed |
| Final phone checks plus reused NVIDIA fake-client checks | 22 passed; overlaps above |
| Synthetic DOM/media/client scenarios | 12 passed |
| Linux staged service-account checks | 18 passed; overlaps Windows checks |
| Source, inline JS and deployment-script syntax | Passed |
| Private HTTPS, live/source page comparison, no-store, unsigned rejection | Passed |
| Credential-read and arbitrary-command rejection | Passed |
| Generated public audio through deployed service-account/fixed sudo worker/NVIDIA | Passed in 1.76 s |
| iPhone microphone, spoken playback, Stop, owner proof | Pending owner acceptance |
| Phone reply with laptop asleep | Deferred by owner |

The public fixture was the previously generated sentence “I'm here. Take your
time, and tell me what you need.” NVIDIA returned “I'm Herr. Take your time and
tell me what you need.” This tests the operational worker/key/provider path,
not pinpoint recognition or the iPhone microphone/HTTP upload path. No human
recording, microphone, camera, owner biometric or private-vault material was
used by the agent. One generated public fixture was sent to NVIDIA; no agent
answer-model call was made.

SDK import peaked at 34.1 MiB. Service idle sample after update was 17,899,520
bytes/one task, with unchanged 256 MiB/40-task limits. These are import/idle
samples, not sustained load or full iPhone latency qualification.

Artifacts: `validation.json`, `host-stage.json`, `host-activate.json`,
`page-update.json`, `public-speech.json`, `live-network.json`,
`check_connection.py`, `check_client.js`, `check_network.py`,
`check_public_speech.py`, and `test_mobile_voice.py` in the workspace root.
The first network comparison incorrectly compared the generated security nonce
with its source placeholder; the nonce-aware check above corrected the check.

Next: owner verifies a harmless spoken question, playback/Read reply and Stop
on iPhone, then fresh Verify owner. Laptop-sleep testing remains deferred.
