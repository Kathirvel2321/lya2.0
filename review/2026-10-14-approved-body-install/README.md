# Approved desktop body installation — 2026-10-14

Owner approved the reference-matched curved blue glass design and requested
replacing the current LYA body. Installed the approved render unchanged at
`desktop/assets/lya-reference-body.png` and its self-contained model at
`desktop/assets/lya-reference-body.glb`.

The existing main-checkout launcher runs `tools/start_nvidia_lya.py`, which loads
`desktop/app.py`. Crystal now loads the new transparent render. Startup selects
the approved default rather than overriding it with the old experimental bake.
That legacy artwork remains an explicit option; original source images remain.
Voice, hearing, authentication, storage, controls, palettes, decorative effects,
circle docking and launcher configuration were not changed. No PR merge.

The owner-approved design came from the isolated PR worktree's
`visual creativity/model/reference-matched/` output. Front highlights are baked
from the reference onto closed relief geometry; depth and rear glass are authored.
The desktop uses the PNG, not a real-time GLB renderer. The GLB is preserved for
future model work, not imported by the assistant.

Verification: `.venv-asr/Scripts/python.exe desktop/check_approved_body.py` passed
five native synthetic states: resting, listening, thinking, speaking, docked.
Also verified the exact installed image, transparency, startup selection,
keyboard activation, reduced-motion idle timer and legacy-toggle return.
Results: [validation.json](validation.json), [listening](listening.png),
[docked](docked.png). The listening render was visually inspected.
The isolated script imports Crystal only; it never constructs Desktop or starts
microphone, camera, brain, private stores or network services.

Read-only Windows process check found no LYA Python process. The full assistant
was not launched or voice-tested. Next normal owner launch loads the new artwork.
Local installation only: no commit, push, merge or cloud/mobile deployment.
Pre-change desktop source is preserved in `app-before.py`; earlier artwork assets
remain in their existing paths. Other uncommitted work is preserved.
