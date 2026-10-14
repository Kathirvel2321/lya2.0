# English voice decision — 2026-09-23

The owner accepted the current Tamil voice but rejected English spoken with the
Tamil acoustic model. The desktop now selects the installed native English Piper
`en_US-ljspeech-medium`; Tamil remains `ta_IN-rasa_female-medium`. Both run locally.
No model was downloaded and no cloud speech was enabled. The two languages now
have different speaker identities. The requested youthful, conversational sound
has **not** been established by listening.

Public, synthetic listening samples: [English everyday](english-everyday.wav),
[English joyful](english-joyful.wav), [Tamil everyday](tamil-everyday.wav).
The exact reproducible test is [benchmark_native.py](benchmark_native.py).

Measured on this laptop with silent rendering: the cold English everyday line
took 6.0 s total / 4.9 s to first audio for 4.64 s of speech, with 222 MB peak
process working set. A warm English joyful line took 0.91 s total / 0.24 s to
first audio for 4.46 s of speech. Loading the Tamil model raised peak process
working set to 376 MB; its cold line took 5.1 s total / 4.6 s to first audio.
These are one-run measurements, not a battery or p95 guarantee.

An already-installed Kokoro candidate was tried with a two-thread, low-priority
20-second limit on a short public phrase; it timed out and was not put in the
desktop path. Prior measurements of Kokoro were also far slower than real time.
No additional heavy model was installed.

Validation: six `test_setup_speech` checks and 42 focused voice tests passed.
This establishes routing, rendering and stream behavior. It does not establish
that English sounds like a 20-year-old, that an English/Tamil code-switched
sentence is flawless, or that ordinary-workload playback has no glitches.

Next: owner listens to both English samples in a normal LYA session. If the
English voice still sounds too mature or read aloud, evaluate another small
local English model under the same RAM, startup and listening gates. Keep
private speech local unless the owner explicitly changes the privacy policy.
