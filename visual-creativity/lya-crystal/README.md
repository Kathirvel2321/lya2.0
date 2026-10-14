# LYA crystal concept

Standalone visual concept for a future LYA crystal presence. This folder is intentionally
not imported by the desktop or mobile runtime.

## Files

- `lya-crystal.glb` — lightweight glTF 2.0 binary asset for 3D viewers.
- `lya-crystal.obj` / `lya-crystal.mtl` — simple interchange copy for DCC tools.
- `preview.png` — generated front-view concept render.
- `build_asset.py` — deterministic source generator for the mesh, materials and preview.
- `asset-manifest.json` — generated size/count/checksum record.

## Visual direction

The mesh is a compact, elongated double-terminated crystal rather than a large scene:

- 8-sided low-poly rings create the sharp silhouette and readable facets.
- A smaller inner faceted core creates the dark-blue depth visible through the outer glass.
- Transparent blue/ice materials use glTF transmission and IOR extensions where supported.
- A very small amber material accent echoes the reference image without turning the crystal
  into a glowing ornament.
- No floor, particles, animation, UI, or application hooks are included.

The GLB is a concept-quality, render-ready starting point. Physical refraction and final
lighting depend on the viewer or renderer used later.

## Rebuild

From the project root:

```powershell
python visual-creativity\lya-crystal\build_asset.py
```

This only writes files inside this folder.
