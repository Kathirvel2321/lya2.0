# Window controls and crystal rotation

Implemented 2026-09-17 in `desktop/experience.py`, `desktop/app.py`, and
`brain/workflow.py`. The fixed-size crystal mask caused the clipped circular
window; the compact experience now clears it. The system prompt requests only
the direct answer, with material uncertainty when needed. No live model output
was checked in this UI task, so provider compliance is not guaranteed.

Ordinary answer cards contain only text. Click the circle for input. Commands:

- `open chat box`, `close chat`, `make it full screen`, `restore chat`.
- `show two files`, `show three files`, or `show README.md and LYA_VISION.md`.
- `stay as a crystal`, `become a circle`.

Conversation updates are incremental: existing chat history remains fixed, the
new question appears immediately, and only the newest LYA reply is typewritten.
The temporary transcript remains bounded to 12 speaker entries and clears when
the panel closes.
After a compact answer finishes, typing a printable character changes the card to
input mode and keeps that first character; Enter opens an empty input. Control,
Alt and Meta shortcuts remain shortcuts. Typing is ignored while answer reveal is
still running, so it cannot accidentally cancel an unfinished response.

Drag chat/answer cards by their top edge; drag file windows by their native title
bar. File windows can be resized, maximized and closed independently. Moving the
orb does not move existing windows. Placement minimizes overlap among LYA's
windows; it cannot detect other applications' occupied space, and small displays
may require overlap. Only the four existing allowlisted project documents are
available, with the existing 64,000-character limit; arbitrary private files are
not newly authorized.

The greeting expands from the bottom-center circle to a centered crystal, plays
one 360-degree turn, then returns. Stay-crystal keeps the crystal visible. Rotation
uses 48 cached 288x408 GLB renders (about 3 MB compressed, about 22 MB decoded), at
20 frames/second for a finite burst. `desktop/bake_crystal.py` now accepts an angle
through its Python function. Frames/reports: `desktop/assets/rotation/`. Original
GLB is unchanged. Reduced motion skips rotation; idle repainting stops.

Synthetic previews: `input.png`, `answer.png`, `chat.png`. These are offscreen Qt
renders, not a physical Windows desktop trial. Tests cover mask removal, plain
answer layout, chat controls, independent files, persistent crystal, and complete
rotation shutdown. Physical smoothness and battery use still need owner testing.

Follow-up verification: all 66 isolated checks passed. The added regression check
keeps an earlier reply exactly once while a second reply advances incrementally;
the full backend, privacy, base UI, window and animation suite also passed.
The later compact-input regression brings the full total to 67 isolated checks.
