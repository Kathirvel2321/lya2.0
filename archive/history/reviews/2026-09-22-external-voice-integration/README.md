# LYA external voice assessment and bounded integration

Date: 2026-09-22

## Verdict

The `external work/` voice system is useful and its local synthesis pipeline is
working. It is substantially more complete than the earlier experimental
`audio/synthesis.py`: it has one bounded runtime, English/Tamil planning, local
Piper synthesis, cancellation, sensitivity-aware routing, 22 emotion profiles,
  7 speaking styles and a 100-test offline suite.

It is not yet accepted as LYA's final voice. Automated checks prove that it makes
audible, bounded audio; they cannot prove that the voice sounds like one natural
young adult woman or that English pronunciation through the Tamil acoustic model
is acceptable. That decision requires owner listening.

## What is now connected

- `desktop/setup_speech.py` loads `external work/alya_voice` in the existing
  subprocess. It uses the `unified` Tamil female Piper model for both English and
  Tamil, so the acoustic timbre remains consistent across both languages.
- The worker remains alive for at most 45 seconds after a response. This avoids
  loading the model again during an active conversation and releases it after
  inactivity.
- Remote speech is disabled for every desktop call. Interjections are disabled,
  so LYA never adds words that were absent from the answer.
- Desktop speech auditing is disabled. Spoken text and text fingerprints are not
  written by this integration.
- Each rendered audio chunk emits its phrase and measured duration before audio
  playback. The compact answer panel reveals words across that duration and then
  restores the exact full answer, including formatting.
- `voice natural` selects local Piper; `voice economy` selects Windows SAPI.
  Supported language controls are `auto`, `en` and `ta`. Styles are `everyday`,
  `joyful`, `storyteller`, `hacker`, `hype`, `whisper` and `night`.
- Spoken answers have one display path: the normal completed-answer render is
  suppressed while audio-timed captions are active, preventing duplicate text.
- The default style has a real -8% rate offset, reduced synthesis variance and
  gentler jitter/breath processing for clearer words. A `joyful` style provides
  brighter delivery without changing the acoustic speaker.

## Evidence

| Check | Result |
|---|---|
| External voice suite | 100/100 passed |
| Speech transport suite | 5/5 passed |
| Desktop experience suite | 16/16 passed |
| Real `.venv-ui` + real Piper model smoke test | Passed; 2 chunks, 1.25 s mixed English/Tamil audio |
| Static compilation | Passed |
| Offline benchmark | First audio about 2.1–2.8 s; total generation about 2.4–2.9 s |
| Remote transmission | Disabled in desktop integration |

The repository-wide discovery run still has pre-existing failures outside this
integration: stale Windows DPAPI test material cannot decrypt in the present user
context, older Oracle/mock assumptions fail, and the retired experimental
`test_synthesis.py` expectations do not match its current implementation. Those
failures are not evidence against this voice path and were not hidden or changed.

## Owner listening gate

Listen with headphones and normal laptop speakers. Judge identity consistency,
Tamil pronunciation, English accent, sentence rhythm, harshness and whether the
styles still sound like the same person.

- [English warm](../../external%20work/out/reel-01-warm.wav)
- [English cheerful](../../external%20work/out/reel-02-cheerful.wav)
- [English serious](../../external%20work/out/reel-04-serious.wav)
- [Tamil warm](../../external%20work/out/reel-09-warm.wav)
- [Tamil cheerful](../../external%20work/out/reel-10-cheerful.wav)
- [Tamil curious](../../external%20work/out/reel-12-curious.wav)

Acceptance requires the owner to say which samples sound wrong and why. If the
English accent is not acceptable, the single-model `unified` requirement and
native pronunciation conflict: the next experiment should compare a trained
cross-lingual single-speaker model, rather than disguising two speakers with DSP.

Fresh samples made after the slower clarity tuning:

- [Tuned English everyday](samples/english-everyday.wav)
- [Tuned English joyful](samples/english-joyful.wav)
- [Tuned Tamil everyday](samples/tamil-everyday.wav)
- [Tuned Tamil joyful](samples/tamil-joyful.wav)

## Remaining work

1. Owner listening acceptance and native-Tamil pronunciation notes.
2. Measure warm-conversation first-audio latency, process memory and battery use
   over a longer session. The current benchmark's memory field is unreliable.
3. Improve or replace the model only if listening fails; keep the transport,
   privacy policy and caption contract.
4. Build microphone input, echo cancellation and barge-in as a separate task.
   This change provides output speech only.
