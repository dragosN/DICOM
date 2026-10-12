"""REQ-GEO-*: DICOM → NIfTI round-trip preserves spacing, orientation, HU."""

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from app.convert.nifti import series_to_nifti, series_to_volume
from app.dicom.geometry import affine_lps_to_ras, build_lps_affine
from app.dicom.validate import load_dicom_directory

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "dicom"
EXPECTED = json.loads((FIXTURES / "good_series_expected.json").read_text(encoding="utf-8"))


@pytest.mark.req_geo
def test_series_to_volume_shape_and_hu(tmp_path: Path) -> None:
    datasets = load_dicom_directory(FIXTURES / "good_series")
    result = series_to_volume(datasets)
    assert result.volume_hu.shape == (
        EXPECTED["cols"],
        EXPECTED["rows"],
        EXPECTED["num_slices"],
    )
    assert result.spacing_mm == pytest.approx(
        (
            EXPECTED["pixel_spacing"][0],
            EXPECTED["pixel_spacing"][1],
            EXPECTED["slice_spacing"],
        )
    )
    # Center voxel of middle slice should be bone HU
    mid = EXPECTED["num_slices"] // 2
    cx, cy = EXPECTED["cols"] // 2, EXPECTED["rows"] // 2
    assert result.volume_hu[cx, cy, mid] == pytest.approx(EXPECTED["bone_hu"])
    # Corner should be air
    assert result.volume_hu[0, 0, mid] == pytest.approx(EXPECTED["air_hu"])


@pytest.mark.req_geo
def test_nifti_affine_is_ras_and_matches_geometry(tmp_path: Path) -> None:
    datasets = load_dicom_directory(FIXTURES / "good_series")
    out = tmp_path / "volume.nii.gz"
    result = series_to_nifti(datasets, out)

    expected_lps = build_lps_affine(
        EXPECTED["iop"],
        EXPECTED["origin_lps"],
        row_spacing=EXPECTED["pixel_spacing"][0],
        col_spacing=EXPECTED["pixel_spacing"][1],
        slice_spacing=EXPECTED["slice_spacing"],
    )
    expected_ras = affine_lps_to_ras(expected_lps)
    np.testing.assert_allclose(result.affine_lps, expected_lps, atol=1e-6)
    np.testing.assert_allclose(result.affine_ras, expected_ras, atol=1e-6)

    img = nib.load(str(out))
    np.testing.assert_allclose(img.affine, expected_ras, atol=1e-5)
    data = np.asanyarray(img.dataobj)
    assert data.shape == result.volume_hu.shape
    np.testing.assert_allclose(data, result.volume_hu, atol=1e-3)


@pytest.mark.req_geo
def test_wrong_orientation_affine_would_fail_check() -> None:
    """Interview talking point: flipping IOP breaks the RAS affine equality."""
    datasets = load_dicom_directory(FIXTURES / "good_series")
    result = series_to_volume(datasets)
    # Corrupt IOP as if someone swapped row/col directions
    bad_iop = [0.0, 1.0, 0.0, 1.0, 0.0, 0.0]
    bad_lps = build_lps_affine(
        bad_iop,
        result.origin_lps,
        row_spacing=result.spacing_mm[0],
        col_spacing=result.spacing_mm[1],
        slice_spacing=result.spacing_mm[2],
    )
    assert not np.allclose(affine_lps_to_ras(bad_lps), result.affine_ras, atol=1e-3)
