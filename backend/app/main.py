"""FastAPI application skeleton (Day 1 morning)."""

from fastapi import FastAPI

app = FastAPI(
    title="DICOM Portfolio API",
    description="Validate CT series, convert to NIfTI, serve slices for the interview demo.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
