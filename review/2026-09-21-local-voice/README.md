# Local voice implementation — 2026-09-21

## Implemented and tested

LYA now uses local female neural voices for English (Piper LJ Speech medium) and
Tamil (Piper Rasa Female medium). Tamil/English script changes select the appropriate
voice without translating the answer. Romanized Tamil is not reliably identifiable;
use Tamil script. Switching languages currently changes speaker timbre.

`audio/synthesis.py` handles bounded spoken text, language routing, CPU inference
and playback. `desktop/setup_speech.py` runs it in a cancellable child process:
stdin JSON, no shell, no speech upload, no persisted reply audio. Neural models
are loaded on demand, limited to two CPU inference threads with idle spinning off,
and released when the reply completes. No microphone opens for speech output.

`desktop/experience.py` speaks only the current completed brain result, never the
old panel title. Closing, a new command, mute, and quit cancel speech. File-open
acknowledgments follow the actual read result; failure does not announce success.
There is no fabricated generic task-complete event. This does not validate the
truth of an LLM response or implement an arbitrary task executor.

Registration uses the same renderer and its existing mute/replay controls. Legacy
`audio/voice.py` output now also uses local synthesis instead of silently sending
text to Edge TTS. Transcription defaults to offline; explicit legacy remote calls
remain possible. Speech output does not itself make remote AI answers private.

## Try it

Restart `launch-lya.cmd`, then ask an ordinary question. Spoken replies start enabled.
Type `voice off` to mute, `voice on` to enable, or `stop speaking` to interrupt.
`voice natural` selects the local neural engine. `voice economy` selects the
installed English female Windows voice (Zira here); it refuses Tamil rather than
mispronouncing it. Preferences are session-only.

`voice style warm`, `calm`, `cheerful`, `serious`, or `neutral` adjusts pacing.
These are NOT emotion-conditioned acting or a promise of human emotion.
`voice language auto` routes Tamil/English/Devanagari by script. Explicit `en`,
`ta`, `hi`, `fr`, `es`, `it`, `pt` codes are accepted. Only Tamil and English have
been benchmarked; the other five use the slower experimental Kokoro path and are
not production-qualified. Unsupported scripts fail visibly and leave text intact.

Synthetic samples: [English](english.wav), [Tamil](tamil.wav).
No owner voice was recorded or cloned. Speaker playback, pronunciation, perceived
naturalness, loudness consistency and long-conversation comfort need human QA.

## Evidence and limits

Latest sequential benchmark (`benchmark.json`): English 3.704 s synthesis / 4.725 s
audio; Tamil 4.214 s / 3.994 s. First audio 3.212 / 3.765 s respectively. This is
one short synthetic run, not p95 latency or a battery measurement. Results vary
with load and stochastic synthesis. Process peak working set: 181.7 MB for this
benchmark (`memory.json`), not the entire LYA application or a worst-case ceiling.

Initial Kokoro English result was 43.943 s / 4.331 s audio, so it was rejected as
the default (`initial-kokoro-benchmark.json`). An adapter fixes the upstream
0.4.9 int32 speed conversion for the pinned float-speed export.

Checks: 20 voice/synthesis/transport tests passed, one explicitly online test
skipped; 28 registration checks passed; 15 desktop experience checks passed.
All use synthetic inputs/mocks/temporary stores. No live microphone or enrollment.

Production gates still open: owner listening tests for Tamil/English and mixed
phrases; multilingual text normalization (numbers, abbreviations, names);
consistent cross-language persona; emotion-conditioned model evaluation; p50/p95
latency, underruns and battery measurements; bounded local ASR with visible
microphone consent; echo cancellation and reliable barge-in; long-session soak
and audio device removal/reconnection. This is working speech output, not a
finished production conversational voice system.

## Reproduce and model sources

Install `audio/requirements-voice.txt` into `.venv-ui`, then run
`.venv-ui\Scripts\python.exe tools/install-voice-models.py`.
The installer checks exact SHA-256 and sizes from `models/voice/manifest.json`.
Pinned weights are ignored by Git; metadata/configs remain in the project.
Playback never downloads models. Synthetic WAV files in this review are generated
artifacts, not downloaded reference recordings.

- English: https://huggingface.co/rhasspy/piper-voices/tree/c10ece1aade47bb51c153c893d14e5bf8e5b7117/en/en_US/ljspeech/medium
  Female LJ Speech dataset, public domain per model card. Card saved in models/voice.
- Tamil: https://huggingface.co/tinisoft/piper-ta_IN-rasa_female-medium/tree/89e15edafc8b31e66ddf25f2adbe3bd3f20a9496
  CC BY 4.0. Attribution: tinisoft model trained on AI4Bharat Rasa;
  Praveen Srinivasa Varadhan, Ashwin Sankar, Giri Raju, Mitesh M. Khapra,
  “Rasa: Building Expressive Speech Synthesis Systems for Indian Languages in
  Low-resource Settings”, INTERSPEECH 2024. https://arxiv.org/abs/2407.14056
- Piper runtime: https://github.com/OHF-Voice/piper1-gpl — GPL-3.0 runtime;
  preserve its license/source obligations when distributing.
- Experimental Kokoro: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
  Apache 2.0 weights; https://github.com/thewh1teagle/kokoro-onnx MIT wrapper.
  Published language list does not include Tamil. No claim of universal mastery.

Agent-reach search/update executables were unavailable; official model cards and
runtime source were inspected using web fallback. No API credentials were needed.
