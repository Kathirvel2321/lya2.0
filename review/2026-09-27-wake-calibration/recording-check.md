# Owner-requested local recording check

2026-09-27. Owner reports maximum Windows input volume but a low meter, and explicitly requested recording input to assess audibility. Captured one ten-second sample from the selected input at its native rate. Kept the strongest input channel as mono for assessment. Created an original and a louder listening copy in an owner-local temporary `lya-voice-check-*` directory, outside the repository. No recording, transcript, detailed runtime reading or voice-derived identity information belongs in this ledger.

The sample had very low level without clipping. A bounded louder copy was tested with local Vosk alongside the original. Neither recovered the requested test phrase. That establishes a weak signal and unsuccessful local recognition, not proof that the sample contains no audible speech. The assistant did not listen through a cloud audio model and must not claim a personal listening judgment. No audio or transcript was sent online by the diagnostic.

Provide the owner the local playback files to distinguish faint but understandable speech from noise/wrong input. Do not apply global gain, change Windows settings, enroll a voice, or claim successful wake based solely on boosting the sample. The files are temporary diagnostic artifacts retained for the owner's playback; they are not training/enrollment samples. Production source and settings were unchanged in this turn.

Next: owner confirms whether the louder sample contains their recognizable voice. If it does, investigate capture level/gain; if it does not, inspect the selected physical input/microphone path. Human wake and greeting acceptance remain open.
