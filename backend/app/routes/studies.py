"""Study ingest and asset endpoints."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.convert.nifti import axial_slice_hu, series_to_nifti
from app.deid import deidentify_datasets
from app.dicom.validate import load_dicom_files, validate_series
from app.imaging import slice_to_png_bytes
from app.schemas import StudyCreateResponse, StudySummary, ValidationIssueOut
from app.store import StudyStore, store

router = APIRouter(prefix="/studies", tags=["studies"])

# Error codes that block conversion (geometry / identity unsafe).
BLOCKING_CODES = {
    "EMPTY",
    "MISSING_TAGS",
    "MIXED_SERIES",
    "INCONSISTENT_ORIENTATION",
    "INCONSISTENT_SPACING_OR_SIZE",
    "BAD_STACK",
}


def _issues_out(issues: list) -> list[ValidationIssueOut]:
    return [
        ValidationIssueOut(
            code=i.code if hasattr(i, "code") else i["code"],
            message=i.message if hasattr(i, "message") else i["message"],
            severity=i.severity.value if hasattr(i, "severity") else i["severity"],
            requirement_id=(
                i.requirement_id if hasattr(i, "requirement_id") else i.get("requirement_id")
            ),
        )
        for i in issues
    ]


def _summary_from_record(record) -> StudySummary:
    return StudySummary(
        id=record.id,
        ok=record.ok,
        slice_count=record.slice_count,
        series_uid=record.series_uid,
        spacing_mm=record.spacing_mm,
        iop=record.iop,
        origin_lps=record.origin_lps,
        shape_ijk=record.shape_ijk,
        deidentified=record.deidentified,
        nifti_ready=record.nifti_ready,
        issues=_issues_out(record.issues),
    )


def _extract_upload(upload: UploadFile, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    filename = upload.filename or "upload.bin"
    raw_path = dest / filename
    raw_path.write_bytes(upload.file.read())

    if zipfile.is_zipfile(raw_path):
        extract_dir = dest / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(raw_path, "r") as zf:
            zf.extractall(extract_dir)
        return [p for p in extract_dir.rglob("*") if p.is_file()]

    return [raw_path]


def ingest_paths(
    paths: list[Path],
    *,
    deidentify: bool,
    study_store: StudyStore,
) -> StudyCreateResponse:
    datasets = load_dicom_files(paths)
    if deidentify and datasets:
        deidentify_datasets(datasets)

    report = validate_series(datasets)
    issues = [
        {
            "code": i.code,
            "message": i.message,
            "severity": i.severity.value,
            "requirement_id": i.requirement_id,
        }
        for i in report.issues
    ]
    blocking = {i.code for i in report.issues if i.severity.value == "error"} & BLOCKING_CODES
    can_convert = len(datasets) > 0 and not blocking

    study_id = study_store.new_id()
    origin_lps = None
    shape_ijk = None
    spacing = report.spacing_mm
    iop = report.iop
    nifti_ready = False
    volume = None

    if can_convert:
        try:
            nifti_path = study_store.study_dir(study_id) / "volume.nii.gz"
            result = series_to_nifti(datasets, nifti_path)
            volume = result.volume_hu
            origin_lps = result.origin_lps
            shape_ijk = tuple(int(x) for x in result.volume_hu.shape)
            spacing = result.spacing_mm
            iop = result.iop
            nifti_ready = True
        except Exception as exc:  # noqa: BLE001 — surface as validation issue
            issues.append(
                {
                    "code": "CONVERSION_FAILED",
                    "message": str(exc),
                    "severity": "error",
                    "requirement_id": "REQ-GEO-001",
                }
            )
            report.ok = False

    record = study_store.save(
        study_id=study_id,
        ok=report.ok and nifti_ready,
        slice_count=report.slice_count,
        series_uid=report.series_uid,
        spacing_mm=spacing,
        iop=iop,
        origin_lps=origin_lps,
        shape_ijk=shape_ijk,
        deidentified=deidentify,
        nifti_ready=nifti_ready,
        issues=issues,
        volume=volume,
    )
    return StudyCreateResponse(**_summary_from_record(record).model_dump())


FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "dicom"

DEMO_SAMPLES = {
    "synthetic": FIXTURE_ROOT / "good_series",
    "tcia": FIXTURE_ROOT / "tcia_sample",
}


@router.post("", response_model=StudyCreateResponse)
async def create_study(
    file: UploadFile = File(..., description="DICOM file or ZIP of a CT series"),
    deidentify: bool = Query(True, description="Blank PHI tags on ingest"),
) -> StudyCreateResponse:
    with tempfile.TemporaryDirectory(prefix="dicom_ingest_") as tmp:
        paths = _extract_upload(file, Path(tmp))
        if not paths:
            raise HTTPException(status_code=400, detail="Empty upload")
        return ingest_paths(paths, deidentify=deidentify, study_store=store)


@router.post("/demo/{sample}", response_model=StudyCreateResponse)
def create_demo_study(
    sample: str,
    deidentify: bool = Query(True, description="Blank PHI tags on ingest"),
) -> StudyCreateResponse:
    """Load a fixture series without uploading (synthetic or TCIA sample)."""
    key = sample.lower().strip()
    if key not in DEMO_SAMPLES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown sample '{sample}'. Use: {', '.join(sorted(DEMO_SAMPLES))}",
        )
    directory = DEMO_SAMPLES[key]
    if not directory.exists():
        hint = (
            "Run: uv run python ../scripts/download_tcia_sample.py"
            if key == "tcia"
            else "Run: uv run python ../scripts/generate_fixtures.py"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Fixture missing at {directory}. {hint}",
        )
    paths = sorted(p for p in directory.rglob("*") if p.is_file())
    if not paths:
        raise HTTPException(status_code=404, detail=f"No DICOM files in {directory}")
    return ingest_paths(paths, deidentify=deidentify, study_store=store)


@router.get("/{study_id}", response_model=StudySummary)
def get_study(study_id: str) -> StudySummary:
    try:
        record = store.get(study_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Study not found") from exc
    return _summary_from_record(record)


@router.get("/{study_id}/nifti")
def download_nifti(study_id: str) -> FileResponse:
    try:
        record = store.get(study_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Study not found") from exc
    if not record.nifti_ready or not record.nifti_path.exists():
        raise HTTPException(status_code=404, detail="NIfTI not available for this study")
    return FileResponse(
        record.nifti_path,
        media_type="application/gzip",
        filename=f"{study_id}.nii.gz",
    )


@router.get("/{study_id}/slices/{z}")
def get_slice(
    study_id: str,
    z: int,
    center: float = Query(40.0, description="Window center (HU)"),
    width: float = Query(400.0, description="Window width (HU)"),
) -> Response:
    try:
        record = store.get(study_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Study not found") from exc
    if not record.volume_path.exists():
        raise HTTPException(status_code=404, detail="Volume not available")
    volume = record.load_volume()
    try:
        slice_hu = axial_slice_hu(volume, z)
    except IndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    png = slice_to_png_bytes(slice_hu, center=center, width=width)
    return Response(content=png, media_type="image/png")
