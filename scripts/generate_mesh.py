#!/usr/bin/env python3
"""Build the viewer bone GLB from the anatomical femur OBJ (preferred).

Falls back to a procedural solid-looking shaft only if femur.obj is missing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEMUR_OBJ = ROOT / "fixtures" / "meshes" / "femur.obj"
OUT = ROOT / "fixtures" / "meshes" / "bone.glb"
PUBLIC_OUT = ROOT / "frontend" / "public" / "meshes" / "bone.glb"
OBJ_TO_GLB = ROOT / "scripts" / "obj_to_glb.py"


def main() -> int:
    if not FEMUR_OBJ.exists():
        print(
            f"Missing {FEMUR_OBJ}. Place a femur OBJ there, or re-download from\n"
            "https://raw.githubusercontent.com/nzfeng/points-as-tori/9896681d/data/femur.obj",
            file=sys.stderr,
        )
        return 1

    subprocess.check_call(
        [sys.executable, str(OBJ_TO_GLB), str(FEMUR_OBJ), "-o", str(OUT)],
    )
    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.write_bytes(OUT.read_bytes())
    print(f"Wrote {PUBLIC_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
