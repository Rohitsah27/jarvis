"""
Builds assets/models/jarvis_face.glb — a real triangulated 3D mesh (positions,
normals, indices) generated from the SAME procedural head+neck+shoulders
geometry used by the original QPainter-based holographic face
(ui.components.ai_core._generate_face_point_cloud), so the 3D bust matches
the silhouette/proportions already tuned there.

This is a hand-written, dependency-free glTF 2.0 binary (.glb) exporter:
just stdlib `json`/`struct`, no pygltflib/trimesh. glTF is simply a JSON
scene description plus a flat binary buffer of vertex data, so no library
is actually required to emit a valid, spec-compliant file.

Run standalone:
    python tools/build_face_glb.py
"""
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "models" / "jarvis_face.glb"


def _face_width_profile(pn: float) -> float:
    """Same taper curve as ui.components.ai_core._face_width_profile."""
    if pn < 0.32:
        return 0.68 + 0.32 * (pn / 0.32)
    elif pn < 0.62:
        return 1.0
    else:
        t = (pn - 0.62) / 0.38
        return 1.0 - 0.62 * t


def _generate_face_mesh_rows(n_theta: int, n_phi: int):
    """
    Same head+neck+shoulders bump geometry as
    ui.components.ai_core._generate_face_point_cloud, WITHOUT the per-point
    random jitter that function bakes in. That jitter is deliberate there —
    it keeps a sparse hand-drawn point cloud from looking like a rigid grid
    — but for a continuous shaded mesh at any real density it's actively
    harmful: each point's normal is derived from its neighbors' positions,
    so independent per-point noise of a fixed magnitude turns into visible
    surface graininess once the grid spacing shrinks below that magnitude
    (exactly what a denser real-time mesh needs, unlike the sparse CPU-drawn
    dots). Kept as a separate function rather than adding a toggle to the
    tested, tuned 2D version.
    """
    rows = []
    phi_min, phi_max = math.pi * 0.08, math.pi * 0.94

    for j in range(n_phi):
        phi = phi_min + (phi_max - phi_min) * (j / (n_phi - 1))
        pn = (phi - phi_min) / (phi_max - phi_min)
        row = []
        for i in range(n_theta):
            theta = -math.pi / 2 + math.pi * (i / (n_theta - 1))
            tn = theta / (math.pi / 2)

            bump = 0.0
            for ex in (-0.36, 0.36):
                d2 = ((tn - ex) / 0.115) ** 2 + ((pn - 0.40) / 0.075) ** 2
                bump -= 0.38 * math.exp(-d2)
            d2 = (tn / 0.07) ** 2 + ((pn - 0.52) / 0.18) ** 2
            bump += 0.32 * math.exp(-d2)
            d2 = (tn / 0.05) ** 2 + ((pn - 0.63) / 0.045) ** 2
            bump += 0.22 * math.exp(-d2)
            d2 = (tn / 0.18) ** 2 + ((pn - 0.81) / 0.028) ** 2
            bump -= 0.15 * math.exp(-d2)
            for cx in (-0.46, 0.46):
                d2 = ((tn - cx) / 0.16) ** 2 + ((pn - 0.56) / 0.12) ** 2
                bump += 0.11 * math.exp(-d2)
            d2 = (tn / 0.13) ** 2 + ((pn - 0.95) / 0.045) ** 2
            bump += 0.12 * math.exp(-d2)

            r = 1.0 + bump
            width = _face_width_profile(pn)
            x = r * math.sin(phi) * math.sin(theta) * width
            y = -r * math.cos(phi)
            z = r * math.sin(phi) * math.cos(theta)
            row.append((x, y, z))
        rows.append(row)

    head_bottom_y = rows[-1][n_theta // 2][1]

    n_neck_rows = 4
    neck_y0, neck_y1 = head_bottom_y, head_bottom_y + 0.10
    neck_width = 0.30
    for k in range(n_neck_rows):
        t = k / (n_neck_rows - 1)
        yn = neck_y0 + (neck_y1 - neck_y0) * t
        row = []
        for i in range(n_theta):
            theta = -math.pi / 2 + math.pi * (i / (n_theta - 1))
            x = neck_width * math.sin(theta)
            z = neck_width * math.cos(theta) * 0.75
            row.append((x, yn, z))
        rows.append(row)

    n_shoulder_rows = 8
    sh_y0, sh_y1 = neck_y1, neck_y1 + 0.30
    for k in range(n_shoulder_rows):
        t = k / (n_shoulder_rows - 1)
        ys = sh_y0 + (sh_y1 - sh_y0) * t
        shoulder_width = neck_width + 1.35 * (t ** 1.15)
        depth_scale = 0.55 * (1.0 - 0.4 * t)
        row = []
        for i in range(n_theta):
            theta = -math.pi / 2 + math.pi * (i / (n_theta - 1))
            x = shoulder_width * math.sin(theta)
            z = shoulder_width * math.cos(theta) * depth_scale
            row.append((x, ys, z))
        rows.append(row)

    return rows

# GLB chunk type constants (glTF 2.0 spec)
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942
_GLB_MAGIC = 0x46546C67
_GLB_VERSION = 2

# glTF component/type constants
_FLOAT = 5126
_UNSIGNED_SHORT = 5123


def _build_mesh(rows, flat_shaded=True):
    """
    Converts the row-grid point cloud into a vertex array plus a triangle
    index list — the standard "grid of quads -> two triangles each"
    tessellation.

    The point cloud's own coordinate space has +Y pointing DOWN the screen
    (top-of-head is negative Y, per _generate_face_point_cloud's comment),
    which matches Qt's 2D painter convention it was built for. A regular 3D
    scene convention has +Y UP, so Y is negated here.

    flat_shaded=True gives each triangle its own vertices and a single flat
    normal (faceted "cut panel" look) instead of smoothly-averaged vertex
    normals. This deliberately trades organic smoothness for a low-poly,
    angular, panel-like read — smooth shading blurs the eye/nose/cheek
    bumps into an almost featureless dome, while flat facets make each bump
    visible as a distinct plane, closer to the reference image's metallic
    panel aesthetic.
    """
    n_rows = len(rows)
    n_cols = len(rows[0])

    base_positions = []
    for row in rows:
        for (x, y, z) in row:
            base_positions.append((x, -y, z))  # flip Y: screen-down -> world-up

    def vidx(r, c):
        return r * n_cols + c

    quads = []
    for r in range(n_rows - 1):
        for c in range(n_cols - 1):
            a = vidx(r, c)
            b = vidx(r, c + 1)
            d = vidx(r + 1, c)
            e = vidx(r + 1, c + 1)
            quads.append((a, b, e, d))  # two triangles: (a,b,e) and (a,e,d)

    def sub(p, q):
        return (p[0] - q[0], p[1] - q[1], p[2] - q[2])

    def cross(u, v):
        return (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )

    def normalize(n):
        length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
        return (n[0] / length, n[1] / length, n[2] / length)

    raw_triangles = []
    face_normals_z_sum = 0.0
    for (a, b, e, d) in quads:
        for (ia, ib, ic) in ((a, b, e), (a, e, d)):
            pa, pb, pc = base_positions[ia], base_positions[ib], base_positions[ic]
            n = cross(sub(pb, pa), sub(pc, pa))
            face_normals_z_sum += n[2]
            raw_triangles.append((ia, ib, ic, n))

    # This mesh is an open front-facing shell (no back-of-head geometry),
    # meant to face the camera along +Z. If the winding above happens to
    # produce normals pointing away from the camera on average, flip every
    # face consistently rather than guessing per-face (which would produce
    # a mixed/inconsistent shading result).
    flip = face_normals_z_sum < 0

    if flat_shaded:
        positions, normals, indices = [], [], []
        for (ia, ib, ic, n) in raw_triangles:
            n = normalize((-n[0], -n[1], -n[2]) if flip else n)
            order = (ic, ib, ia) if flip else (ia, ib, ic)
            for vi in order:
                indices.append(len(positions))
                positions.append(base_positions[vi])
                normals.append(n)
        return positions, normals, indices

    # Smooth-shaded path (kept for reference / future use): accumulate
    # face normals into shared vertices and average.
    normals_acc = [[0.0, 0.0, 0.0] for _ in base_positions]
    for (ia, ib, ic, n) in raw_triangles:
        if flip:
            n = (-n[0], -n[1], -n[2])
        for i in (ia, ib, ic):
            normals_acc[i][0] += n[0]
            normals_acc[i][1] += n[1]
            normals_acc[i][2] += n[2]

    final_indices = []
    for (ia, ib, ic, _n) in raw_triangles:
        final_indices.extend((ic, ib, ia) if flip else (ia, ib, ic))
    final_normals = [normalize(tuple(n)) for n in normals_acc]

    return base_positions, final_normals, final_indices


def _pad(data: bytes, align: int, pad_byte: bytes) -> bytes:
    remainder = len(data) % align
    if remainder:
        data += pad_byte * (align - remainder)
    return data


def export_glb(rows, out_path: Path, flat_shaded=True):
    positions, normals, indices = _build_mesh(rows, flat_shaded=flat_shaded)
    n_verts = len(positions)
    use_short = n_verts <= 65535
    index_fmt = "<H" if use_short else "<I"
    index_component_type = _UNSIGNED_SHORT if use_short else 5125  # UNSIGNED_INT

    pos_bytes = b"".join(struct.pack("<3f", *p) for p in positions)
    norm_bytes = b"".join(struct.pack("<3f", *n) for n in normals)
    idx_bytes = b"".join(struct.pack(index_fmt, i) for i in indices)
    idx_bytes = _pad(idx_bytes, 4, b"\x00")  # keep subsequent accessors 4-byte aligned

    pos_min = [min(p[a] for p in positions) for a in range(3)]
    pos_max = [max(p[a] for p in positions) for a in range(3)]

    bin_chunk = pos_bytes + norm_bytes + idx_bytes

    gltf = {
        "asset": {"version": "2.0", "generator": "jarvis-build_face_glb.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "JarvisFaceBust"}],
        "meshes": [
            {
                "name": "JarvisFaceBustMesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1},
                        "indices": 2,
                        "material": 0,
                        "mode": 4,  # TRIANGLES
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "JarvisHoloMetal",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.05, 0.14, 0.20, 1.0],
                    "metallicFactor": 0.15,
                    "roughnessFactor": 0.55,
                },
                "emissiveFactor": [0.01, 0.05, 0.08],
                "doubleSided": True,
            }
        ],
        "buffers": [{"byteLength": len(bin_chunk)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(norm_bytes), "target": 34962},
            {
                "buffer": 0,
                "byteOffset": len(pos_bytes) + len(norm_bytes),
                "byteLength": len(idx_bytes),
                "target": 34963,
            },
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": _FLOAT,
                "count": n_verts,
                "type": "VEC3",
                "min": pos_min,
                "max": pos_max,
            },
            {"bufferView": 1, "componentType": _FLOAT, "count": n_verts, "type": "VEC3"},
            {
                "bufferView": 2,
                "componentType": index_component_type,
                "count": len(indices),
                "type": "SCALAR",
            },
        ],
    }

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bytes = _pad(json_bytes, 4, b" ")  # glTF JSON chunk padding must be spaces

    json_chunk_header = struct.pack("<II", len(json_bytes), _CHUNK_JSON)
    bin_chunk_header = struct.pack("<II", len(bin_chunk), _CHUNK_BIN)

    total_length = (
        12  # GLB header
        + 8 + len(json_bytes)
        + 8 + len(bin_chunk)
    )
    glb_header = struct.pack("<III", _GLB_MAGIC, _GLB_VERSION, total_length)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(glb_header)
        f.write(json_chunk_header)
        f.write(json_bytes)
        f.write(bin_chunk_header)
        f.write(bin_chunk)

    return n_verts, len(indices) // 3


if __name__ == "__main__":
    # A real GPU-rasterized mesh (unlike the CPU QPainter point-cloud this
    # geometry was originally built for) comfortably affords a much denser
    # grid, which is what actually makes the Gaussian eye/nose/cheek bumps
    # read as smooth continuous curvature instead of a handful of jagged,
    # hard-to-parse facets.
    rows = _generate_face_mesh_rows(n_theta=90, n_phi=60)
    n_verts, n_tris = export_glb(rows, OUT_PATH, flat_shaded=False)
    size_kb = OUT_PATH.stat().st_size / 1024.0
    print(f"Wrote {OUT_PATH} ({size_kb:.1f} KB): {n_verts} vertices, {n_tris} triangles")
