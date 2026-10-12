"""REQ-VAL-*: series integrity validation on synthetic fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.dicom.validate import load_dicom_directory, validate_series

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "dicom"


@pytest.mark.req_val
def test_good_series_passes() -> None:
    datasets = load_dicom_directory(FIXTURES / "good_series")
    report = validate_series(datasets)
    assert report.ok is True
    assert report.slice_count == 8
    assert report.spacing_mm is not None
    assert report.spacing_mm[0] == pytest.approx(1.0)
    assert report.spacing_mm[1] == pytest.approx(1.0)
    assert report.spacing_mm[2] == pytest.approx(2.0)
    error_codes = {i.code for i in report.issues if i.severity.value == "error"}
    assert error_codes == set()


@pytest.mark.req_val
def test_missing_slice_detected() -> None:
    datasets = load_dicom_directory(FIXTURES / "missing_slice")
    report = validate_series(datasets)
    assert report.ok is False
    codes = {i.code for i in report.issues}
    assert "MISSING_SLICE_GAP" in codes
    assert any(i.requirement_id == "REQ-VAL-004" for i in report.issues)


@pytest.mark.req_val
def test_mixed_series_detected() -> None:
    datasets = load_dicom_directory(FIXTURES / "mixed_series")
    report = validate_series(datasets)
    assert report.ok is False
    codes = {i.code for i in report.issues}
    assert "MIXED_SERIES" in codes
    assert any(i.requirement_id == "REQ-VAL-001" for i in report.issues)


@pytest.mark.req_val
def test_empty_series_fails() -> None:
    report = validate_series([])
    assert report.ok is False
    assert report.issues[0].code == "EMPTY"
