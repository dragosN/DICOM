"""REQ-GEO-*: LPS affine, RAS conversion, HU rescale."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.dicom.geometry import (
    LPS_TO_RAS,
    affine_lps_to_ras,
    build_lps_affine,
    direction_cosine_matrix,
    estimate_slice_spacing,
    hounsfield_units,
    slice_normal,
)
from app.dicom.validate import load_dicom_directory, sort_by_position

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "dicom"
EXPECTED = json.loads((FIXTURES / "good_series_expected.json").read_text(encoding="utf-8"))


@pytest.mark.req_geo
def test_axial_iop_normal_is_plus_z() -> None:
    iop = EXPECTED["iop"]
    normal = slice_normal(iop)
    np.testing.assert_allclose(normal, [0.0, 0.0, 1.0], atol=1e-8)


@pytest.mark.req_geo
def test_direction_matrix_orthonormal() -> None:
    matrix = direction_cosine_matrix(EXPECTED["iop"])
    np.testing.assert_allclose(matrix.T @ matrix, np.eye(3), atol=1e-8)


@pytest.mark.req_geo
def test_build_lps_affine_maps_voxel_origin_to_ipp() -> None:
    affine = build_lps_affine(
        EXPECTED["iop"],
        EXPECTED["origin_lps"],
        row_spacing=EXPECTED["pixel_spacing"][0],
        col_spacing=EXPECTED["pixel_spacing"][1],
        slice_spacing=EXPECTED["slice_spacing"],
    )
    origin = affine @ np.array([0.0, 0.0, 0.0, 1.0])
    np.testing.assert_allclose(origin[:3], EXPECTED["origin_lps"], atol=1e-8)

    # One step in +i (column) should move +1 mm in +X (LPS left)
    neighbor = affine @ np.array([1.0, 0.0, 0.0, 1.0])
    np.testing.assert_allclose(
        neighbor[:3],
        np.asarray(EXPECTED["origin_lps"]) + np.array([1.0, 0.0, 0.0]),
        atol=1e-8,
    )

    # One step in +k (slice) should move +slice_spacing along +Z
    next_slice = affine @ np.array([0.0, 0.0, 1.0, 1.0])
    np.testing.assert_allclose(
        next_slice[:3],
        np.asarray(EXPECTED["origin_lps"]) + np.array([0.0, 0.0, EXPECTED["slice_spacing"]]),
        atol=1e-8,
    )


@pytest.mark.req_geo
def test_lps_to_ras_flips_x_and_y() -> None:
    affine_lps = build_lps_affine(
        EXPECTED["iop"],
        EXPECTED["origin_lps"],
        row_spacing=1.0,
        col_spacing=1.0,
        slice_spacing=2.0,
    )
    affine_ras = affine_lps_to_ras(affine_lps)
    point_lps = affine_lps @ np.array([2.0, 3.0, 1.0, 1.0])
    point_ras = affine_ras @ np.array([2.0, 3.0, 1.0, 1.0])
    np.testing.assert_allclose(
        point_ras[:3],
        [-point_lps[0], -point_lps[1], point_lps[2]],
        atol=1e-8,
    )
    np.testing.assert_allclose(LPS_TO_RAS @ point_lps, point_ras, atol=1e-8)


@pytest.mark.req_geo
def test_hounsfield_units_from_fixture_values() -> None:
    stored = np.array([24, 1424], dtype=np.int16)
    hu = hounsfield_units(stored, slope=EXPECTED["slope"], intercept=EXPECTED["intercept"])
    np.testing.assert_allclose(hu, [EXPECTED["air_hu"], EXPECTED["bone_hu"]])


@pytest.mark.req_geo
def test_fixture_slice_spacing_matches_expected() -> None:
    datasets = load_dicom_directory(FIXTURES / "good_series")
    assert len(datasets) == EXPECTED["num_slices"]
    sorted_ds = sort_by_position(datasets)
    positions = [[float(x) for x in ds.ImagePositionPatient] for ds in sorted_ds]
    spacing = estimate_slice_spacing(positions, EXPECTED["iop"])
    assert spacing == pytest.approx(EXPECTED["slice_spacing"])
