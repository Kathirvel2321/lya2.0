# First-run setup, voice-first start and glass surface — 2026-09-25

Owner asked: stop making a separate workflow, make the existing `launch-lya.cmd`
path behave like a new phone (setup first, then LYA opens), stop requiring typed
commands, and give the panel a modern glassy look with faster speech.

No new workflow was added. Everything below changed the existing launcher.

## What changed

### 1. First run sets up before LYA opens

- `desktop/experience.py`: added `needs_owner_setup()`, `begin_owner_setup()` and
  `on_setup_dismissed()` to `OrbDesktop`.
  - `needs_owner_setup()` reads the encrypted store and returns True only when it
    is readable **and** holds no primary administrator. An unreadable store
    returns False, so a damaged store can never silently open owner setup.
  - `begin_owner_setup()` hides the orb, opens the six-act activation dialog, and
    subscribes to both outcomes.
  - Closing setup leaves a usable docked guest orb with
    `SETUP NOT FINISHED · SAY "REGISTER ADMIN" TO CONTINUE` rather than a locked
    window.
- `desktop/experience.py`: on first run, `on_admin_authenticated` now waits for
  the dialog to finish and then plays the normal orb introduction, instead of
  showing a second "admin verified" panel.
- `desktop/app.py`: `main()` calls `begin_owner_setup()` when required and
  `start_intro()` otherwise. New flags: `--skip-setup` and `--no-voice`.
  `--voice` is kept for compatibility but is no longer needed.

Result: `launch-lya.cmd` shows setup by itself on a fresh machine. Nothing to type.

### 2. Voice-first instead of typing

- `desktop/app.py`: the voice listener starts by default. Typing is now the
  fallback, not the entry point.
- `Desktop.start_voice(allow_cloud=False)` replaces the old signature. The
  caller decides whether remote transcription is allowed.
- `main()` resolves the configured transcriber key and passes `allow_cloud=True`
  only when one exists. The listener reports which mode is live, on screen:
  `TRANSCRIPTION REMOTE (GROQ)` or `LOCAL VOICE LISTENER RUNNING · AUDIO STAYS ON
  DEVICE`. The microphone mode is never hidden from the owner.
- Why voice did not work before: `wake_loop` was started with
  `offline_required=True`, and no local Vosk model exists on this machine, so the
  listener raised and stopped. With the local model absent, `transcribe()` now
  reaches the already-implemented Groq Whisper path when a key is configured.

### 3. Faster speech

- `desktop/setup_speech.py`: added `prewarm()`. The local voice worker is loaded
  at launch and then kept warm for 45 seconds idle, so the first answer is spoken
  without paying the model-load cost at answer time. A `warming` flag
  distinguishes pre-loading from a real request; `stop()` and `_finished()` clear
  it.
- `desktop/app.py`: `main()` calls `speech.prewarm()` before the orb appears.

### 4. Glass surface

- `desktop/app.py` `GlassPanel`: an accent glow behind the panel, a three-stop
  translucent gradient, a lit inner rim and a top-light sheen over a rounded
  corner radius of 24. Buttons gained a pressed state and a brighter hover; the
  input well is deeper and the focus ring stronger.

## Checks

| Suite | Result |
|---|---|
| `test_activation.py` (incl. 2 new first-run gate tests) | 22 passed |
| `desktop/check_ui.InterfaceChecks` | 16 passed |
| `desktop/check_experience.ExperienceChecks` | 23 passed |
| `test_registration_ui.py` | 22 passed |
| `test_router` / `test_oracle` / `test_provider_setup` / `test_brain_workflow` | 14 / 8 / 3 / 41 passed |

The two new tests assert that `needs_owner_setup()` is True on an empty
temporary store, False once a device admin exists, and False for an unreadable
store path. All runs were offscreen with injected sensors and a temporary
encrypted store.

`activate-lya.cmd` was restored: it is committed and documented as a direct way
to open the walk-through.

## Still blocked — this is what stops you registering

The owner's own dated report (`review/2026-09-25-admin-activation-refresh/README.md`)
records that everything works **except the Windows proof**: the locally built,
unsigned `security/HelloVerifier.exe` is stopped by **Windows Smart App Control**
before it runs, and Microsoft provides no per-app approval for that policy. Camera,
microphone and the local speech worker were all confirmed working outside the
restricted tool session.

So the first-run experience now opens by itself, but the final "Create admin"
step still fails until the Windows proof is replaced. Two legitimate paths, and
neither one requires weakening Windows:

1. **Reviewed in-process consent** — call the Windows credential/consent API from
   inside the signed Python process via `ctypes`, so no new unsigned binary is
   created. This is the smaller change and the likely unblock.
2. **A trusted signed helper** — sign the existing helper with a certificate the
   machine trusts, then keep the current design.

This task implemented neither: it is a security-critical change to a
fail-closed gate and the owner should choose the path first.

## Limits

- No real camera, microphone, Windows prompt, admin profile or enrollment was
  performed. Everything was offscreen with fakes.
- Latency was improved structurally (warm voice worker, no first-call model
  load). No timing measurement of a real spoken answer was taken, and the
  brain round trip itself was not changed.
- Voice recognition still depends on a transcriber: a configured remote key, or
  a local Vosk model that is not installed here.
