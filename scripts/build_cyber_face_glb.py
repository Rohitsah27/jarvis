import json
import struct
import numpy as np
from pathlib import Path

def build_cyber_face_glb():
    src_glb = Path("ui/web/LeePerrySmith.glb")
    out_glb = Path("ui/web/jarvis_cyber_face.glb")
    
    print(f"Reading base model: {src_glb}")
    with open(src_glb, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        chunk_len, chunk_type = struct.unpack("<II", f.read(8))
        gltf = json.loads(f.read(chunk_len).decode("utf-8"))
        bin_len, bin_type = struct.unpack("<II", f.read(8))
        bin_data = f.read(bin_len)
        
    acc_idx = gltf["accessors"][0]
    acc_pos = gltf["accessors"][1]
    acc_norm = gltf["accessors"][2]
    acc_uv = gltf["accessors"][3]
    
    bv_idx = gltf["bufferViews"][acc_idx["bufferView"]]
    bv_pos = gltf["bufferViews"][acc_pos["bufferView"]]
    bv_norm = gltf["bufferViews"][acc_norm["bufferView"]]
    bv_uv = gltf["bufferViews"][acc_uv["bufferView"]]
    
    idx_offset = bv_idx.get("byteOffset", 0) + acc_idx.get("byteOffset", 0)
    pos_offset = bv_pos.get("byteOffset", 0) + acc_pos.get("byteOffset", 0)
    norm_offset = bv_norm.get("byteOffset", 0) + acc_norm.get("byteOffset", 0)
    uv_offset = bv_uv.get("byteOffset", 0) + acc_uv.get("byteOffset", 0)
    
    indices = np.frombuffer(bin_data[idx_offset:idx_offset + acc_idx["count"] * 2], dtype=np.uint16).copy()
    positions = np.frombuffer(bin_data[pos_offset:pos_offset + acc_pos["count"] * 12], dtype=np.float32).reshape(-1, 3).copy()
    normals = np.frombuffer(bin_data[norm_offset:norm_offset + acc_norm["count"] * 12], dtype=np.float32).reshape(-1, 3).copy()
    uvs = np.frombuffer(bin_data[uv_offset:uv_offset + acc_uv["count"] * 8], dtype=np.float32).reshape(-1, 2).copy()
    
    # 1. Center the geometry on exact anatomical center
    center = (positions.max(axis=0) + positions.min(axis=0)) / 2.0
    positions -= center
    
    # Precise nose tip centering
    nose_mask = (np.abs(positions[:, 0]) < 0.3) & (positions[:, 1] > 0.5) & (positions[:, 1] < 1.5)
    nose_pts = positions[nose_mask]
    tip_idx = np.argmax(nose_pts[:, 2])
    x_shift = nose_pts[tip_idx, 0]
    positions[:, 0] -= x_shift
    print(f"Shifted X axis by {-x_shift:.4f} so nose apex is exactly at X=0.0")
    
    # 2. Deform geometry according to Subject ID: PHM-731 blueprint:
    y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
    
    for i in range(len(positions)):
        x, y, z = positions[i]
        
        # A. Jawline Taper & V-Chin (Sleek V-shaped cyber jaw from blueprint)
        if y < 0.6:
            t = np.clip((y - (-1.2)) / (0.6 - (-1.2)), 0.0, 1.0)
            taper = 0.66 + 0.34 * (t ** 1.35)
            positions[i, 0] *= taper
            
        # Chin apex narrowing
        if -0.2 < y < 0.5 and abs(x) < 0.8 and z > 1.6:
            chin_v = np.exp(-((y - 0.15) / 0.30) ** 2) * np.clip(1.0 - (abs(x) / 0.7), 0.0, 1.0)
            positions[i, 0] *= (1.0 - 0.25 * chin_v)
            
        # Submental neck tuck (clean, sharp profile jawline without rounded submental bulge)
        if -1.4 < y < 0.2 and abs(x) < 0.9:
            if z < 1.7:
                depth_fac = np.clip((1.7 - z) / 1.5, 0.0, 1.0) * (1.0 - (abs(x) / 0.9))
                positions[i, 2] -= 0.22 * depth_fac

        # B. High, sculpted Zygomatic Cheekbones (Blueprint Frontal & 3/4 Profile)
        if 0.7 < y < 1.8 and abs(x) > 0.4:
            cheek_weight = np.exp(-((y - 1.38) / 0.38) ** 2) * np.exp(-((abs(x) - 1.25) / 0.45) ** 2)
            positions[i, 0] += np.sign(x) * 0.075 * cheek_weight
            positions[i, 2] += 0.095 * cheek_weight
            
        # C. Slender, refined cyber button nose (45% narrower bridge and pinched nostrils)
        if 0.6 < y < 1.6 and abs(x) < 0.65 and z > 1.2:
            nose_weight = np.exp(-((y - 1.15) / 0.35) ** 2) * np.clip(1.0 - (abs(x) / 0.55), 0.0, 1.0)
            positions[i, 0] *= (1.0 - 0.42 * nose_weight)
            if z > 2.0:
                positions[i, 1] += 0.045 * nose_weight
                positions[i, 2] += 0.020 * nose_weight

        # D. Brow Ridge Softening (eliminate heavy male supraorbital torus)
        if 1.7 < y < 2.3 and abs(x) < 1.4 and z > 1.4:
            brow_weight = np.exp(-((y - 1.95) / 0.28) ** 2) * np.clip(1.0 - (abs(x) / 1.3), 0.0, 1.0)
            positions[i, 2] -= 0.14 * brow_weight
            
        # E. Cranial Oval & Temple Narrowing
        if y > 1.4:
            crown_t = (y - 1.4) / (y_max - 1.4)
            crown_taper = 1.0 - 0.12 * (crown_t ** 1.3)
            positions[i, 0] *= crown_taper
            
        if 1.5 < y < 2.5 and abs(x) > 1.0:
            temple_w = np.exp(-((y - 1.9) / 0.4) ** 2)
            positions[i, 0] *= (1.0 - 0.10 * temple_w)
            
        # F. Sleek, tucked cyber ears (pull lateral protrusion in)
        if 0.6 < y < 1.9 and abs(x) > 1.6:
            ear_t = np.clip((abs(x) - 1.6) / 0.8, 0.0, 1.0)
            positions[i, 0] -= np.sign(x) * 0.14 * ear_t

        # G. Slender neck
        if y < -0.6:
            neck_t = np.clip((-y - 0.6) / (abs(y_min) - 0.6), 0.0, 1.0)
            positions[i, 0] *= (1.0 - 0.18 * neck_t)
            positions[i, 2] *= (1.0 - 0.12 * neck_t)
            
    print("Anatomical blueprint deformation applied.")
    
    # 3. Recalculate vertex normals
    new_normals = np.zeros_like(positions)
    tri_count = len(indices) // 3
    for t in range(tri_count):
        ia, ib, ic = indices[t*3], indices[t*3+1], indices[t*3+2]
        va, vb, vc = positions[ia], positions[ib], positions[ic]
        fn = np.cross(vb - va, vc - va)
        norm_len = np.linalg.norm(fn)
        if norm_len > 1e-8:
            fn /= norm_len
            new_normals[ia] += fn
            new_normals[ib] += fn
            new_normals[ic] += fn
            
    lengths = np.linalg.norm(new_normals, axis=1, keepdims=True)
    lengths[lengths == 0] = 1.0
    new_normals /= lengths
    
    # 4. Pack into standard GLB binary
    pos_bytes = positions.astype(np.float32).tobytes()
    norm_bytes = new_normals.astype(np.float32).tobytes()
    uv_bytes = uvs.astype(np.float32).tobytes()
    idx_bytes = indices.astype(np.uint16).tobytes()
    
    def pad4(b):
        pad = (4 - (len(b) % 4)) % 4
        return b + b"\x00" * pad
        
    bv0_data = pad4(idx_bytes)
    bv1_data = pad4(pos_bytes)
    bv2_data = pad4(norm_bytes)
    bv3_data = pad4(uv_bytes)
    
    bin_buffer = bv0_data + bv1_data + bv2_data + bv3_data
    
    offset0 = 0
    len0 = len(idx_bytes)
    offset1 = len(bv0_data)
    len1 = len(pos_bytes)
    offset2 = offset1 + len(bv1_data)
    len2 = len(norm_bytes)
    offset3 = offset2 + len(bv2_data)
    len3 = len(uv_bytes)
    
    out_gltf = {
        "asset": {
            "version": "2.0",
            "generator": "JARVIS Cyber Face Generator (PHM-731 Blueprint)"
        },
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "JarvisCyberFace", "mesh": 0}],
        "meshes": [
            {
                "name": "CyberFaceMesh",
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 1,
                            "NORMAL": 2,
                            "TEXCOORD_0": 3
                        },
                        "indices": 0,
                        "mode": 4
                    }
                ]
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5123,
                "count": len(indices),
                "type": "SCALAR"
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5126,
                "count": len(positions),
                "type": "VEC3",
                "max": positions.max(axis=0).tolist(),
                "min": positions.min(axis=0).tolist()
            },
            {
                "bufferView": 2,
                "byteOffset": 0,
                "componentType": 5126,
                "count": len(new_normals),
                "type": "VEC3"
            },
            {
                "bufferView": 3,
                "byteOffset": 0,
                "componentType": 5126,
                "count": len(uvs),
                "type": "VEC2"
            }
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": offset0, "byteLength": len0, "target": 34963},
            {"buffer": 0, "byteOffset": offset1, "byteLength": len1, "target": 34962},
            {"buffer": 0, "byteOffset": offset2, "byteLength": len2, "target": 34962},
            {"buffer": 0, "byteOffset": offset3, "byteLength": len3, "target": 34962}
        ],
        "buffers": [{"byteLength": len(bin_buffer)}]
    }
    
    json_bytes = json.dumps(out_gltf, separators=(',', ':')).encode("utf-8")
    pad_json = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * pad_json
    
    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_buffer)
    
    with open(out_glb, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_buffer), 0x004E4942))
        f.write(bin_buffer)
        
    print(f"Successfully generated {out_glb} (size: {total_len} bytes)!")

if __name__ == "__main__":
    build_cyber_face_glb()
