# LYA visual creativity — prototype and native adapter

2026-10-13. Prototype based on GitHub main 1d7b5c1c497b7b848ea70f5cac5c25aa9efffda7. The offline preview remains isolated. A native reference-artwork adapter is now implemented in the same draft branch; see **INTEGRATION.md** for live state mapping, checks and rollback. Not merged or deployed. Three native Qt widget checks passed on the owner laptop in the separate worktree; full app acceptance and exact 3D reference likeness remain pending.

## What is built

- **preview.html:** offline interactive preview. Open directly in a browser; no web server, network or dependencies. The default Rendered glass study displays eight Blender Cycles views of the actual model. The derived transparent PNG reference and diagnostic geometry view remain selectable; surrounding effects are drawn separately. Select interaction/task, background and simulated voice level. Body appearance is unchanged across states.
- **effects.js + states.json:** deterministic effect geometry, palette, precedence and state rules. Voice/task colours are independently described. Selecting a task previews its signature at idle; select an interaction afterward to see combined behaviour. Attention states override activity; paused/offline/voice-off suppress task animation. Actual backend blocked requests retain amber approval treatment; errors use rose. This corrects the earlier combined blocked/error concept image's ambiguous rose proposal.
- **model/lya-body-candidate.glb:** real editable 3D geometry, seven closed outward-wound components, 2,344 triangles. Contains PBR transmission, volume, IOR and emissive materials. Candidate only: silhouette, side/back geometry, topology intersections, optical glass and glow are not artist-approved.
- **model/body-spec.json + build_model.py:** editable source geometry and deterministic GLB exporter using Python standard library. No state-driven body deformation.
- **model/create_scene.py:** Blender 4.5 authoring/render entry. Checksum-verified portable Blender produced the editable [glass study scene](model/rendered-glass/lya-glass-study.blend), [front render](model/rendered-glass/glass-front.png) and eight transparent turntable views. Materials use blue volume absorption, transmission and IOR, a darker sapphire spine, polished edges and an emissive core. The scene has studio lights and uses CPU Cycles; this is offline design rendering.
- **assets:** original approved four-pose reference and a new transparent raster anchor derived from its top-right Listening pose. The anchor is an ImageGen derivative, not a pixel-exact extraction or a Blender render. Review its likeness before acceptance.

## Try it

Open **preview.html**. It includes all data and artwork. Rendered glass study is the default. Turn effects off to inspect the body, drag Model rotation or enable Turntable. Eight baked angles are spaced 45 degrees apart; lighting and refraction do not recalculate with the page background. Reference artwork provides the approved visual comparison. Diagnostic geometry rotation retains simple software shading. Exact reference likeness is not yet approved. See [refinement evidence and limits](../review/2026-10-13-glass-refinement/README.md).

Voice level is a slider simulation, not microphone input. The controls grant no identity, authority, actions, files, memory or access to the live LYA service. No automatic production installation/deployment.

Rebuild assets from this folder:

```sh
python model/build_model.py
blender --background --factory-startup --python model/create_scene.py -- --turnaround --transparent
python build_preview.py
node tests/check_effects.js
node tests/check_preview.js
python tests/check_model.py
```

If Blender 4+ is available locally, create the authoring scene:

```sh
blender --background --python model/create_scene.py
```

Add `-- --render` for a front PNG, or `-- --turnaround` for eight consistent views. Writes to model/rendered/, preserves the approved raster/reference. No dependency installation is performed by these scripts. Rendering settings are provisional and require visual comparison; do not infer fidelity from the GLB's small file size.

## Reference and palette contract

Approved body: top-right Listening pose of the accepted glass-creature sheet. Freeze the crest, dark spine, large left mantle, small right fin and bright white-cyan core. States change external curves/waves/highlights only. The earlier AI turnaround does not define consistent exact hidden geometry; reconcile proposed views against this candidate during modelling.

Existing values copied from desktop/layout.py and desktop/app.py at the base revision: listening/hearing cyan #68e5f2, thinking violet #b69bff, speaking mint #78e1bf, files blue #6dceff, approval/blocked amber #ffc26b, success #77e0b2, error/uncertain rose #ff879b. New task treatments are labelled proposals in states.json. Role colours are not copied into this preview as authentication.

## Verification

- 1,008 deterministic effect frames across all interaction/task combinations, times and reduced-motion modes pass. Every frame preserves the same body asset, pose, scale, rotation and no tint. Unknown states/nonfinite values rejected. No authority grants.
- 13 synthetic DOM/canvas scheduling scenarios pass: device-pixel-ratio cap, dynamic versus static frames, fixed body dimensions, task/voice combinations, reduced motion, hidden-page stop/resume, attention priority, actual geometry rotation, reset and pagehide/pageshow.
- Five mesh components pass closed-edge count, opposite directed edges, Euler and positive signed-volume checks; nondegenerate finite triangles, GLB lengths/alignment/accessors/materials and deterministic regeneration pass. These are structural checks, not self-intersection, surface-quality or optical validation.
- Python sources parse; JavaScript executes in isolated Node VM. RGBA asset has alpha range 0–255. Self-contained bundle contains no unresolved placeholders, external assets, fetch, microphone, storage or service worker; restrictive CSP disables connections.
- No real browser visual/interaction check: Playwright exists but its Chromium executable is absent. No native Qt runtime or Blender is available. No software download, production test, sensor, live provider or private-data use occurred.

Evidence: tests/effects-validation.json, tests/preview-validation.json, tests/model-validation.json; model/geometry-stats.json.

## Resource design and limits

Active drawing capped at 30 frames/s, canvas pixel ratio capped at 2. Static idle/attention/paused/voice-off/offline and reduced-motion frames do not maintain a drawing loop; hidden/pagehide stop it. This is a bounded rendering design, not a measured CPU/GPU/battery claim. The anchor has original detail; it is not downscaled on disk to claim savings. Alpha-composited artwork does not physically refract desktop content. The mesh preview is a candidate, not a finished glass renderer.

## Next acceptance step

Inspect reference-mode likeness at actual widget size and on navy/grey. Then render the editable 3D candidate in Blender and compare silhouette, broad planes, crest, core/glow and mantle against the approved reference. Refine geometry and lights until the owner accepts the match. The native adapter now displays the reference artwork with preserved input/voice/approval hooks; real Qt acceptance remains pending. After owner acceptance of the finished 3D match, bake final rotation frames and qualify them separately. See INTEGRATION.md for the current native checks and device acceptance steps.

Primary format references: https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_materials_transmission and KHR_materials_volume; https://docs.blender.org/manual/en/5.3/addons/scene_gltf2.html. Documentation describes material interchange, not qualified LYA runtime compatibility.
