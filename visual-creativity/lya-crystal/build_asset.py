"""Build the standalone LYA crystal concept asset.

This is an offline artwork generator, not application/runtime code. It emits a small
flat-faceted GLB, an OBJ interchange copy, and a deliberately simple preview render.
The geometry is kept procedural so the concept can be tuned after owner review without
introducing a large DCC project file or external dependency.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
SIDES = 8

# Material tuples: name, RGBA base color, metallic, roughness, transmission, emission.
MATERIALS = [
    ("OuterIce", (0.52, 0.86, 1.00, 0.48), 0.08, 0.10, 0.72, (0.015, 0.055, 0.08)),
    ("OuterHighlight", (0.88, 0.97, 1.00, 0.62), 0.05, 0.07, 0.68, (0.03, 0.08, 0.11)),
    ("OuterBlue", (0.08, 0.40, 0.70, 0.44), 0.12, 0.13, 0.66, (0.005, 0.035, 0.08)),
    ("OuterDeep", (0.015, 0.10, 0.18, 0.60), 0.20, 0.12, 0.45, (0.0, 0.012, 0.03)),
    ("OuterAqua", (0.12, 0.66, 0.88, 0.50), 0.10, 0.10, 0.70, (0.01, 0.09, 0.13)),
    ("WarmFacet", (1.00, 0.65, 0.18, 0.72), 0.10, 0.11, 0.40, (0.16, 0.045, 0.008)),
    ("EdgeLight", (0.92, 0.99, 1.00, 0.70), 0.04, 0.06, 0.74, (0.04, 0.10, 0.14)),
    ("CoreDeep", (0.012, 0.08, 0.14, 0.74), 0.15, 0.16, 0.36, (0.0, 0.01, 0.025)),
    ("CoreBlue", (0.03, 0.25, 0.48, 0.68), 0.10, 0.14, 0.52, (0.0, 0.035, 0.07)),
    ("CoreCyan", (0.08, 0.54, 0.76, 0.60), 0.08, 0.12, 0.60, (0.0, 0.07, 0.10)),
    ("CoreShadow", (0.005, 0.035, 0.07, 0.78), 0.22, 0.18, 0.24, (0.0, 0.005, 0.012)),
]


def ring_vertices(z: float, radius: float, depth: float, phase: float, scale: float = 1.0):
    """Return a slightly irregular 8-sided ring in x/y/z coordinates."""
    values = []
    for i in range(SIDES):
        angle = phase + (2.0 * math.pi * i / SIDES)
        wobble = 1.0 + 0.045 * math.sin(i * 2.7 + z * 1.9)
        values.append((
            radius * scale * wobble * math.cos(angle),
            depth * scale * wobble * math.sin(angle),
            z * scale,
        ))
    return values


def make_faces(inner: bool = False):
    """Create triangle faces with a material id for each flat facet."""
    scale = 0.82 if inner else 1.0
    phase = 0.18 if inner else 0.0
    rings = [
        ring_vertices(1.16, 0.56, 0.42, phase + 0.08, scale),
        ring_vertices(0.30, 0.77, 0.54, phase - 0.03, scale),
        ring_vertices(-0.34, 0.75, 0.53, phase + 0.06, scale),
        ring_vertices(-1.10, 0.47, 0.35, phase - 0.08, scale),
    ]
    top = (0.0, 0.0, 2.02 * scale)
    bottom = (0.0, 0.0, -2.02 * scale)
    faces = []

    # Each entry is (triangle points, material id, layer name).
    for i in range(SIDES):
        j = (i + 1) % SIDES
        mat = 7 + (i % 4) if inner else [1, 0, 2, 3, 0, 4, 1, 2][i]
        faces.append(([top, rings[0][i], rings[0][j]], mat, "core" if inner else "outer"))
        faces.append(([rings[-1][i], bottom, rings[-1][j]], mat, "core" if inner else "outer"))

    for band in range(len(rings) - 1):
        for i in range(SIDES):
            j = (i + 1) % SIDES
            a, b = rings[band][i], rings[band][j]
            c, d = rings[band + 1][i], rings[band + 1][j]
            if (i + band) % 2:
                triangles = [(a, b, c), (b, d, c)]
            else:
                triangles = [(a, b, d), (a, d, c)]
            for part, triangle in enumerate(triangles):
                if inner:
                    mat = [7, 8, 9, 10][(i * 3 + band + part) % 4]
                else:
                    # Sparse warm facets on the right-facing midsection, not a gold object.
                    if band == 1 and i == 1 and part == 1:
                        mat = 5
                    elif band == 1 and i == 2 and part == 0:
                        mat = 6
                    else:
                        mat = [0, 2, 3, 1, 4, 0, 2, 6][(i * 2 + band + part) % 8]
                faces.append((list(triangle), mat, "core" if inner else "outer"))
    return faces


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(value):
    length = math.sqrt(sum(part * part for part in value)) or 1.0
    return tuple(part / length for part in value)


def face_normal(points):
    return normalize(cross(vec_sub(points[1], points[0]), vec_sub(points[2], points[0])))


def make_triangle_groups():
    groups = defaultdict(list)
    all_faces = make_faces(inner=True) + make_faces(inner=False)
    for points, material, layer in all_faces:
        groups[(layer, material)].append((points, face_normal(points)))
    return groups, all_faces


def pad4(data: bytes, fill: bytes = b"\x00") -> bytes:
    return data + fill * ((4 - len(data) % 4) % 4)


def build_glb(path: Path, groups):
    """Write a self-contained glTF 2.0 binary with flat-shaded triangle primitives."""
    binary = bytearray()
    buffer_views = []
    accessors = []

    def append_attribute(values, accessor_type, min_values, max_values):
        offset = len(binary)
        packed = struct.pack("<" + "f" * len(values), *values)
        binary.extend(packed)
        binary.extend(b"\x00" * ((4 - len(binary) % 4) % 4))
        view_index = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(packed)})
        accessor_index = len(accessors)
        accessors.append({
            "bufferView": view_index,
            "componentType": 5126,
            "count": len(values) // 3,
            "type": accessor_type,
            "min": list(min_values),
            "max": list(max_values),
        })
        return accessor_index

    primitives = []
    for (layer, material), triangles in sorted(groups.items()):
        positions = [coord for points, _normal in triangles for point in points for coord in point]
        normals = [coord for _points, normal in triangles for _point in _points for coord in normal]
        xyz = list(zip(*[iter(positions)] * 3))
        nxyz = list(zip(*[iter(normals)] * 3))
        pos_accessor = append_attribute(positions, "VEC3", [min(v[i] for v in xyz) for i in range(3)], [max(v[i] for v in xyz) for i in range(3)])
        norm_accessor = append_attribute(normals, "VEC3", [min(v[i] for v in nxyz) for i in range(3)], [max(v[i] for v in nxyz) for i in range(3)])
        primitives.append({
            "attributes": {"POSITION": pos_accessor, "NORMAL": norm_accessor},
            "material": material,
            "mode": 4,
            "extras": {"layer": layer, "flatFacets": len(triangles)},
        })

    materials = []
    for name, color, metallic, roughness, transmission, emission in MATERIALS:
        materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(color),
                "metallicFactor": metallic,
                "roughnessFactor": roughness,
            },
            "emissiveFactor": list(emission),
            "alphaMode": "BLEND",
            "doubleSided": True,
            "extensions": {
                "KHR_materials_transmission": {"transmissionFactor": transmission},
                "KHR_materials_ior": {"ior": 1.45},
            },
        })

    document = {
        "asset": {"version": "2.0", "generator": "LYA standalone crystal concept builder"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "LYA Crystal", "mesh": 0}],
        "meshes": [{"name": "LYA Crystal Facets", "primitives": primitives}],
        "materials": materials,
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "extensionsUsed": ["KHR_materials_transmission", "KHR_materials_ior"],
        "extras": {
            "concept": "transparent blue faceted LYA crystal",
            "triangleCount": sum(len(value) for value in groups.values()),
            "runtimeIntegration": False,
        },
    }
    json_chunk = pad4(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = pad4(bytes(binary))
    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    glb = bytearray(struct.pack("<4sII", b"glTF", 2, total_length))
    glb.extend(struct.pack("<II", len(json_chunk), 0x4E4F534A))
    glb.extend(json_chunk)
    glb.extend(struct.pack("<II", len(bin_chunk), 0x004E4942))
    glb.extend(bin_chunk)
    path.write_bytes(glb)
    return document


def write_obj(path: Path, groups):
    lines = ["# LYA crystal concept — flat-faceted standalone mesh", "mtllib lya-crystal.mtl", "o LYA_Crystal"]
    vertex_index = 1
    for (layer, material), triangles in sorted(groups.items()):
        lines.append(f"usemtl {MATERIALS[material][0]}")
        for points, normal in triangles:
            start = vertex_index
            for point in points:
                lines.append(f"v {point[0]:.6f} {point[1]:.6f} {point[2]:.6f}")
            lines.extend([f"vn {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}"] * 3)
            lines.append("f " + " ".join(f"{index}//{vertex_index + offset}" for offset, index in enumerate(range(start, start + 3))))
            vertex_index += 3
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    mtl = ["# LYA crystal concept materials"]
    for name, color, metallic, roughness, transmission, _emission in MATERIALS:
        mtl.extend([
            f"newmtl {name}",
            f"Kd {color[0]:.4f} {color[1]:.4f} {color[2]:.4f}",
            f"d {color[3]:.4f}",
            f"Ns {max(8, int((1.0 - roughness) * 900))}",
            f"Pm {metallic:.4f}",
            f"Pr {roughness:.4f}",
            "illum 4",
            "",
        ])
    (path.parent / "lya-crystal.mtl").write_text("\n".join(mtl), encoding="utf-8")


def project(point, width, height):
    x, y, z = point
    camera = 7.5
    factor = camera / (camera + y)
    return (width * 0.5 + x * 148 * factor, height * 0.5 - z * 164 * factor)


def preview(path: Path, all_faces):
    width, height = 480, 720
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            dx = (x - width * 0.53) / width
            dy = (y - height * 0.48) / height
            glow = max(0.0, 1.0 - math.sqrt(dx * dx + dy * dy) * 2.1)
            pixels[x, y] = (int(18 + 28 * glow), int(27 + 47 * glow), int(38 + 64 * glow))

    halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    halo_draw.ellipse((118, 70, 380, 650), fill=(50, 153, 217, 34))
    halo = halo.filter(ImageFilter.GaussianBlur(48))
    image = Image.alpha_composite(image.convert("RGBA"), halo)

    palette = [
        (126, 216, 251), (218, 244, 255), (35, 126, 194), (10, 42, 68),
        (57, 193, 227), (255, 184, 66), (229, 250, 255), (8, 39, 65),
        (20, 91, 158), (46, 178, 219), (5, 20, 39),
    ]
    light = normalize((-0.45, -0.80, 0.95))
    # Render the inner volume first, then transparent outer facets back-to-front.
    for layer in ("core", "outer"):
        layer_faces = [face for face in all_faces if face[2] == layer]
        layer_faces.sort(key=lambda face: sum(point[1] for point in face[0]) / 3, reverse=True)
        for points, material, _layer in layer_faces:
            normal = face_normal(points)
            brightness = 0.48 + max(0.0, sum(a * b for a, b in zip(normal, light))) * 0.92
            base = palette[material]
            color = tuple(min(255, int(channel * brightness)) for channel in base)
            alpha = int((base[0] * 0.10 + base[1] * 0.20 + base[2] * 0.08 + 18) if layer == "outer" else 92)
            if material == 5:
                alpha = 168
            projected = [project(point, width, height) for point in points]
            # Draw on a temporary layer so alpha is composited as glass instead of
            # replacing the preview's background pixels.
            face_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ImageDraw.Draw(face_layer).polygon(projected, fill=(*color, alpha))
            image = Image.alpha_composite(image, face_layer)

    edges = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edges)
    for points, material, layer in all_faces:
        projected = [project(point, width, height) for point in points]
        if layer == "outer":
            edge_color = (205, 242, 255, 38 if material != 5 else 132)
            edge_draw.line(projected + [projected[0]], fill=edge_color, width=1, joint="curve")
    image = Image.alpha_composite(image, edges)

    # A small amount of cool bloom keeps the transparent silhouette legible without adding UI.
    bloom = edges.filter(ImageFilter.GaussianBlur(5))
    bloom.putalpha(bloom.getchannel("A" ).point(lambda value: value // 5))
    image = Image.alpha_composite(image, bloom)
    image.convert("RGB").save(path, quality=94)


def main():
    groups, all_faces = make_triangle_groups()
    glb_path = ROOT / "lya-crystal.glb"
    obj_path = ROOT / "lya-crystal.obj"
    build_glb(glb_path, groups)
    write_obj(obj_path, groups)
    preview(ROOT / "preview.png", all_faces)
    manifest = {
        "asset": "LYA crystal concept",
        "runtimeIntegration": False,
        "geometry": {
            "triangles": len(all_faces),
            "materials": len(MATERIALS),
            "layers": {layer: sum(1 for _points, _material, item_layer in all_faces if item_layer == layer) for layer in ("core", "outer")},
        },
        "files": {},
        "checks": {
            "glbHeader": glb_path.read_bytes()[:4] == b"glTF",
            "previewSize": list(Image.open(ROOT / "preview.png").size),
            "transmissionMaterials": sum(1 for item in MATERIALS if item[4] > 0),
        },
    }
    for name in ("lya-crystal.glb", "lya-crystal.obj", "lya-crystal.mtl", "preview.png"):
        data = (ROOT / name).read_bytes()
        manifest["files"][name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    (ROOT / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
