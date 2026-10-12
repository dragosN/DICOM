"""Patient geometry helpers: DICOM LPS affine, RAS conversion, HU rescale.

DICOM stores Image Position/Orientation Patient in the LPS frame
(Left, Posterior, Superior). NIfTI commonly uses RAS (Right, Anterior, Superior).
Getting this wrong is the classic medical imaging bug.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from pydicom.dataset import Dataset

# Homogeneous transform that flips L→R and P→A (LPS → RAS).
LPS_TO_RAS: NDArray[np.float64] = np.diag([-1.0, -1.0, 1.0, 1.0])


def direction_cosine_matrix(iop: Sequence[float]) -> NDArray[np.float64]:
    """Build a 3x3 direction matrix from ImageOrientationPatient (6 values).

    Columns are: row direction (X), column direction (Y), slice normal (Z = X × Y).
    """
    if len(iop) != 6:
        raise ValueError(f"ImageOrientationPatient must have 6 values, got {len(iop)}")
    row = np.asarray(iop[:3], dtype=np.float64)
    col = np.asarray(iop[3:], dtype=np.float64)
    normal = np.cross(row, col)
    matrix = np.column_stack([row, col, normal])
    return matrix


def slice_normal(iop: Sequence[float]) -> NDArray[np.float64]:
    """Unit-ish slice normal from IOP (X × Y)."""
    return direction_cosine_matrix(iop)[:, 2]


def pixel_spacings(ds: Dataset) -> tuple[float, float]:
    """Return (row_spacing_mm, col_spacing_mm) from PixelSpacing.

    DICOM PixelSpacing is [adjacent_row_spacing, adjacent_column_spacing].
    """
    spacing = getattr(ds, "PixelSpacing", None)
    if spacing is None or len(spacing) != 2:
        raise ValueError("Dataset missing PixelSpacing")
    row_spacing = float(spacing[0])
    col_spacing = float(spacing[1])
    return row_spacing, col_spacing


def build_lps_affine(
    iop: Sequence[float],
    ipp: Sequence[float],
    row_spacing: float,
    col_spacing: float,
    slice_spacing: float,
) -> NDArray[np.float64]:
    """4x4 affine mapping voxel indices (i, j, k) → LPS patient mm.

    i = column index, j = row index, k = slice index.
    Origin is ImagePositionPatient of the first slice (voxel 0,0,0).
    """
    dirs = direction_cosine_matrix(iop)
    # Scale columns by voxel sizes: col (i), row (j), slice (k)
    scaled = dirs @ np.diag([col_spacing, row_spacing, slice_spacing])
    affine = np.eye(4, dtype=np.float64)
    affine[:3, :3] = scaled
    affine[:3, 3] = np.asarray(ipp, dtype=np.float64)
    return affine


def affine_lps_to_ras(affine_lps: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert an LPS voxel→world affine into RAS (NIfTI-style)."""
    return LPS_TO_RAS @ np.asarray(affine_lps, dtype=np.float64)


def hounsfield_units(
    stored: NDArray[np.floating] | NDArray[np.integer],
    slope: float = 1.0,
    intercept: float = 0.0,
) -> NDArray[np.float64]:
    """Apply RescaleSlope / RescaleIntercept → Hounsfield units."""
    return np.asarray(stored, dtype=np.float64) * float(slope) + float(intercept)


def estimate_slice_spacing(
    positions: Sequence[Sequence[float]],
    iop: Sequence[float],
) -> float:
    """Median spacing between consecutive sorted IPP projections along the slice normal."""
    if len(positions) < 2:
        raise ValueError("Need at least two ImagePositionPatient values")
    normal = slice_normal(iop)
    projections = np.array([np.dot(np.asarray(p, dtype=np.float64), normal) for p in positions])
    projections.sort()
    deltas = np.diff(projections)
    # Ignore near-zero duplicates; take median of positive gaps
    positive = deltas[deltas > 1e-6]
    if positive.size == 0:
        raise ValueError("All slices share the same projected position")
    return float(np.median(positive))


def dataset_geometry(ds: Dataset) -> dict[str, object]:
    """Extract geometry fields used by validation and conversion."""
    iop = [float(x) for x in ds.ImageOrientationPatient]
    ipp = [float(x) for x in ds.ImagePositionPatient]
    row_spacing, col_spacing = pixel_spacings(ds)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    return {
        "iop": iop,
        "ipp": ipp,
        "row_spacing": row_spacing,
        "col_spacing": col_spacing,
        "rows": int(ds.Rows),
        "cols": int(ds.Columns),
        "slope": slope,
        "intercept": intercept,
        "series_uid": str(ds.SeriesInstanceUID),
        "sop_uid": str(ds.SOPInstanceUID),
        "instance_number": int(getattr(ds, "InstanceNumber", 0)),
    }
