"""CT series integrity validation (REQ-VAL-*)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pydicom
from pydicom.dataset import Dataset

from app.dicom.geometry import estimate_slice_spacing, slice_normal


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    requirement_id: str | None = None


@dataclass
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    slice_count: int = 0
    series_uid: str | None = None
    spacing_mm: tuple[float, float, float] | None = None  # row, col, slice
    iop: list[float] | None = None

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity == Severity.ERROR:
            self.ok = False


def load_dicom_files(paths: Iterable[Path | str]) -> list[Dataset]:
    """Load DICOM datasets from files; skip non-DICOM quietly."""
    datasets: list[Dataset] = []
    for path in paths:
        path = Path(path)
        try:
            ds = pydicom.dcmread(path, force=True)
        except Exception:
            continue
        if not hasattr(ds, "SOPClassUID"):
            continue
        datasets.append(ds)
    return datasets


def load_dicom_directory(directory: Path | str) -> list[Dataset]:
    directory = Path(directory)
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    return load_dicom_files(files)


def _vectors_close(a: Sequence[float], b: Sequence[float], atol: float = 1e-4) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), atol=atol))


def sort_by_position(datasets: Sequence[Dataset]) -> list[Dataset]:
    """Sort slices along the stack normal using ImagePositionPatient."""
    if not datasets:
        return []
    iop = [float(x) for x in datasets[0].ImageOrientationPatient]
    normal = slice_normal(iop)

    def key(ds: Dataset) -> float:
        ipp = np.asarray([float(x) for x in ds.ImagePositionPatient], dtype=np.float64)
        return float(np.dot(ipp, normal))

    return sorted(datasets, key=key)


def validate_series(datasets: Sequence[Dataset]) -> ValidationReport:
    """Validate a CT series for mixed identity, spacing, orientation, and gaps.

    Requirement IDs (interview / traceability):
    - REQ-VAL-001 mixed SeriesInstanceUID
    - REQ-VAL-002 inconsistent Rows/Columns or PixelSpacing
    - REQ-VAL-003 inconsistent ImageOrientationPatient
    - REQ-VAL-004 missing / gapped slices along the stack
    - REQ-GEO-001 spacing / orientation extractable for conversion
    """
    report = ValidationReport(ok=True, slice_count=len(datasets))

    if not datasets:
        report.add(
            ValidationIssue(
                code="EMPTY",
                message="No DICOM instances provided",
                requirement_id="REQ-VAL-004",
            )
        )
        return report

    required = (
        "SeriesInstanceUID",
        "SOPInstanceUID",
        "ImageOrientationPatient",
        "ImagePositionPatient",
        "PixelSpacing",
        "Rows",
        "Columns",
    )
    for idx, ds in enumerate(datasets):
        missing = [tag for tag in required if not hasattr(ds, tag)]
        if missing:
            report.add(
                ValidationIssue(
                    code="MISSING_TAGS",
                    message=f"Instance {idx} missing tags: {', '.join(missing)}",
                    requirement_id="REQ-GEO-001",
                )
            )
    if not report.ok:
        return report

    series_uids = {str(ds.SeriesInstanceUID) for ds in datasets}
    report.series_uid = next(iter(series_uids))
    if len(series_uids) > 1:
        report.add(
            ValidationIssue(
                code="MIXED_SERIES",
                message=f"Upload contains {len(series_uids)} SeriesInstanceUID values",
                requirement_id="REQ-VAL-001",
            )
        )

    ref = datasets[0]
    ref_iop = [float(x) for x in ref.ImageOrientationPatient]
    ref_spacing = [float(x) for x in ref.PixelSpacing]
    ref_rows, ref_cols = int(ref.Rows), int(ref.Columns)
    report.iop = ref_iop

    for idx, ds in enumerate(datasets):
        iop = [float(x) for x in ds.ImageOrientationPatient]
        spacing = [float(x) for x in ds.PixelSpacing]
        if not _vectors_close(iop, ref_iop):
            report.add(
                ValidationIssue(
                    code="INCONSISTENT_ORIENTATION",
                    message=f"Instance {idx} ImageOrientationPatient differs from first slice",
                    requirement_id="REQ-VAL-003",
                )
            )
        if not _vectors_close(spacing, ref_spacing) or int(ds.Rows) != ref_rows or int(ds.Columns) != ref_cols:
            report.add(
                ValidationIssue(
                    code="INCONSISTENT_SPACING_OR_SIZE",
                    message=(
                        f"Instance {idx} PixelSpacing/Rows/Columns inconsistent "
                        f"(got spacing={spacing}, {ds.Rows}x{ds.Columns})"
                    ),
                    requirement_id="REQ-VAL-002",
                )
            )

    # Gap detection on sorted positions
    sorted_ds = sort_by_position(datasets)
    positions = [[float(x) for x in ds.ImagePositionPatient] for ds in sorted_ds]
    try:
        slice_spacing = estimate_slice_spacing(positions, ref_iop)
    except ValueError as exc:
        report.add(
            ValidationIssue(
                code="BAD_STACK",
                message=str(exc),
                requirement_id="REQ-VAL-004",
            )
        )
        return report

    report.spacing_mm = (float(ref_spacing[0]), float(ref_spacing[1]), slice_spacing)

    normal = slice_normal(ref_iop)
    projections = np.array([np.dot(np.asarray(p), normal) for p in positions])
    # projections already ordered by sort_by_position
    deltas = np.diff(projections)
    if deltas.size:
        expected = slice_spacing
        # Flag gaps larger than 1.5x expected spacing, or near-duplicates
        for i, delta in enumerate(deltas):
            if delta < expected * 0.25:
                report.add(
                    ValidationIssue(
                        code="DUPLICATE_OR_OVERLAPPING_SLICE",
                        message=f"Slices {i} and {i + 1} nearly overlap (Δ={delta:.4f} mm)",
                        severity=Severity.WARNING,
                        requirement_id="REQ-VAL-004",
                    )
                )
            elif delta > expected * 1.5:
                report.add(
                    ValidationIssue(
                        code="MISSING_SLICE_GAP",
                        message=(
                            f"Gap between slices {i} and {i + 1}: Δ={delta:.4f} mm "
                            f"(expected ~{expected:.4f} mm)"
                        ),
                        requirement_id="REQ-VAL-004",
                    )
                )

    instance_numbers = [int(getattr(ds, "InstanceNumber", -1)) for ds in sorted_ds]
    if all(n >= 0 for n in instance_numbers):
        nums = sorted(instance_numbers)
        expected_nums = list(range(nums[0], nums[0] + len(nums)))
        if nums != expected_nums:
            report.add(
                ValidationIssue(
                    code="INSTANCE_NUMBER_GAP",
                    message=f"InstanceNumber sequence has gaps or duplicates: {instance_numbers}",
                    severity=Severity.WARNING,
                    requirement_id="REQ-VAL-004",
                )
            )

    return report
