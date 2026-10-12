#!/usr/bin/env python3
"""Write a tiny bone-like cylinder GLB (no trimesh dependency)."""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "meshes" / "bone.glb"


def _cylinder(radius: float = 4.0, height: float = 14.0, segments: int = 16):
    positions: list[float] = []
    indices: list[int] = []
    # Top and bottom center + rings
    positions.extend([0.0, height / 2, 0.0])  # 0 top
    positions.extend([0.0, -height / 2, 0.0])  # 1 bottom
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x, z = radius * math.cos(angle), radius * math.sin(angle)
        positions.extend([x, height / 2, z])  # top ring starts at 2
        positions.extend([x, -height / 2, z])  # bottom ring
    for i in range(segments):
        top_a = 2 + 2 * i
        top_b = 2 + 2 * ((i + 1) % segments)
        bot_a = top_a + 1
        bot_b = top_b + 1
        # top fan
        indices.extend([0, top_a, top_b])
        # bottom fan
        indices.extend([1, bot_b, bot_a])
        # side quads → two tris
        indices.extend([top_a, bot_a, bot_b])
        indices.extend([top_a, bot_b, top_b])
    return positions, indices


def write_glb(path: Path) -> None:
    positions, indices = _cylinder()
    pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
    idx_bytes = struct.pack(f"<{len(indices)}H", *indices)
    # Align each buffer view to 4 bytes
    def pad4(b: bytes) -> bytes:
        return b + (b"\x00" * ((4 - (len(b) % 4)) % 4))

    pos_padded = pad4(pos_bytes)
    idx_padded = pad4(idx_bytes)
    bin_chunk = pos_padded + idx_padded

    pos_min = [min(positions[i::3]) for i in range(3)]
    pos_max = [max(positions[i::3]) for i in range(3)]

    gltf = {
        "asset": {"version": "2.0", "generator": "dicom-portfolio-generate_mesh"},
        "scenes": [{"nodes": [0]}],
        "scene": 0,
        "nodes": [{"mesh": 0, "name": "Bone"}],
        "meshes": [
            {
                "name": "BoneMesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1,
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
                "componentType": 5123,
                "count": len(indices),
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
            {
                "buffer": 0,
                "byteOffset": len(pos_padded),
                "byteLength": len(idx_bytes),
                "target": 34963,
            },
        ],
        "buffers": [{"byteLength": len(bin_chunk)}],
    }

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bytes = pad4(json_bytes)

    # GLB: 12-byte header + JSON chunk + BIN chunk
    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    header = struct.pack("<4sII", b"glTF", 2, total_length)
    json_chunk = struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes
    bin_header = struct.pack("<I4s", len(bin_chunk), b"BIN\x00") + bin_chunk

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + json_chunk + bin_header)
    print(f"Wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    write_glb(OUT)
