#!/usr/bin/env python3
"""Convert a Wavefront OBJ (triangle mesh) to a padded glTF 2.0 GLB."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path


def load_obj(path: Path) -> tuple[list[float], list[float], list[int]]:
    positions: list[list[float]] = []
    normals_in: list[list[float]] = []
    faces: list[tuple[tuple[int, int | None], ...]] = []

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif parts[0] == "vn" and len(parts) >= 4:
            normals_in.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif parts[0] == "f" and len(parts) >= 4:
            corners = []
            for token in parts[1:]:
                bits = token.split("/")
                vi = int(bits[0]) - 1
                ni = int(bits[2]) - 1 if len(bits) >= 3 and bits[2] else None
                corners.append((vi, ni))
            # triangulate fan
            for i in range(1, len(corners) - 1):
                faces.append((corners[0], corners[i], corners[i + 1]))

    # Expand to unique vertices so normals stay correct
    out_pos: list[float] = []
    out_nrm: list[float] = []
    indices: list[int] = []
    for tri in faces:
        for vi, ni in tri:
            p = positions[vi]
            out_pos.extend(p)
            if ni is not None and 0 <= ni < len(normals_in):
                out_nrm.extend(normals_in[ni])
            else:
                out_nrm.extend([0.0, 0.0, 0.0])
            indices.append(len(out_pos) // 3 - 1)

    # Fill missing normals from faces
    if all(n == 0.0 for n in out_nrm):
        out_nrm = [0.0] * len(out_pos)
        for i in range(0, len(indices), 3):
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
            p0 = out_pos[i0 * 3 : i0 * 3 + 3]
            p1 = out_pos[i1 * 3 : i1 * 3 + 3]
            p2 = out_pos[i2 * 3 : i2 * 3 + 3]
            e1 = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]]
            e2 = [p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]]
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            for idx in (i0, i1, i2):
                out_nrm[idx * 3] += nx
                out_nrm[idx * 3 + 1] += ny
                out_nrm[idx * 3 + 2] += nz
        for i in range(0, len(out_nrm), 3):
            x, y, z = out_nrm[i], out_nrm[i + 1], out_nrm[i + 2]
            length = math.sqrt(x * x + y * y + z * z) or 1.0
            out_nrm[i] = x / length
            out_nrm[i + 1] = y / length
            out_nrm[i + 2] = z / length

    # Center and scale to ~18 units tall for the viewer
    xs = out_pos[0::3]
    ys = out_pos[1::3]
    zs = out_pos[2::3]
    min_y, max_y = min(ys), max(ys)
    cx = (min(xs) + max(xs)) / 2
    cy = (min_y + max_y) / 2
    cz = (min(zs) + max(zs)) / 2
    extent = max(max(xs) - min(xs), max_y - min_y, max(zs) - min(zs)) or 1.0
    scale = 18.0 / extent
    for i in range(0, len(out_pos), 3):
        out_pos[i] = (out_pos[i] - cx) * scale
        out_pos[i + 1] = (out_pos[i + 1] - cy) * scale
        out_pos[i + 2] = (out_pos[i + 2] - cz) * scale

    return out_pos, out_nrm, indices


def pad4(b: bytes, pad: bytes = b"\x00") -> bytes:
    return b + (pad * ((4 - (len(b) % 4)) % 4))


def write_glb(path: Path, positions: list[float], normals: list[float], indices: list[int]) -> None:
    pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
    nrm_bytes = struct.pack(f"<{len(normals)}f", *normals)
    if max(indices, default=0) > 65535:
        idx_bytes = struct.pack(f"<{len(indices)}I", *indices)
        idx_component = 5125
    else:
        idx_bytes = struct.pack(f"<{len(indices)}H", *indices)
        idx_component = 5123

    pos_padded = pad4(pos_bytes)
    nrm_padded = pad4(nrm_bytes)
    idx_padded = pad4(idx_bytes)
    bin_chunk = pos_padded + nrm_padded + idx_padded
    nrm_offset = len(pos_padded)
    idx_offset = nrm_offset + len(nrm_padded)

    pos_min = [min(positions[i::3]) for i in range(3)]
    pos_max = [max(positions[i::3]) for i in range(3)]

    gltf = {
        "asset": {"version": "2.0", "generator": "dicom-portfolio-obj_to_glb"},
        "scenes": [{"nodes": [0]}],
        "scene": 0,
        "nodes": [{"mesh": 0, "name": "Femur"}],
        "meshes": [
            {
                "name": "FemurMesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1},
                        "indices": 2,
                        "mode": 4,
                    }
                ],
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": len(positions) // 3,
                "type": "VEC3",
                "max": pos_max,
                "min": pos_min,
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": len(normals) // 3,
                "type": "VEC3",
            },
            {
                "bufferView": 2,
                "componentType": idx_component,
                "count": len(indices),
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": nrm_offset, "byteLength": len(nrm_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_chunk)}],
    }

    json_bytes = pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), pad=b"\x20")
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    blob = (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_bytes), b"JSON")
        + json_bytes
        + struct.pack("<I4s", len(bin_chunk), b"BIN\x00")
        + bin_chunk
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    print(f"Wrote {path} ({path.stat().st_size} bytes, {len(indices) // 3} tris)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("obj", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    pos, nrm, idx = load_obj(args.obj)
    write_glb(args.output, pos, nrm, idx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
