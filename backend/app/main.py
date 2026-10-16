"""FastAPI application: DICOM ingest, validation, NIfTI, slices."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import meshes, studies

app = FastAPI(
    title="DICOM Portfolio API",
    description="Validate CT series, convert to NIfTI, serve slices for the interview demo.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(studies.router)
app.include_router(meshes.router)


@app.get("/")
def root() -> dict[str, object]:
    """Landing for browsers hitting localhost:8000 (avoids a bare 404)."""
    return {
        "name": "DICOM Portfolio API",
        "status": "ok",
        "intended_use": "Educational / interview demo only. Not SaMD. Not for diagnosis or treatment.",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "POST /studies": "Upload a DICOM ZIP",
            "POST /studies/demo/{synthetic|tcia}": "Load fixture series",
            "GET /studies/{id}": "Study metadata + validation",
            "GET /studies/{id}/slices/{z}": "Axial PNG slice",
            "GET /studies/{id}/nifti": "Download NIfTI",
            "GET /meshes/bone": "Demo GLB mesh",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
