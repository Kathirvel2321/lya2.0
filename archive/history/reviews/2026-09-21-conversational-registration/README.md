# Conversational setup — 2026-09-21

Centered crystal, single prompt and action controls replace the registration rail
and dense cards. The ordinary command panel hides while setup is visible.

Local Windows SAPI reads each stage after the reveal or a 250 ms transition pause.
Voice on/off, Replay, page change, hide and close control a bounded speech child
process. No online speech fallback. Accent indicates process activity, not phonemes.
The camera and microphone remain off; voice input/enrollment are still pending.

44 isolated checks passed: 16 UI, 12 core, 13 experience, 3 speech transport.
Local speech synthesis to memory returned 122344 bytes. Audible playback was not
performed. Battery consumption has not been measured; no idle animation was added.

Restart LYA, enter `register admin`, listen to the greeting, type a name, continue,
try Replay and Voice off, then close. The command input must stay hidden throughout.

`render_preview.py` reproduces the six synthetic frames with speech disabled.
