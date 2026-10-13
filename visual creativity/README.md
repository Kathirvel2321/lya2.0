# LYA visual creativity

Isolated design workspace, started 2026-10-13.
Reference: owner-supplied 379f75e0-ecf5-445e-9a7c-f463252a7231.png, viewed inline in the conversation.

## Scope

The owner asked to create this folder, assess the supplied crystal first, and recommend a feasible rendering direction. This first checkpoint is a design brief, not a replacement crystal or a production interface change. Production desktop/mobile artwork, animation, controls, models, voice and authentication remain untouched.

The attachment's advertised local path was unavailable. The visible image was assessed; its original bytes have not been imported, traced, reconstructed or fabricated here.

## Reference assessment

Preserve the tall, double-pointed silhouette, narrow upper/lower tips, broad middle, asymmetric triangular facets, dark sapphire interior, clear icy edges, cyan reflected light and small amber facet on the right. The visible silhouette is approximately 1.9 times taller than wide; confirm exact measurements from the original image before mesh work.

The interesting contrast is a dark core against bright outer planes. The amber detail gives the design a recognizable accent. Keep the outer shape intact before proposing structural alternatives. No plinth, orbiting rings, detached shards, extra crystal pieces or new surrounding effects are part of this reference.

This is more distinctive than a generic circular assistant presence, but faceted crystals are an established visual motif. No worldwide originality or "never used before" claim is made. Its identity should come from a consistent silhouette, facet arrangement, material, accent and restrained behavior.

At the current desktop crystal's 184 by 252 pixel window, tiny face reflections and a mesh of bright facet lines may become visually noisy. Inspect the body at its actual displayed size as well as large reference scale. Large renders are insufficient acceptance evidence.

## Recommended approach

Create one true 3D master with a reproducible mesh/material/light/camera setup. Then compare:

| Runtime | Benefit | Tradeoff |
| --- | --- | --- |
| Static 2D artwork | Closest to one reference view; simplest native integration | Little parallax or changing reflections |
| Baked 3D frames with native interaction | 3D-authored glass appearance and controlled motion; fits the current pixmap renderer | Fixed lighting/view sequence; not physically dynamic refraction |
| Real-time 3D | Arbitrary views and responsive material lighting | Requires a qualified rendering path; glass quality, transparency and resource cost need device measurements |

Recommendation: 3D master plus baked frames as the first runtime candidate. Treat real-time 3D as an optional comparison after profiling, not as automatically better. Current desktop source loads crystal-original.png and experimental obsidian-baked.png through QPixmap and native QPainter; it does not render the GLB interactively. The source uses bounded motion bursts and a low-power/reduced-motion fallback. Preserve those protections and all existing input/state functionality.

Glass appearance depends on material transmission/refraction, roughness, volume and lighting, not polygon count or extra neon glow. Author the visual material in 3D, then preserve its art-directed contrast when baking. A transparent PNG background does not itself provide physical refraction. Runtime glass would refract objects in its rendered scene, not automatically other desktop applications.

The image fixes one view only. Hidden geometry and reflections are underdetermined, so do not promise an exact physical 360-degree object from it. Target a close front-view match and get side/back design approval before finalizing rotations.

## First acceptance gates

1. Import the original reference bytes when accessible; record dimensions and silhouette.
2. Establish a fixed front camera and gray comparison background.
3. Match the outline and visible facet junctions before material/animation polish.
4. Produce matched front-view previews: neutral geometry, glass material, actual-size native-scale image. Label them as previews.
5. Review small-scale readability and user-confirmed similarity. Do not claim an exact match from a distant or decorative render.
6. Only then qualify subtle interaction motion using existing LYA state semantics; geometry stays stable.
7. Compare idle/activity CPU/GPU use, memory, startup, background/hidden stop, click/drag/focus and reduced motion on the actual owner device. Do not invent FPS, battery, resource or performance results.
8. Runtime integration is a separate authorized step after visual acceptance.

Suggested future assets: editable 3D scene, exported mesh, reproducible render settings, front/side/back comparison views, transparent baked frames and their manifest. No such assets have been created at this checkpoint.

## Primary technical references

- Qt Quick 3D PrincipledMaterial: https://doc.qt.io/qt-6/qml-qtquick3d-principledmaterial.html
- Blender Principled BSDF: https://docs.blender.org/manual/en/dev/render/shader_nodes/shader/principled.html

These document candidate material controls, not measured LYA quality or runtime readiness.

## Verification and next step

Checked the current GitHub desktop rendering source at main revision 1d7b5c1c497b7b848ea70f5cac5c25aa9efffda7 and the visible reference. Documentation only; no product tests are required for this reversible brief. No model, shader, renderer, software installation, sensor/provider request, deployment or production file edit performed.

Next: owner reviews the direction, then build an isolated front-view 3D material/geometry prototype in this workspace.
