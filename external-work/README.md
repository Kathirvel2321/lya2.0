# ALYA voice lab (`external work`)

An isolated voice stack exploring one requirement from the owner's brief: **a
single 21-year-old bilingual (English + Tamil) female voice with many tones,
emotions and styles, that sounds like one person and wants to talk** — without a
paid provider, without a GPU, and without silently uploading private text.

Nothing in this folder is imported by, required by, or wired into the LYA
application. It reuses the Piper model files already pinned in the parent project
(`../models/voice/`) but does not modify the parent project, its stores, its
databases or its runtime.

Read `docs/01-research.md` first for why these engines were chosen and what was
verified on this laptop.

## Status (honest summary)

| Dimension                                                 | State                                                                                           |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Offline synthesis (Piper, English + Tamil)                | **Working** — verified on this laptop                                                           |
| Emotion / style direction                                 | **Working** — 22 emotions, 6 styles, cue inference + explicit tags                              |
| Offline economy fallback (Windows SAPI, English)          | **Working** — refuses Tamil rather than mispronouncing it                                       |
| Remote quality tier (Edge multilingual female)            | **Implemented, disabled by default** — needs opt-in; live quality not yet accepted by the owner |
| Text normalisation (numbers, dates, ₹, %, Tamil numerals) | **Implemented** — Tamil numerals not reviewed by a native speaker                               |
| Test suite                                                | **98 tests, all passing** offline (Piper tests skip if models are absent)                       |
| Listening acceptance (does it actually sound natural?)    | **Not done** — requires the owner's ears                                                        |
| Wired into the LYA app                                    | **No — deliberately not connected**                                                             |

This lab proves the _pipeline_ works and produces audible, emotion-differentiated
audio. It does **not** prove naturalness, and no one should claim otherwise until
a native speaker has listened to `out/reel-*.wav`.

## Layout

```
external work/
├── alya_voice/            the package
│   ├── persona.py         one speaker identity, styles, voice mapping
│   ├── emotions.py        emotion table, tag parsing, cue inference, delivery maths
│   ├── normalize.py       written text -> spoken form (EN + TA)
│   ├── director.py        text -> prosody plan (sentences -> clauses -> spans)
│   ├── dsp.py             pitch/formant/WSOLA/vibrato/breath/loudness
│   ├── privacy.py         sensitivity classification + fail-closed routing policy
│   ├── runtime.py         plan -> engine ladder -> render -> playback (cancellable)
│   ├── cache.py           optional hash-keyed render cache (off by default)
│   ├── audit.py           salted, text-free audit log
│   ├── audiofile.py       minimal WAV I/O + MP3 duration estimate
│   ├── engines/           offline_piper | offline_sapi | cloud_edge
│   └── cli.py             the command line
├── config/                persona.json, emotions.json, policy.json
├── tests/                 the offline test suite
├── tools/                 alya-voice.cmd, run-tests.cmd
├── docs/                  research, architecture, usage, limitations, status
└── out/                   rendered audio, benchmark JSON, audit log (git-ignorable)
```

## Quick start

```cmd
:: from the repository root
external work\tools\alya-voice.cmd doctor
external work\tools\alya-voice.cmd plan "Hey, I'm Alya. 25% done."
external work\tools\alya-voice.cmd demo --silent
external work\tools\run-tests.cmd
```

The launcher uses `../.venv-ui/Scripts/python.exe` when present, otherwise `python`.
See `docs/03-usage.md` for every command, and `docs/02-architecture.md` for how a
sentence becomes audio.

## The three engines

| Engine          | Kind   | Cost                             | Tamil            | Emotion control   | Default          |
| --------------- | ------ | -------------------------------- | ---------------- | ----------------- | ---------------- |
| `offline_piper` | local  | ~63 MB model, CPU, 2 threads     | yes              | DSP + prosody     | **yes** (`auto`) |
| `offline_sapi`  | local  | Windows built-in                 | no (refuses)     | SSML prosody      | fallback         |
| `cloud_edge`    | remote | free, no key, text leaves device | yes (one timbre) | rate/pitch/volume | **off**          |

`auto` never selects the remote engine. The remote engine additionally requires
`config/policy.json` to say `"remote": "opt_in"` **and** an explicit `--remote`
flag on the run, and it refuses anything above `public` sensitivity — private or
personal text is never sanitised and sent, it is routed local or refused.

## What this lab deliberately does not do

- It does not touch the main LYA project, its data, its keys or its stores.
- It does not clone a voice, record anyone, or capture microphone input.
- It does not download models at runtime and does not require an account or key.
- It does not enable the remote engine by default, and it never sends text it has
  classified as personal or private.
- It does not store what it says: the audit log keeps a per-run salted hash only.

## Known limitations

See `docs/04-limitations.md`. The short version: naturalness is unaccepted, Tamil
number words are unreviewed, the offline `unified` timbre trades English accent
for one consistent voice, remote quality is unmeasured, and the DSP is a
deliberate lightweight approximation rather than a neural vocoder.
