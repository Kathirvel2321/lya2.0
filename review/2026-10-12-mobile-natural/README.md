# LYA mobile: natural voice and optional typing

Date: 2026-10-12. Base revision: 3a84266d3e8c9af33743897267c90c6aacd98c15.

The owner requested mobile first: conversational voice without repeated routine button presses, with typing available when wanted. This supersedes the earlier removal of the text composer for this mobile scope.

## Result

- Keep the existing dark/cyan crystal identity, reduce visual clutter and move owner verification/Lock into a Connection disclosure.
- Voice starts after authenticated sign-in when browser audio and microphone permission permit it, submits after an acoustic pause, plays the configured reply, then listens again.
- Quiet pauses no longer stop the conversation after twenty seconds. Silent recordings rotate at the unchanged 120-second bound without transcription/provider calls. An unfinished question that reaches the bound is discarded, then listening resumes.
- The crystal is the accessible pause/resume/recovery control. There are no routine Send, Talk, Stop or conversation-enable buttons.
- The optional text field pauses microphone capture on focus; Enter/the mobile Send keyboard action submits a text-only reply. IME composition is preserved. Tap the crystal to return to voice; an empty field also restores prior voice mode on blur.
- Missing reply audio keeps the text reply and resumes listening. Permission/service/quota failures pause with a usable text/retry path, without automatic network retries. Stale responses and late permission grants are cancelled/released.
- Audio is primed inside the sign-in gesture. A pending browser audio-resume promise has a bounded timeout and points to the existing crystal rather than a removed Read reply button.
- Background/close/expiry stop media, abort requests, clear drafts/replies, and clear pending authentication. Restored tabs recheck the existing session. An explicit pause remains paused on visibility restoration.

## Scope preserved

Only cloud/mobile.html changes product behavior. The backend, model/hearing/speaking providers, private-memory boundaries, passkey verification, origin checks, secure cookies, security headers, speech quota and recording/request size limits remain unchanged. No desktop files, provider credentials, real owner data or enrollment changes.

## Checks

From repository root:

```sh
node review/2026-10-12-mobile-natural/check_client.js
```

28 synthetic DOM/media/network regression scenarios pass; client-validation.json records the result. Covers automatic turns, pauses and recording limits, type/voice switching, IME, owner/stop intent, missing audio, denied/pending audio, denied/late microphone grants, stale chat/transcript responses, quota error, expiry, visibility/pagehide/bfcache and interrupted authentication.

Extracted JavaScript passes node --check. HTML IDs are unique and every literal script target exists. The page retains two CSP nonce placeholders, no third-party requests/storage and the existing API routes. These are simulated checks, not a Safari/audio/security integration result.

preview.html is an offline interactive layout preview: synthetic text only, no microphone, account, model, external script or network calls. Type a sample sentence and press Return; tap the crystal for its paused/listening preview. It is not the production voice application.

Browser visual QA could not run: Playwright is installed but its Chromium executable is absent. No browser download or real sensor/provider call was performed. Actual iPhone keyboard, autoplay, permission, layout and multi-turn acceptance remain unverified. Desktop/backend suites were not rerun because their implementation is unchanged.

## Honest limits

This remains sequential voice: microphone capture pauses during inference/reply playback. It does not support spoken interruption while LYA is speaking; tapping the crystal or focusing typing interrupts it. Acoustic end-of-turn detection is not semantic reasoning or speaker isolation. Silence rotation briefly releases/reopens capture. Latency and naturalness depend on the existing providers.

Safari may require an initial audio gesture and microphone permission. Passkey verification/expiry remain required; zero taps in all browser/authentication states is not a realistic promise. Voice is foreground-only; leaving the page releases the microphone. A silent model-audio failure is recoverable but does not synthesize a different voice automatically.

## Publication

Implemented and tested on a development branch. Not merged into main and not deployed to Oracle. The existing deployment operator depends on ignored local SSH configuration/keys that are unavailable in this environment. No replacement credential, pairing reset, server restart or network exposure attempted.

update_page.py prepares a guarded page-only publication through that existing operator, based on the preceding reviewed publisher. It preserves protected backend/configuration/inference hashes, service PID and pairing inode, backs up the existing HTML, checks exact nonce-normalized served content and security headers, and rolls back on failure. It has been syntax checked only; no remote execution is claimed. Use it only from the owner's existing trusted project checkout with the existing operator available:

```sh
python review/2026-10-12-mobile-natural/update_page.py
```

After publication, the owner should use the existing private HTTPS address: sign in, allow microphone/audio if prompted, speak two harmless questions without turn-by-turn taps, wait more than twenty seconds and speak again, type one question, resume with the crystal, then close the tab and verify its microphone indicator disappears. Also test denial/retry, expired session, background/resume and an actual small-screen keyboard. Record pass/fail rather than inferring live success from these fixtures.
