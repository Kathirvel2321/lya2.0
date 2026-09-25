# Owner-introduction visual redesign — 2026-09-21

## Outcome

The first four-corner concept looked like cropped artwork attached to a normal dark
form. This revision keeps the crystal intact and turns four small vector facets into
the stage rail. The result uses one calm surface, a permanent left identity dock,
compact cards, short copy and specific action labels.

The reveal lasts 1.05 seconds, requests at most about 30 paints per second, stops
fully at rest, can be skipped, and is bypassed in reduced-motion mode. The crystal
image is loaded and scaled once. There is no WebGL, live blur, video, looping glow,
particle system or idle timer.

## Research applied

- Microsoft Fluent motion: connected, context-appropriate transitions and brief
  167–333 ms motion units rather than continuous spectacle.
- Microsoft material guidance: avoid stacked acrylic; acrylic is GPU-intensive and
  can increase power consumption. The Qt screen therefore uses an opaque-tinted
  fallback surface rather than live desktop blur.
- Current Web Interface Guidelines: visible focus, reduced motion, concise active
  copy, explicit action labels, labelled inputs, and interruptible animation.

Sources:

- https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/motion
- https://learn.microsoft.com/en-us/windows/apps/design/style/acrylic
- https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md

## Artifacts

- `01-core.png` — centered intact identity core
- `02-connected-reveal.png` — core travels to its dock while vector facets become stages
- `03-identity.png` — display-name stage
- `04-device.png` — Windows verification stage
- `05-signals.png` — face/voice preference stage
- `06-review.png` — explicit ready/pending/locked review
- `render_preview.py` — synthetic offscreen renderer; opens no sensor or verifier

## Checks

- `test_registration_ui.py`: 15 passed
- `test_registration.py`: 12 passed
- `desktop/check_experience.py`: 13 passed
- Total: 40 passed

These are isolated UI/core checks and synthetic screenshots. Interactive Windows
verification and real owner enrollment remain untested and incomplete.
