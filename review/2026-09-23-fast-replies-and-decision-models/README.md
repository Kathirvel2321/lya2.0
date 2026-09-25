# Fast replies and decision-model fit — 2026-09-23

The owner reported that the response text was held back while voice and letters
were roughly synchronized. In the desktop path, `on_brain()` cleared the normal
answer reveal and `begin_spoken()` waited for the first local TTS chunk. The
previous English benchmark took 4.9 seconds to first audio on a cold start.
That made completed answers look slow even after inference had finished.

Changed `desktop/experience.py` so answer text starts revealing as soon as the
brain result arrives, independently of TTS. Longer answers use larger groups of
characters on the existing 40-ms Qt timer and finish in at most 30 ticks (about
1.2 seconds of animation). Short answers keep the small type-on effect. This
adds no model, process, timer or idle animation. Voice remains enabled and local,
but its start may lag behind already visible text. This does not shorten the
network/model's time to produce the completed answer, nor the cold TTS startup.

Validation: 17 isolated desktop experience checks passed, including a new
regression that reveals a spoken answer without a speech caption and finishes a
long answer in 30 ticks. Real interactive playback and battery measurements
remain untested.

The three linked projects are different from speech synthesis:

* [Laya](https://github.com/NandhaKishorM/laya) is an open-weight typed
  decision/classification engine. It does not generate answer text or speech.
  The author's English/multilingual checkpoints are 421M/322M parameters. Its
  benchmark is mainly on a T4 GPU; the README warns that zero-shot typed
  decision accuracy is near chance without task-specific fine-tuning. On this
  laptop, it needs a separate memory and accuracy benchmark before adoption.
* [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) is browser
  automation code. It calls the hosted TypeSafe Jev decision service and a
  separate text model API. Its one flight-search speed claim is not a LYA voice
  or general answer-latency benchmark. It would add browser and network work.
* [TypeSafe Jev](https://docs.typesafe.ai/) selects among typed actions/choices.
  It does not write conversational replies or synthesize audio. It may later
  help choose browser/UI actions, subject to privacy, cost and task-success
  tests, but does not address the current display bottleneck.

Decision: do not install any of these for the current voice/display issue.
For a future action-routing experiment, first define a small labelled LYA task
set and compare accuracy, latency, memory, cost and abstention against the
existing rules. Keep the current authorizing policy separate from any model's
suggested action.
