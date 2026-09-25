# Free voice options for a 21-year-old bilingual (English + Tamil) female voice

Researched and verified on 2026-09-22 on this laptop (Windows, Python 3.12.14,
`.venv-ui`). Every claim below is either (a) checked against a file in this
workspace, (b) checked against the installed package source, or (c) sourced from
the vendor/first-party page linked next to it. Nothing here was installed for
this work and no account, key or payment was created.

## Hard constraints given by the owner

1. No paid provider, no subscription.
2. Weak laptop: no GPU, low RAM headroom, no constant background load.
3. One voice. English and Tamil must sound like the same 21-year-old woman,
   with many tones/emotions and styles, not "a different girl per language".
4. Fluent, natural, "wants to talk" - not a robot reading a memo.
5. Secure: no unnecessary upload of private text, nothing new listening in the
   background.

## What is already on this laptop (verified)

| Item | Evidence |
|---|---|
| `piper-tts 1.8.0`, `edge-tts 7.2.8`, `kokoro-onnx 0.4.9`, `sounddevice 0.5.6`, `numpy 2.5.3`, `scipy 1.18.1`, `onnxruntime 1.30.0`, `pywin32 312` | `pip list` in `.venv-ui` |
| Piper Tamil female model `ta_IN-rasa_female-medium.onnx` (63.5 MB) and English `en_US-ljspeech-medium.onnx` (63.5 MB) | `models/voice/` in this repo (269 MB total, already hash-pinned by the LYA project) |
| Edge TTS is reachable and lists **322** voices, including `ta-IN-PallaviNeural` (Female) and the multilingual set `en-US-AvaMultilingualNeural` | `edge_tts.list_voices()` run from this workspace |
| Edge TTS XML-escapes the text before sending SSML, so text cannot inject markup | `edge_tts/communicate.py` line 350 (`escape(remove_incompatible_characters(text))`) |
| Edge TTS exposes only `rate` / `volume` / `pitch` per request, as strict integers (`^[+-]\d+%$`, `^[+-]\d+Hz$`) | `edge_tts/data_classes.py::TTSConfig` |
| Edge TTS **cannot** apply `mstts:express-as` emotion styles: the service then speaks an unrelated default clip | upstream issue rany2/edge-tts#426, closed as *not planned* |

## Candidate comparison

| Option | Licence / cost | Weight on this laptop | Tamil | English | Emotion control | Verdict |
|---|---|---|---|---|---|---|
| **Piper** (local, already pinned) | runtime GPL-3.0, models public-domain / CC BY 4.0 | 63 MB model, CPU, 2 threads, ~0.2 GB peak | yes, female (Rasa) | yes, female (LJ Speech) | none native - pacing only | **Chosen offline default.** Proven in this project, works with no network. |
| **Edge TTS** (Microsoft, free, no key) | free public endpoint; text leaves the device | ~0 load locally, model runs on their servers | yes (`ta-IN-PallaviNeural`) | yes | per-request rate/pitch/volume; no style tags | **Chosen opt-in quality tier.** Only free way found to keep one timbre across both languages. Privacy cost is real and gated. |
| **Kani TTS** (local) | Apache-2.0 | 370-400 M params | **no** | yes | limited without fine-tuning | Rejected: no Tamil. |
| **IndicF5 / AI4Bharat** (local) | research model, reference-audio driven | F5-TTS scale; GPU-class compute | yes | **no** (Indic-only fine-tune) | expressive, controlled by a reference clip | Deferred, not rejected: it needs a *prompt voice* (cloning), and the LYA requirements defer enrollment/voice capture. Also too heavy here. |
| **Kokoro-82M** (local, pinned here) | Apache-2.0 weights | 114 MB int8 | **no** | yes | limited | Rejected for this goal; already rejected as too slow for the English default in the project. |
| **XTTS-v2, Chatterbox multilingual, Orpheus, Higgs Audio** | mixed | GPU-class | **no** | yes | yes | Rejected: no Tamil. |
| **Windows SAPI female voice** (local, installed) | part of Windows | ~0 | no | yes (accent is not Indian) | SSML prosody, support varies by voice | Kept as the offline *economy* fallback (instant, English-only, refuses Tamil rather than mispronouncing it). |
| **MMS-TTS Tamil (VITS)** | CC-BY-NC | ~150 MB, CPU | yes | no | none | Documented only: light and fully offline, but flat and monotone. Not installed or tested here. |

## The key finding

`en-US-AvaMultilingualNeural` is a **single female voice that Microsoft documents
as supporting `ta-IN`** together with English (Azure multilingual voice group;
the locale index marks `ta-IN` as supported). It is also present on the free Edge
endpoint this project already has. That gives a realistic "one girl, two
languages" result at zero cost and near-zero laptop load - at the price of the
sentence text leaving the device, which is exactly what this lab refuses by
default and only allows with an explicit opt-in.

Everything else follows from the `express-as` limitation: since Edge will not act
"cheerful" on request, and Piper never could, emotion has to be produced by *us* -
a prosody director plus light DSP - which is also what makes one voice sound
alive instead of synthetic.

## Sources

- Edge TTS package source: `.venv-ui/Lib/site-packages/edge_tts/communicate.py`
  (`mkssml`, `escape`, `Communicate.__init__`) and `edge_tts/data_classes.py`.
- Upstream style limitation: https://github.com/rany2/edge-tts/issues/426
- Microsoft multilingual voice list and locale index:
  https://raw.githubusercontent.com/MicrosoftDocs/azure-ai-docs/main/articles/ai-services/speech-service/includes/language-support/multilingual-voices.md
- Piper voices and runtime: https://github.com/OHF-Voice/piper1-gpl and the two
  model cards already stored in this repository (`models/voice/`).
- Kani TTS: https://github.com/nineninesix-ai/kani-tts (Apache-2.0, no Tamil).
- IndicF5: https://github.com/AI4Bharat/IndicF5 (11 Indic languages, prompt
  audio required, no English).
- Rasa, the dataset behind the Tamil Piper voice: https://arxiv.org/abs/2407.14056
- Project constraints: `LYA_VISION.md` (zero-subscription budget, existing
  hardware) and `review/2026-09-21-local-voice/README.md` (open voice gates).
