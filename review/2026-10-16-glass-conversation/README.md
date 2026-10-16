# Native glass conversation and task border

Implemented against main `945eeec364fa743ef56c1ec5276f06d4f581cd44` after the owner approved the conversation/app-border visual and required low battery impact.

## Runtime

- `desktop/glass_style.py`: rounded navy surface, fixed reflective gradients and a restrained hairline. No screenshot capture, live backdrop blur, WebView or live 3D renderer.
- `desktop/experience.py`: existing approved body appears beside answers/chat; optional typing remains available. Voice requests reveal the same panel. Existing transcript bounds, phrase captions, speech engine, startup and circle docking are preserved. Close returns to the existing dock.
- `desktop/task_border.py`: four narrow native input-transparent/no-focus strips and a small readable status tag. `begin(generation, target, label, state)` accepts an explicit `QtTarget` or pinned `WindowsTarget`. Native bounds are verified against HWND/PID and converted from DWM physical pixels using the matching Qt monitor. Unrelated foreground, invisible/minimized/cloaked and destroyed windows are not outlined.
- `brain/workflow.py`/`desktop/app.py`: optional observer reports actual source retrieval and model invocation stages; public/private routing and existing authorization remain authoritative. Research runs through HTTP adapters, so its progress appears around LYA's own panel. It does not surround whichever browser happens to be open.
- `skills/limited_apps.py`: the same permitted commands emit an optional receipt after `Popen` succeeds. Only a window attributable to that PID receives a 0.6-second “App opened” highlight. Calculator/browser process handoffs can prevent attribution; the implementation skips the border rather than guessing. A launch is not continuing work in the app.

The backend currently has no general long-running external app automation executor. The explicit target border is implemented and synthetic-tested; such a worker must supply the exact target and stop the border on every completion/cancellation/error path before claiming live external-app work.

## Resource behavior

The panel is painted only for content/state changes and a small top-edge glint during actual activity. The glint timer is 80 ms (12.5 fps); external border geometry is checked every 250 ms only while its task is active. Launch discovery expires after 1.5 seconds. Four narrow edge surfaces avoid an app-sized translucent render target. Hidden panels and hidden/minimized/other-foreground app targets stop decorative motion; reduced motion is static. Stop/close/quit clear border timers and surfaces. The approved PNG/GLB are unchanged.

This limits unnecessary painting; it is not a measured battery guarantee. Laptop CPU/GPU, battery, physical multi-monitor/DPI, live voice and perceived likeness require owner-device acceptance. The native gradients approximate the concept's glass surface and do not provide physically accurate live refraction.

## Verification

`QT_QPA_PLATFORM=offscreen python desktop/check_glass.py`

Ten local real-Qt checks pass: optional typing and literal transcript text, actual worker progress, real public research stages with a fake provider, observer failure isolation, launch receipt ordering, stale/cancelled events, full desktop request/cancellation, native flag declarations, follow/move/resize/hide/close, deadline cleanup and mixed-DPI/negative-origin geometry. No sensor or provider is opened. The exact binary body could not be fetched by the connector locally; an earlier reference is used as an uncommitted local fixture. Do not treat that local image as the accepted installed body.

`QT_QPA_PLATFORM=windows python desktop/check_glass_windows.py`

Native Windows smoke check uses a synthetic foreground window to verify real DWM bounds, HWND/PID pinning, movement/minimize, no focus stealing and actual Windows input-transparent/no-activate styles. GitHub Actions checks and a preview rendered with the unchanged repository asset are pending at this checkpoint.

The Actions artifact includes `native-preview.png` and `research-panel.png`; the preview is rendered from actual Qt widgets with synthetic content. It is not a screenshot of a running real research task or proof of a pixel-exact concept match. Main, deployed mobile service and owner laptop are not changed by this branch.
