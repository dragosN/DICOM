"""Static mesh assets for the viewer demo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/meshes", tags=["meshes"])

MESH_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "meshes"


@router.get("/bone")
def get_bone_mesh() -> FileResponse:
    path = MESH_ROOT / "bone.glb"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="bone.glb missing — run: uv run python ../scripts/generate_mesh.py",
        )
    return FileResponse(path, media_type="model/gltf-binary", filename="bone.glb")
