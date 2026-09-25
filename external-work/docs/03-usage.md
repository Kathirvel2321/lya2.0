# 03 — Usage

Every command below is offline unless it says otherwise. Run them from the
repository root with the provided launcher, or from this folder with
`$env:PYTHONPATH = (Get-Location).Path` and the venv Python.

```cmd
external work\tools\alya-voice.cmd <command> [options]
external work\tools\run-tests.cmd
```

## Global options

| Option | Meaning |
|---|---|
| `--persona PATH` | load a different persona JSON |
| `--models DIR` | directory holding the Piper `.onnx` models |
| `--timbre unified\|native` | one timbre for both languages (**default**) or one model per language |
| `--seed N` | reproducible prosody (same seed → same plan) |
| `--keep-warm` | keep model memory between calls (faster, more RAM) |

## `doctor` — is anything usable?

```cmd
alya-voice.cmd doctor
alya-voice.cmd doctor --remote
```

Prints the persona, styles, emotion count, policy, audit/cache location, timbre,
and each engine's availability with a reason. `--remote` also asks whether the
remote engine *would* be allowed (it still will not call it).

## `plan` — inspect prosody without speaking

```cmd
alya-voice.cmd plan "Hey, I'm Alya. 25% done, and 1,204 files are safe."
alya-voice.cmd plan "வணக்கம், நலம்." --emotion warm
alya-voice.cmd plan "No, stop." --style hacker --seed 7
```

Shows each span's language, emotion, rate/pitch/volume deltas, pause and text,
then the same plan as JSON. This is the fastest way to see *why* something sounds
the way it does.

## `say` — speak

```cmd
alya-voice.cmd say "Good evening. The backup finished four minutes ago."
alya-voice.cmd say "சூப்பர்! வேலை முடிந்தது." --emotion cheerful --wav out/ta.wav
alya-voice.cmd say "Important. Do not open that link." --style serious --silent
```

| Option | Meaning |
|---|---|
| `--emotion NAME` | force an emotion (see `config/emotions.json`) |
| `--style NAME` | delivery style (see `config/persona.json`) |
| `--language auto\|en\|ta` | force a language instead of detecting |
| `--engine auto\|offline_piper\|offline_sapi\|cloud_edge` | pick an engine |
| `--remote` | acknowledge that text will leave the device (remote only) |
| `--silent` | render without playing |
| `--wav [PATH]` | export a mono 16-bit WAV (auto-named if no path) |
| `--no-interjections` | disable the discourse markers ("mm, okay so") |

Prints a JSON report: engine used, spans, chunk count, first-audio ms, total ms,
audio seconds, sensitivity, any findings, and notes explaining every fallback.

## `demo` — the bilingual emotion reel

```cmd
alya-voice.cmd demo --silent          :: writes 12 WAVs into out/, plays nothing
alya-voice.cmd demo                   :: writes and plays
alya-voice.cmd demo --infer           :: infer emotion from cues instead of fixed tags
```

Twelve lines — eight English, four Tamil — across warm, cheerful, playful,
serious, worried, sympathetic, tired, surprised and curious, plus a private-text
line that the policy refuses. **Listen to these files before trusting any claim
about naturalness.**

## `bench` — latency, audio seconds, memory

```cmd
alya-voice.cmd bench --engine offline_piper
```

Renders the benchmark set, prints per-case ms, audio seconds and real-time factor
(RTF), then writes `out/bench-<engine>-<timestamp>.json` including the process
peak working set.

## `redact` — classification and routing, no speaking

```cmd
alya-voice.cmd redact "my password is hunter2"
alya-voice.cmd redact "mail ravi.k@example.com about the backup"
```

Shows the sensitivity level, each finding (masked), the redacted text, and what
each engine would be allowed to do. Useful for verifying the privacy boundary
before wiring anything.

## `voices` — the voice map

```cmd
alya-voice.cmd voices
alya-voice.cmd voices --list-remote ta-IN   :: network: queries the live Edge list
```

## `remote-probe` — the only command that talks to the network

```cmd
alya-voice.cmd remote-probe --remote
```

Refuses unless `config/policy.json` says `"remote": "opt_in"` **and** `--remote`
is passed. Renders two short clips (one English, one Tamil) through the Edge
multilingual voice and writes `out/remote-probe-*.json`. It proves *delivery*, not
quality, and it means that text left the laptop — only run it with text you are
happy to send.

## Environment variables

| Variable | Effect |
|---|---|
| `ALYA_VOICE_MODELS` | override the Piper model directory |

## Where output goes

| Path | Contents |
|---|---|
| `out/reel-*.wav` | the demo reel |
| `out/say-*.wav` | auto-named exports from `say --wav` |
| `out/bench-*.json` | benchmark results |
| `out/remote-probe-*.json` | remote probe results |
| `out/audit/voice-audit.jsonl` | append-only log — **salted hash only, never the text** |
| `out/cache/` | render cache (only when enabled in policy) |
| `out/remote/` | temporary MP3s from the remote engine, deleted on close |

## Adding an emotion or style

1. Edit `config/emotions.json` — add a name with `rate_pct`, `pitch_hz`,
   `pitch_range`, `volume_pct`, `pause_scale`, `breath`, `humanize_cents`,
   `contour`, `description`, and `cues`.
2. Or edit `config/persona.json` `styles` to add a delivery vector.
3. Run `alya-voice.cmd plan "..." --emotion <name>` and listen.

Values are clamped by `persona.json → delivery_limits`, so an over-bright edit
cannot send an absurd request to an engine. `docs/02` explains the maths.
