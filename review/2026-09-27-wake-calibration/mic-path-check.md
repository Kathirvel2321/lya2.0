# Local microphone path check — 2026-09-27

Owner reports that the prior local listening copy contained LYA playback but no discernible owner voice, with substantial household background noise. No audio was saved or transmitted for this path check.

Windows microphone permission was allowed. LYA's default Realtek array and its WASAPI path both opened and received sound. Lower-level WDM-KS Realtek input paths could not be opened with the blocking stream API. A cued, bounded check using LYA's exact default 16 kHz mono input had weak signal in the spoken-name window. The `DoubleClap` detector returned true in the separate clap window. This verifies one detector event, not the complete desktop wake/greeting flow or repeatability in the room. The earlier owner recording and this signal check do not establish that the owner voice is intelligible to LYA.

Diagnostic: `tools/check_mic_paths.py` (`--lya-only` runs only the exact LYA input check). It stores no audio or transcript. Next: ask the owner to try speaking close to the laptop microphone at the camera bezel, compare the Windows input meter or a local recording with the previous sample, and then run the bounded full wake/greeting check. If close speech is still absent, inspect hardware mute, selected Windows input device and vendor microphone processing before further wake-code changes.
