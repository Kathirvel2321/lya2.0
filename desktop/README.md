# LYA crystal desktop milestone

The user's custom black-chrome crystal is now a small native Windows widget, with
an attached translucent result panel. This is the first implementation of the new
desktop presentation layer. It does not import the legacy runtime.

## Start it

Double-click `launch-lya.cmd`, or run this from the project root in PowerShell.
It opens the panel and works without changing PowerShell's execution policy:

```powershell
.\launch-lya.cmd
```

The existing PowerShell launcher is also available if scripts are permitted:

```powershell
.\launch-lya.ps1
```

Or run directly to see any startup errors:

```powershell
.\.venv-ui\Scripts\python.exe desktop\app.py
```

Optional: `--show-panel` opens the card at launch; `--reduced-motion` disables the
crystal's gentle movement and color-transition animations. The PowerShell launcher
accepts `-ShowPanel` and `-ReduceMotion` and uses `pythonw.exe` to avoid a console.

The `.cmd` launcher always opens the panel; use `--reduced-motion` with it to
disable animations. It starts the installed Python executable directly, never
changes execution policy, and does not enable microphone/camera collection.

The isolated environment is already installed on this workspace with Python
3.12.14 and PySide6 Essentials 6.11.2. To create a new environment on another
machine with Python 3.12 installed:

```powershell
py -3.12 -m venv .venv-ui
.\.venv-ui\Scripts\python.exe -m pip install -r desktop\requirements.txt
```

## Use it

- Click the crystal or press Enter/Space while it has focus to open the panel.
- Drag the crystal. The result panel follows and stays inside the current monitor's
  available work area, avoiding the taskbar. It opens to the left or right when
  possible and shifts upward in tight spaces.
- Type `show files`, or click Project files. These are actual saved LYA project
  documents, not a connected private vault. Double-click a row or press Enter to
  read it. Nothing is executed, edited or uploaded.
- `time` shows the local time. `help` lists the implemented commands.
- Right-click the crystal or use the tray menu to preview colors and change motion
  or opacity. Cosmetic person choices do not identify anyone or grant permissions.
- Escape/`stop` closes the card and rejects stale read results. Ctrl+M toggles
  reduced motion. Ctrl+Q quits. The tray menu can also wake, sleep, recenter or quit.

Person palettes: guest ice, admin amber, family violet, friend jade. Task accents
take priority: listening cyan, thinking violet, files blue, success green,
approval amber, error rose. `task idle` returns to the selected person palette.
The crystal keeps its original cyan/amber fissures with a restrained color wash
and changing aura, rather than replacing the user's artwork with a generic circle.

## Design and implementation

- Two compact native Qt windows; no browser, web server, full-screen overlay or
  background desktop screenshot sampling.
- Original artwork copied unchanged to `assets/crystal-original.png`. A native
  painter clip follows its silhouette; the original gray background is not shown.
  This is a 2D artwork animation, not a reconstructed rotatable 3D model.
- Cached tinted pixmaps, 420ms color interpolation and a low-amplitude timed drift.
  Idle repaint target is 30Hz; Qt drives color transitions separately. Rendering
  stops continuously repainting when the orb is hidden or reduced motion is enabled.
- Card opens with a 260ms movement from the crystal's direction and a 210ms fade.
  Only geometry/opacity animate; document contents do not reflow during the reveal.
- Dark translucent glass, opaque text, subtle shadow, inner highlight and outline
  provide contrast against light or dark wallpapers. An opaque option is available.
  This is a tinted glass treatment, not OS-level acrylic/background blur.
- Document reading runs in a single worker. A generation id prevents completion
  callbacks from reopening a dismissed result. Reads are allowlisted to four
  project documents and limited to 64,000 characters; links never open externally.

Qt references used: [translucent QWidget windows](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html)
and [property animations](https://doc.qt.io/qt-6/qpropertyanimation.html).

## Check it

```powershell
.\.venv-ui\Scripts\python.exe -B desktop\check_ui.py
```

The checks exercise alpha/native-window setup, monitor bounds (including negative
coordinates), keyboard use, cosmetic-role isolation, read allowlisting, stale-result
cancellation and animation lifecycle. They render actual widgets over synthetic
light and dark backgrounds in `qa/` and save a short timing sample in
`qa/measurement.json`. Screenshots are UI test fixtures, not captures of the user's
desktop. Short paint timings are not guarantees of frame rate, battery use or
long-duration stability under model/camera workloads.

## Brain workflow milestone (2026-09-13)

Type `brain demo` for a labelled synthetic demonstration, `brain status` for
readiness, `brain help` for memory commands, or `who am i` for session identity.
Requests run on a background worker; closing the panel suppresses late results.
See [the brain guide](../LYA_BRAIN_WORKFLOW.md) for lifetimes, graph and council.

The real desktop session stays a guest: identity and phone approval are not yet
bound to this workflow. Personal memory operations therefore remain locked.
General model responses require a selected, reachable local model; none was
reachable during this check. Cosmetic role selection never grants access.

Voice has an optional bridge with readiness/error indicators. The desktop requires
a local Vosk model before recording, with no transcription cloud fallback. That
model is missing in the checked environment; live wake/recognition is unverified.
The separate legacy voice module also contains online speech services, which are
not evidence that offline voice works. No sensor or online speech test was run
in the isolated brain acceptance pack.

## Artwork attempt provenance

The original is the owner's `ChatGPT Image Sep 12, 2026, 06_46_46 PM.png`. A built-in
ImageGen background-extraction attempt produced a baked checkerboard rather than
alpha, so that generated output is not used by the app. No replacement raster or
CLI image API was installed. The original source is displayed through the native
silhouette clip instead.

Prompt used: “Use case: background-extraction. Edit target: the attached user's
custom LYA crystal. Create a production desktop sprite by removing ONLY the flat
gray background. Preserve the original single floating jagged black chrome crystal,
exact tall diamond silhouette, facets, glass reflections, and cyan and amber
illuminated fissures. Do not redesign it, do not add rings or text. Genuine
transparent alpha background (not a checkerboard painted into image), clean finely
antialiased edges, no backdrop, no cast shadow beyond the crystal, no floor. Center
the full uncut crystal with a little transparent padding. Return PNG with
transparency. This image will be a small floating native desktop assistant.”
