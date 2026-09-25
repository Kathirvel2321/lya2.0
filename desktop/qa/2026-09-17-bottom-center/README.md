# Bottom-center experience — 2026-09-17

Implemented in `desktop/experience.py` and the crystal painter in `desktop/app.py`.
The 2.2-second greeting stays at bottom center; an eased 1.1-second crossfade
transforms the cached crystal into a 64 px circular control. Panels open above
it and change geometry over 450 ms. Answers omit decorative headings and reveal
two characters per 40 ms tick using incremental document insertion.

`check-t01.cmd`: all 62 isolated checks passed. Updated experience assertions
cover bottom alignment, circle completion, incremental reveal, hidden answer
title, preserved clock output, cancellation, private denial, layout and stopped
idle repainting. Tests use mocked providers; no live request or sensor ran.

`input.png`, `answer.png`, `chat.png` are synthetic offscreen Qt previews on light
and dark backgrounds, not screenshots of the owner's desktop. Prior previews
remain in the dated 2026-09-16 directory. Run preview generation with:
`$env:PYTHONPATH='desktop;.'; .\.venv-ui\Scripts\python.exe -B -c "from check_experience import preview; preview()"`

No continuous 3D rendering or additional dependencies. Actual battery consumption,
physical monitor smoothness and live AI response quality remain unmeasured.
Next: owner checks the launcher and transition pacing on the real desktop.
