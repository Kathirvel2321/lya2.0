# Mobile conversation and Amy voice — 2026-10-10

Update 2026-10-11: owner reports clean working phone conversation. General live acceptance is owner-reported; specific Stop/internal-pause/fresh-proof/laptop-asleep checks remain unconfirmed. Memory, owner interaction and delay findings: [owner-feedback-2026-10-11.md](owner-feedback-2026-10-11.md). The release report below records the earlier state.

Implemented and deployed. The owner accepted the earlier manual iPhone speech/transcript/playback path, then requested fewer taps, pause-aware turn taking and the familiar LYA voice. The owner chose to test this new conversation mode later. New live iPhone conversation, Amy playback, Stop and laptop-asleep acceptance remain pending.

## Try it later

1. Keep iPhone Tailscale connected. Refresh the existing LYA Safari page; sign in once after the server update. Existing pairing is preserved; no new registration is required.
2. Enable **Allow ordinary speech to NVIDIA**, then tap **Start conversation** and allow microphone access. Starting conversation enables spoken replies. Keep the page visible.
3. Speak naturally, including a short pause within a question. LYA detects speech and then a pause, transcribes and automatically sends the ordinary question, plays Amy, and starts listening again after playback. No Finish/Send tap per turn. Tap **Stop** to close the loop.

Manual Talk/Finish, transcript editing and Send remain inside **Text and manual controls**. Automatic mode sends recognized words without that manual review; the page explains this before starting. Voice failure preserves the text and stops the loop. **Read reply** can explicitly use the iPhone voice as fallback when Amy is unavailable.

## Behavior and boundaries

- A lightweight browser waveform detector uses a changing noise floor and speech activity, without downloading a recognition model. End-of-turn silence starts around 1.8 seconds for short questions, 2.8 seconds after longer speech, and adapts up to 3.6 seconds after internal pauses. Speech resumption resets the silence timer. This estimates an acoustic pause; it cannot prove sentence meaning or isolate the owner from nearby speakers.
- No-speech idle ends after 20 seconds without uploading. Conversation turns have a 120-second safety ceiling; hitting it discards the unfinished turn rather than sending partial words. Manual recording retains its existing 45-second bound.
- The microphone closes for transcription/reply playback. Listening resumes after playback. Stop cancels pending work and audio; spoken stop can end a subsequent listening turn. Spoken interruption during playback, simultaneous listening/speaking, background/locked-screen wake and semantic streaming endpointing are not implemented.
- Existing NVIDIA recognition/model fallback is reused. Audio goes to NVIDIA only after the explicit speech consent. Conversation must remain in the foreground; hiding the page stops active work and clears displayed conversation data. No intentional persistent phone model, audio, chat database or service worker was added. Browser/passkey/session/network storage remains unavoidable.
- The server generates replies using the same public Amy medium model as desktop; downloaded assets matched the desktop model hash. Piper 1.8.0 is isolated in a server-only environment, one inference CPU thread, with bounded mono PCM output. Prosody/loudness may differ from desktop playback. No desktop voice/model/capture/default/interface was changed.
- Neural CPU arena/pattern reuse is off. Unpunctuated text is bounded to 80-character spans with terminal punctuation before model inference; Linux freed buffers are returned between spans. This can introduce audible sentence breaks. Voice requests are limited to 4000 characters, 180 seconds of audio and a 25-second child timeout; full text remains available on voice failure.
- Audio synthesis currently completes before playback, rather than streaming. A synthetic long reply took about 17 seconds; short replies are much quicker. Network/provider time is additional. Fast human-like streaming and full barge-in are future work, not claims of this release.
- One heavy audio worker runs at a time. The existing service limits remain 256 MiB/40 tasks. Existing public session expiry (15 minutes), fresh scoped owner proof (up to 5 minutes), 50 request IDs per session and 100 transcriptions/day remain. Each conversation turn normally consumes one transcription and one chat request ID. This update does not relax authority or add private memory/photos/push/device tools. Provider quota/free access/uptime are not guaranteed.

## Files and deployment

Changed public application files: `cloud/mobile.html`, `cloud/mobile.py`, `cloud/mobile_runtime.py`, `cloud/mobile_speech.py`, `cloud/ssh_session.py`; new server-only `cloud/mobile_tts.py`, `test_mobile_conversation.py`, and `tools/update_mobile_conversation.py`. Updated the overlong-audio fixture in `test_mobile_voice.py`. Existing shared transport callers retain their default output bound; only the fixed reply worker requests a larger bounded output.

Pinned operator SSH staged synthetic checks before activation. One phone-service restart enabled the release, preserving auth metadata and inference source; a later checked TTS-only source replacement required no restart. The deployed public source matches the workspace. Piper/model files are server-only. Existing protected credentials were neither replaced nor copied again. No owner profile/private vault, human microphone/camera, human recording, model-provider inference or new speech-provider call was used for these checks.

## Evidence

- `validation.json`: 217 isolated checks pass, including fake-key/passkey/revocation/cancellation, owner/visitor/desktop regressions, audio validation, fixed worker and fake model span checks. Source syntax/whitespace/usual launcher import/inline JavaScript pass. An attempted sandbox run could not open Windows temporary SQLite files; the unchanged isolated runner passed outside that sandbox.
- `check_client.js` / `client-validation.json`: 18 simulated browser scenarios pass, including adaptive pauses, auto send, reply playback/rearm, Stop, idle discard, hard-ceiling discard and visibility cancellation. These are simulated APIs, not real Safari acceptance.
- `host-stage.json`: 24 Linux synthetic checks passed before activation. `host-activate.json`: release activated with existing inference/credential files and auth database preserved. Counts overlap with the main suite.
- Seven selected shared transport/inference/archive checks passed; see `transport-validation.json`.
- `amy-resource-check.json`: earlier short public generated reply completed in 3.55 seconds under a strict 192 MiB worker cap. It did not record measured peak RSS.
- Initial long-reply/192 MiB unpunctuated probes failed with OOM and did not activate their candidates. `amy-long-probe-failure.json` and `amy-sentence-resource-check.json` retain failure evidence. A subsequent arena-off long test passed; earlier measurements are not the final release result.
- `check_full_reply.py` / `final-full-reply-resource-check.json`: final full Connection/chat/runtime/actual Amy path with fake session and long public text passed under the unchanged 256 MiB cap: 16.83 seconds, cgroup peak 225,828,864 bytes (about 215.4 MiB). This is one bounded stress fixture, not sustained-load qualification or a worst-case guarantee.
- `final-service-check.json`: deployed short Amy reply passes, public source matches, service active with zero automatic restarts and an idle sample about 18 MiB; private Funnel remains disabled. No provider or human audio involved.
- `check_network.py` / `live-network.json`: private HTTPS certificate/page/source/no-store/security headers and unsigned-session rejection pass. Camera is disabled; microphone requires permission.

Next: owner tests the foreground conversation/short internal pause/Amy/Stop flow when ready. Laptop-asleep acceptance remains separately deferred. Preserve accepted desktop and mobile pairing behavior.

## Primary references

- Browser waveform API: https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode/getFloatTimeDomainData
- Piper Python synthesis API: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
- Public Amy model card: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/amy/medium/MODEL_CARD

Agent Reach was used for web retrieval; its Jina route failed DNS, so official-source browsing supplied the research fallback. No paid provider or new recognition model was substituted.
