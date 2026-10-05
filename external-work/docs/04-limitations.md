# 04 — Limitations

What this lab does **not** establish. Read this before repeating any claim about
the voice as though it were proven.

## Naturalness is unaccepted

The pipeline produces audible, emotion-differentiated audio, and the tests check
signal properties (peak, loudness, pitch ratio, duration). None of that proves the
voice _sounds good_. That requires a human listener, and specifically a native
Tamil speaker. Until `out/reel-*.wav` has been listened to and accepted, the
correct description is "renders speech with directional emotion", not "sounds
natural".

## Tamil number words are unreviewed

`normalize.number_to_words_ta` builds Tamil numerals from a rule table
(`ஆயிரம்`, `இலட்சம்`, `கோடி`, `சதவீதம்` …). It was not written or checked by a
native speaker. Long compound numerals may sound formal or stilted, and month
names, ordinals and units are approximations. English number handling is the more
trustworthy of the two.

## One timbre is a trade-off, not a free win

- `unified` gives one consistent voice across both languages by speaking both
  through the Tamil-trained Piper model — English then carries a noticeable accent.
- `native` gives a better English model, but two different female timbres, i.e.
  two different-seeming people.
- The remote `en-US-AvaMultilingualNeural` is the only _free_ way found to get one
  timbre across both languages properly, and it costs privacy.

There is no offline, free option that is simultaneously accurate in both
languages _and_ one timbre. This is a genuine constraint, not a tuning problem.

## Emotion is direction, not acting

The 22 "emotions" are delivery targets: rate, pitch offset, contour, pause scaling,
breath and micro-vibrato. They are not trained emotional speech, and cue inference
is a keyword/punctuation heuristic with continuity, not sentiment analysis. Two
consequences:

- A cue can misfire. The `firm` cues were tightened during development because a
  bare `"cannot"` matched _"I cannot believe it"_ and turned astonishment into
  refusal.
- Emotion never changes **what** she says — only how. That is deliberate, but it
  means emotion is expressed entirely through prosody, which is a weaker signal
  than genuine emotional speech.

## The DSP is an approximation

`dsp.py` is deliberately lightweight: WSOLA-lite time-stretch, linear resampling,
cepstral spectral-envelope formant correction, micro-vibrato and additive breath.
It is not a neural vocoder and not high-fidelity phase vocoding. Measured pitch
accuracy is within ~6% on a test tone (the suite asserts this), which is fine for
delivery shaping and obviously not fine for singing. Pitch shifting is the only
non-trivial stage and is bounded to short spans.

## Remote quality is unmeasured

`cloud_edge` has been exercised for _delivery_ (a clip comes back), not for
quality, latency on a poor connection, or consistency across languages. It is off
by default. Enabling it means the sentence text leaves the device, which the LYA
project refuses by default; the opt-in exists so that decision is explicit and
per-run, not implicit.

## Not integrated, and not automatically safe in the app

Nothing here is wired into LYA. There are no tests proving this stack behaves under
the app's real threading, approval or session model. If it is ever integrated, that
integration needs its own privacy review — the fail-closed policy here is evidence
for the _voice_ boundary only.

## Windows-specific pieces

`offline_sapi` (via `pywin32`), the MCI file-player in `runtime._play_file`, and the
`GetProcessMemoryInfo` peak-working-set measurement in the CLI are Windows-only.
The Piper engine, director, emotions, normaliser, DSP and privacy layers are
platform-independent Python.

## Resource figures are not guarantees

Any peak-memory or latency number recorded from `bench` is a single short run on
one laptop. It is not a battery, thermal or worst-case-resource guarantee.

## Voice cloning and enrollment are out of scope

This lab does **not** clone a voice, record anyone, or capture microphone input.
Voice-driven identity (speaker verification) is a different problem and is tracked
separately in the parent project, where enrollment remains deferred.
