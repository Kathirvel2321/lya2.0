# LYA review — 2026-09-13

Your additions are real progress, particularly person-scoped encrypted storage,
synthetic identity tests and voice-to-Qt signal dispatch. LYA is not yet a working
end-to-end personal assistant. Passing component tests currently hides several
integration defects. This review did not modify application behavior.

## Findings, in priority order

| Priority | Finding | Evidence and effect | Next correction |
|---|---|---|---|
| P1 | Missing person ID selects the first stored person | `brain/mind.py:127–140`; `_memory_block()` picks `people[0]`. `main.py:182` calls a verified response without a person ID. Fake-data probe reproduced selection of the first profile. | Require an explicit authenticated person ID; missing identity must yield no private context. |
| P1 | Scoped-memory errors fall back to unscoped legacy memory | `brain/mind.py:138–140`; an exception returns `brain.memory.recall()` instead. Reproduced with a simulated store error. | Fail closed and show a recoverable storage error; do not change the data owner on failure. |
| P1 | Authentication credentials can enter model context | `vision/identity.py:120` stores secondary password hashes as credential-kind memories. `brain/mind.py:136` reads every kind. A synthetic credential marker appeared in model-context text. No real credential was accessed or transmitted. | Exclude credential kinds from model context using an explicit content allowlist; preferably separate authentication records from conversational memory. |
| P1 | Desktop voice imports are broken under the documented script layout | `desktop/app.py:620` imports sibling `audio`, but the script directory is `desktop/` and no project-root setup exists. Reproduced `find_spec('audio') == None` with that script path. Tests/bootstrap add the parent path, masking this gap. Errors only print from the background thread. | Use a consistent package entry point or establish imports explicitly; add a test of the actual launcher. Surface startup failure in the panel. |
| P2 | Legacy runtime checks the old identity file after registry migration | `main.py:88` gates recognition on `vision/known_faces.lya`, while `vision/identity.py` now uses `storage.store`. Fake missing-file probe confirmed recognition is never called. | Query the current registry; carry its person ID into the session and memory calls. Test new enrollment fixtures through the runtime, not only identity functions. |
| P2 | Voice labels and offline behavior disagree | `desktop/app.py:341` always says microphone off, including after voice is enabled. The start method calls itself offline, but `audio/voice.py:119` uses Google transcription without a Vosk model. | Show actual microphone state, require the local model for offline mode, and make failure visible. |
| P2 | Expired pending faces can still be promoted | `storage/store.py:474` selects by ID without checking expiry. Cleanup runs on list/write, so direct promotion can bypass it. Reproduced an expired synthetic pending record being promoted. | Enforce expiry inside the promotion transaction. |
| P2 | The new UI still has no identity, memory or model command route | `desktop/app.py::command` handles files/time/status/presentation commands. The voice bridge invokes that same handler. `main.py` remains a separate Tk runtime. | Complete one native text → scoped operation → result → cancel journey before expanding features. |

The five reproduction booleans in [review_probes.py.txt](review_probes.py.txt)
are **defects reproduced**, not passing acceptance gates.

## What works in the checks

| Suite rerun | Result | What it establishes |
|---|---|---|
| Storage | 8/8 | Fake person records, encrypted roundtrip, scoped reads, thread writes, template CRUD and basic promotion |
| Identity | 5/5 | Synthetic embedding matches, unknown routing, fake password checks and forget; no real camera/model accuracy evidence |
| Mind | 5/5 | Explicit-person prompt scoping, mock replies, history separation and fallback messaging; the new probes expose missing cases |
| Voice | 7/7 | WAV framing, parsed-text wake routing, conversation timing and synthetic audio heuristics; no microphone/transcription test |
| Native UI | 10/10 | File loading, bounds, cancellation, keyboard controls, palette isolation and synthetic voice signals |
| Total | **35/35** | Component evidence only; the earlier ledger's full 113-test claim was not independently rerun here |

Reproduction command:

```powershell
.\.venv-ui\Scripts\python.exe -B review\review_20260913.py
```

The harness copies only source, project documents and UI artwork to temporary
storage. It uses temporary runtime directories and a newly generated test key,
blocks network/camera/microphone access and supplies a fake TTS engine. It does not
copy existing secrets, biometric records or private databases. Test imports are
explicitly bootstrapped; this is why the separate launcher-path check matters.
No physical sensor, real person, model endpoint, phone or external repo was run.

The short UI sample measured 2.643 ms median and 3.873 ms maximum paint time over
2.516 seconds. That excludes real sensor/model workloads and is not a sustained
FPS or battery-use guarantee. [Timing](measurement.json) · [Suite results](results.json).

## Installed components and repositories

Read-only checks of the active `.venv-ui` environment found PySide6, NumPy,
cryptography, pywin32, OpenCV headless, ONNX Runtime, sounddevice, Vosk and pyttsx3.
The installed OpenCV distribution is `opencv-python-headless`, not the name in
the root requirements file. PySide6 Essentials is 6.11.2; OpenCV headless is
5.0.0.93; Vosk is 0.3.45.

Missing in this environment: `insightface`, `torch`, and `speech_recognition`.
The configured/default Vosk model directory was absent, as was the default
InsightFace buffalo_l directory. Other model locations were not searched.

`security/Silent-Face-Anti-Spoofing/` exists but contains **zero entries**. It is
not an installed source checkout with weights. No `.git` checkout markers were
found inside this project, excluding dependency/cache directories. This does not
rule out ZIP downloads or repositories stored elsewhere. The owner was asked for
their folder paths/names; that part of the review remains pending.

Installing an agent skill, downloading a repository, installing a Python package,
and wiring a component into the running LYA app are separate milestones. For each
additional repo, record its purpose, local path, revision/license, required models,
actual LYA call site and one integration test before marking it usable. No new
repositories or packages were installed in this review.

## Design assessment

The current panel has good contrast, legible text, consistent spacing and a useful
compact footprint. Its silhouette, rounded buttons and fixed-height body resemble
a conventional desktop card more than the futuristic presentation the owner wants.
Short messages also leave a large empty central area.

Recommended visual direction, not yet implemented:

1. Subtle angled corners and fine framing details, retaining the readable glass fill.
2. A short visual connection to the crystal during reveal; let the card feel attached
   to LYA rather than a disconnected window.
3. Content-sized message cards, with bounded scrolling for documents and file lists.
4. A compact task-state strip with truthful microphone/working/error indicators.
5. Restrained state-driven light and movement; preserve keyboard controls and reduced
   motion. Avoid permanent decorative animation that competes with the content.

This can build on the existing native Qt UI. No additional UI repository is needed
to establish that visual direction. [Current message render](message-desktop.png)
and [light-background file render](light-desktop.png) were reviewed.

## Recommended next work

First close the memory-boundary defects and launcher/voice-state gaps. Then finish
one typed native journey using a fake authenticated session and temporary storage.
Apply the futuristic visual revision to that working journey. Physical voice and
camera acceptance follow with explicit device testing; enrollment remains deferred.
Treat prior completed-status entries as dated component evidence, not whole-product
completion. The source and older artifacts have been preserved.
