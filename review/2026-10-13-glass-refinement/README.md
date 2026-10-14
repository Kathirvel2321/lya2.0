# LYA detailed glass study - 2026-10-13

Owner asked to refine the actual 3D model to the design prototype's glass appearance and color shading. Work stays in the separate PR #3 worktree at base commit `6ba5694717df64299ecdf5fc81e370ad8fcdc76e`; no main checkout edits, commits, pushes, merge or deployment.

## Changes

- `visual creativity/model/body-spec.json` and `build_model.py`: seven closed parts, 2,344 triangles and 1,186 shared geometric vertices. Curved/twisted sapphire spine, two internal folds, nested faceted glass panels, blue absorption/IOR/transmission materials, bright fixed core. Geometry remains fixed across interaction/task states.
- `model/create_scene.py`: actual CPU Cycles rendering, transparent turntable outputs, polished edge bevels and studio reflection lights. Editable [Blender scene](../../visual%20creativity/model/rendered-glass/lya-glass-study.blend), [768x1024 front](../../visual%20creativity/model/rendered-glass/glass-front.png) and eight 512x640 views at 45-degree increments. The Blender scene adds small bevels and coat lighting treatment beyond the portable GLB materials.
- Offline [preview.html](../../visual%20creativity/preview.html) defaults to Rendered glass study. It uses the eight physically rendered model views. Reference artwork and diagnostic geometry rotation remain selectable. Glass view angle selection and pause/reduced/hidden scheduling are checked; existing voice/task effects are unchanged.
- Original generator/model/preview artifacts are preserved under [before/](before/). Early clear/blue drafts and the first large front render are retained here for comparison.

## Renderer and environment

Portable Blender 4.5.3 LTS downloaded only from the official vendor, SHA256 `6b657c8bdd3a7b65b07b9e1ae17eb4be7dd4aa23121da7f3d3354fc2551330a7`, verified against the vendor checksum file. URLs: https://download.blender.org/release/Blender4.5/blender-4.5.3-windows-x64.zip and https://download.blender.org/release/Blender4.5/blender-4.5.3.sha256 . Extracted beside the worktree in `../tools/blender-4.5.3-windows-x64/` relative to the worktree root. No system installation, PATH, startup or `.venv-asr` package change. Reused existing Python 3.12.14/Node for source builds and checks.

## Checks and limits

See [model-check.txt](model-check.txt), [effects-check.txt](effects-check.txt), [preview-check.txt](preview-check.txt), [source preservation](source-preservation.json), and final render logs. Geometry checks cover finite/nondegenerate triangles, two-manifold edges, winding, positive volume, Euler topology, GLB bounds/materials and deterministic rebuilding. They do not certify non-intersection between independent components or exact reference likeness. The model-only test does not execute Blender; render evidence is recorded separately.

1,008 effect frames and 15 synthetic preview scenarios pass. Native desktop, voice/hearing, authentication, providers, storage, startup, mobile, original artwork and state/effect data are unchanged in this worktree. Main branch/HEAD/index match their original baseline. A separate ongoing task changed main memory/docs files during this session; those changes were not overwritten or attributed to this task.

Preparation/repair notes: sandbox network DNS denied the first vendor checksum request; authorized vendor retrieval/download succeeded. The first geometry check used an inaccessible sandbox temp folder; rerun with a workspace temp directory passes. A Blender legacy glare-property warning was fixed using its current socket inputs; final renders are checked separately. Initial direct source-byte comparison differed because Git checked text out as CRLF; newline-normalized source checks and byte-identical PNG checks pass. Browser automation rejected the existing local `file:` page; no alternate browser surface/server was used to bypass that restriction. Saved rendered PNGs are inspected directly. Synthetic preview checks are not full browser visual QA.

This is a revised real-glass design study, not an exact approved replica. Front silhouette/facet correspondence still differs from the approved 2D reference, and unseen side/back shapes are authored interpretations. Eight-angle previews have baked studio lighting and stepped rotation; page background changes do not recalculate refraction. Live rendering/battery use and full app acceptance remain untested. Next: owner reviews the rendered likeness and color/facet direction before any native artwork replacement or integration.

Final executed result: both Blender jobs exit 0. Eight 512x640 RGBA angle renders at 64 samples and the 768x1024 front at 96 samples validate; final front render took 1m39.22s. Final logs contain no traceback or legacy glare-property warning. [Render validation and hashes](render-validation.json) and [source/static checks](static-validation.json) record the final artifacts. Offline preview bundles to 3,858,587 bytes and its 15 scenarios pass after the final frame regeneration. PNG inspection is not approval of exact likeness.
