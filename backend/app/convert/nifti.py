"""Convert a validated CT series into a HU volume and NIfTI (.nii.gz)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import nibabel as nib
import numpy as np
from nibabel import Nifti1Image
from numpy.typing import NDArray
from pydicom.dataset import Dataset

from app.dicom.geometry import (
    affine_lps_to_ras,
    build_lps_affine,
    estimate_slice_spacing,
    hounsfield_units,
    pixel_spacings,
)
from app.dicom.validate import sort_by_position


@dataclass(frozen=True)
class ConversionResult:
    volume_hu: NDArray[np.float64]  # shape (i, j, k) = (cols, rows, slices)
    affine_lps: NDArray[np.float64]
    affine_ras: NDArray[np.float64]
    spacing_mm: tuple[float, float, float]  # row, col, slice
    iop: list[float]
    origin_lps: list[float]
    slope: float
    intercept: float


def series_to_volume(datasets: Sequence[Dataset]) -> ConversionResult:
    """Stack sorted DICOM slices into a HU volume with LPS/RAS affines."""
    if len(datasets) < 1:
        raise ValueError("Need at least one DICOM instance to convert")

    sorted_ds = sort_by_position(datasets)
    ref = sorted_ds[0]
    iop = [float(x) for x in ref.ImageOrientationPatient]
    origin = [float(x) for x in ref.ImagePositionPatient]
    row_spacing, col_spacing = pixel_spacings(ref)
    slope = float(getattr(ref, "RescaleSlope", 1.0))
    intercept = float(getattr(ref, "RescaleIntercept", 0.0))

    positions = [[float(x) for x in ds.ImagePositionPatient] for ds in sorted_ds]
    if len(sorted_ds) == 1:
        slice_spacing = float(getattr(ref, "SliceThickness", 1.0))
    else:
        slice_spacing = estimate_slice_spacing(positions, iop)

    # pixel_array is (rows, cols) = (j, i); stack then transpose to (i, j, k)
    slices_ji = []
    for ds in sorted_ds:
        stored = np.asarray(ds.pixel_array)
        hu = hounsfield_units(stored, slope=slope, intercept=intercept)
        slices_ji.append(hu)
    volume_jik = np.stack(slices_ji, axis=-1)
    volume_ijk = np.transpose(volume_jik, (1, 0, 2))

    affine_lps = build_lps_affine(iop, origin, row_spacing, col_spacing, slice_spacing)
    affine_ras = affine_lps_to_ras(affine_lps)

    return ConversionResult(
        volume_hu=volume_ijk,
        affine_lps=affine_lps,
        affine_ras=affine_ras,
        spacing_mm=(row_spacing, col_spacing, slice_spacing),
        iop=iop,
        origin_lps=origin,
        slope=slope,
        intercept=intercept,
    )


def series_to_nifti(datasets: Sequence[Dataset], output_path: Path | str) -> ConversionResult:
    """Convert series to NIfTI using the RAS affine (NIfTI convention)."""
    result = series_to_volume(datasets)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Nifti1Image(result.volume_hu.astype(np.float32), result.affine_ras)
    # Store LPS affine in a header extension-friendly descrip note for debugging
    img.header.set_xyzt_units("mm")
    nib.save(img, str(output_path))
    return result


def axial_slice_hu(volume_ijk: NDArray[np.floating], z: int) -> NDArray[np.float64]:
    """Return axial slice at index z as (rows, cols) for display."""
    if z < 0 or z >= volume_ijk.shape[2]:
        raise IndexError(f"Slice index {z} out of range 0..{volume_ijk.shape[2] - 1}")
    # volume is (i, j, k) → display (j, i) = (rows, cols)
    return np.asarray(volume_ijk[:, :, z].T, dtype=np.float64)
