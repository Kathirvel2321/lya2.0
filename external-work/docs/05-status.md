# 05 — Status and work log

Dated evidence, not proof of current behaviour. Re-run `run-tests.cmd` to confirm.

## 2026-09-23 — Native English voice for the desktop

The desktop now selects native Piper voices per language. English uses
`en_US-ljspeech-medium`, while Tamil keeps `ta_IN-rasa_female-medium`.
The earlier unified Tamil model is still available in this lab but is no longer
the desktop default. Routing/transport and focused engine tests passed;
owner listening and normal-workload battery checks remain open. See
`review/2026-09-23-english-voice/README.md` from the project root.

## 2026-09-22 — Bounded LYA desktop integration

The main desktop speech subprocess now uses `alya_voice.runtime.Voice` with the
unified local Piper timbre. The process stays warm for at most 45 seconds, remote
speech is forced off, interjections are off, and the desktop disables speech
audit records. `Voice.speak()` gained an optional chunk callback; it fires before
playback so the compact UI can reveal each phrase against its measured duration.

Checks after the clarity/duplicate-output pass: 100/100 package tests, 5/5
transport tests and 16/16 desktop experience
tests passed. A real `.venv-ui`/Piper smoke test rendered mixed English/Tamil as
two timed chunks (1.25 seconds of audio). The benchmark measured roughly
2.1–2.8 seconds to first audio. Owner listening and battery/memory soak remain
required; naturalness is not established. Full evidence and samples are in the
project's `review/2026-09-22-external-voice-integration/README.md`.

## 2026-09-22 — Completion pass: 16 failing tests fixed, docs added

When this folder was re-opened, `docs/` contained only `01-research.md`, the
`README.md` referenced by the package did not exist, and **16 of 98 tests failed**.
A saved earlier log (`out/tests-2026-09-22-before-fixes.txt`, and the original
`out/tests.txt`/`out/t2-err.txt`) showed the same failures, so the suite had never
been green. All 98 tests now pass offline, and the CLI produces real audio.

### Root causes found and fixed

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | **All rendered audio was silent** (`peak 0.0`), including the "it speaks" claim | `dsp.time_stretch` had no `return` — it returned `None`, which `pitch_shift` turned into a zero array for every span | Return the overlap-add normalised output |
| 2 | Pitch/time-stretch inaccurate | WSOLA matched the search against the windowed *output* tail instead of the raw input, smearing the fundamental | Match against the raw input tail; time-stretch now holds pitch at ~200 Hz |
| 3 | `breath()` returned all-`NaN` | `np.sin(np.pi*t)` returns a tiny negative at the endpoints; `** 1.5` of a negative is `NaN` | Clip the sine and the edge term to ≥ 0 before the fractional power |
| 4 | **Every explicit emotion tag was silently dropped** (`[emotion:cheerful]`, `<playful>`) | `return explicit[0], SINGLE_TAG_RE.sub(repl, text)` reads the tuple left-to-right, so the tag was read *before* the substitution populated it | Strip first, then read the captured tag |
| 5 | A weak cue in a later sentence overrode a strong earlier emotion | Emotion inference reset per sentence with no continuity | Keep the current emotion unless the new score is at least as strong (or it is the first sentence) |
| 6 | `"I cannot believe it"` classified as `firm` | The `firm` cue list contained bare `"no"` / `"cannot"`, matching negation inside idioms | Tightened to genuine boundary/refusal phrasing |
| 7 | A phone number at end-of-sentence was missed | The lookahead `(?![\d.])` also rejected a trailing sentence period | Reject only a digit continuation (`(?![\d.]\d)`) |
| 8 | An explicitly named remote engine that policy refused was silently downgraded | Substitution happened without telling the caller | `speak()` now raises when a named engine is refused |
| 9 | A pure-silence WAV was exported for path-only (remote) engines and reported as success | Pause padding was appended to the PCM buffer even when a chunk produced no PCM | Only pad a pause when that chunk produced decoded audio |
| 10 | Interjection outcome depended on unrelated prose | The jitter RNG and the interjection draw shared one stream | Interjections draw from their own seeded stream |
| 11 | `plan`/`say`/`demo` crashed on Tamil | `print()` to a cp1252 console raises `UnicodeEncodeError` | Reconfigure stdout/stderr to UTF-8 at CLI entry |
| 12 | `split_sentences('...')` returned a punctuation-only "sentence" | Parts without word characters were kept | Drop punctuation-only parts |

### Checks run

```
external work\tools\run-tests.cmd          98 tests, all passing (exit code 0)
alya-voice.cmd doctor                      all three engines reported with reasons
alya-voice.cmd demo --silent               12 bilingual WAVs written
```

The current run is recorded in `out/tests.txt`; the pre-fix failure logs are kept
as dated history (`out/tests-2026-09-22-before-fixes.txt`,
`out/t2-err-before-fixes.txt`).

Measured on the demo reel (offline Piper, this laptop):

| File | Peak | RMS | Duration |
|---|---|---|---|
| `reel-01-warm.wav` | 0.831 | -16.8 dBFS | 5.45 s |
| `reel-02-cheerful.wav` | 0.919 | -16.6 dBFS | 5.70 s |
| `reel-07-tired.wav` | 0.869 | -16.9 dBFS | 4.68 s |
| `reel-08-surprised.wav` | 0.898 | -16.8 dBFS | 3.48 s |
| `reel-09-warm.wav` (Tamil) | 0.841 | -17.0 dBFS | 3.83 s |
| `reel-12-curious.wav` (Tamil) | 0.901 | -17.1 dBFS | 2.75 s |

All 12 are healthy audio (peak ~0.83–0.92), loudness-normalised to the ~-17 dBFS
target, with durations varying by emotion as intended (`tired` longer per word,
`surprised`/`curious` shorter).

### What is still not done

- **Owner listening acceptance**, especially by a native Tamil speaker. The tests
  prove signal properties, not naturalness.
- Remote (`cloud_edge`) quality — implemented and disabled, only delivery-tested.
- Tamil numeral review by a native speaker.
- Microphone input, echo cancellation, barge-in and battery/memory soak testing.

### Files changed

`alya_voice/dsp.py`, `alya_voice/emotions.py`, `alya_voice/director.py`,
`alya_voice/privacy.py`, `alya_voice/runtime.py`, `alya_voice/cli.py`,
`config/emotions.json`, `tests/test_director.py`, `tests/test_runtime.py`.
Docs added: `README.md`, `docs/02-architecture.md`, `docs/03-usage.md`,
`docs/04-limitations.md`, `docs/05-status.md`.

No file in the parent LYA project was modified.

