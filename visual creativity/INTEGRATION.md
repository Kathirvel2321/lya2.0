# Native LYA body integration — 2026-10-13

Implemented on the existing visual-prototype branch, not merged or deployed.
Normal desktop launch selects the approved fixed body. The native adapter draws
the existing transparent body anchor with separate front/back effects. It does
not render the unfinished GLB or replace the body with a circle when docking.
The docked footprint is 96 × 112 logical pixels; legacy artwork remains 64 × 64.

`desktop/body_style.py` produces the same normalized effect commands as
`effects.js`. `desktop/living_body.py` inherits existing Crystal input handlers.
`desktop/app.py` selects it, adds optional preview/rollback menu entries, and
attaches request accents to existing worker events. `desktop/experience.py`
adjusts docking dimensions and resumes effects only when the resolved state is
active. Main artwork, asset location and state configuration stay in this folder.

## Live presentation mapping

| Existing event | Appearance |
| --- | --- |
| Voice standby/off | Quiet cyan/grey, static |
| Listening/hearing | Cyan orbit/ticks; existing listener level only |
| Thinking/transcribing | Violet crossing paths |
| Speaking | Mint waves, visual cadence rather than a measured TTS envelope |
| Uncertain words | Static rose broken arcs |
| Requested coding/building/learning/research/files/helping work | Outer task accent during the pending request; body untinted |
| Backend blocked/approval | Static amber boundary, priority over speech |
| Backend error | Static rose broken arcs, priority over speech |
| Cancelled/completed request | Clear request accent; suppress the finished thought effect until a new voice event |

Text hints are cosmetic whole-word matches. They neither alter the request sent
to Brain nor select a route, identify a person, declare safety, authorize an
action or prove tool execution. Private/security/high-risk/reconnecting/offline
concepts are available as **visual previews**, not new automatically detected
runtime states. Role palettes still affect the existing panel, not the body.
Preview selection never changes the real voice phase; the next live state clears
the preview. Existing backend approval, privacy and authentication remain intact.

## Resource behavior and rollback

One sprite cache at the current widget size; no per-state tint copies. Cached
sprite DPR is capped at 2. Effects use bounded path commands and lightweight soft
edge strokes, not physical blur/refraction. Active drawing uses a 34 ms timer and
an additional 30 fps guard. Hidden, reduced-motion and static states stop that
timer. Paints averaging above 8 ms over 30 samples select static reduced motion
while preserving the same body. These limits are implemented; device CPU/battery
and perceived glow have not been measured here.

Missing/invalid artwork or configuration falls back to the existing crystal.
Use the right-click **Use approved LYA body** setting to switch back, or launch
with `--original-art` for the earlier crystal and `--model-art` for the legacy
experimental baked artwork. Voice launch flags, camera/owner setup, model
providers, storage, startup scheduling and policy are unchanged. Mobile page and
Oracle deployment are unchanged by this integration.

## Verification and remaining acceptance

Executed: `python desktop/check_body.py` passes 11 headless tests including 1,008
Python/JavaScript effect-frame comparisons, actual new adapter methods with fake
Qt, frame scheduling, layered drawing calls, cache invariance, missing assets,
legacy rollback, existing level-reader usage, and AST-extracted application
request/busy/cancel/stale-response/blocked/error/private-reply lifecycle behavior.
No private stores, hardware, inference or provider requests were used. Source
comparison confirms 126 existing definitions are unchanged across app/experience,
including input handlers and voice, camera, identity and visitor flows. This is
preservation evidence, not full behavioral qualification. Python syntax passes.

`desktop/check_body_qt.py` provides three real Qt acceptance tests for widget
painting, click/keyboard activation, artwork rollback, live timer and hidden
stop. Attempting it here stops at `ModuleNotFoundError: PySide6`; it has **not
passed**. Run it in the owner's installed PySide6 environment before merging.
Then check the running widget against the approved body at intro/docked size,
on light and dark backgrounds, and exercise actual click/drag/voice/typing,
approval/cancellation and resource behavior. No native screenshot or real device
success is claimed. Earlier browser/model structural checks remain separate.

This implementation displays derived raster artwork. Exact reference likeness,
finished all-side 3D glass/refraction and accepted rotation frames remain pending.
The editable mesh stays a candidate; no new state changes its geometry.
