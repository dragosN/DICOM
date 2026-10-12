"""Light tag de-identification."""

from __future__ import annotations

from pathlib import Path

from app.deid import deidentify_datasets
from app.dicom.validate import load_dicom_directory

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "dicom"


def test_deidentify_blanks_patient_tags() -> None:
    datasets = load_dicom_directory(FIXTURES / "good_series")
    assert str(datasets[0].PatientName) != ""
    deidentify_datasets(datasets)
    for ds in datasets:
        assert str(ds.PatientName).strip() in {"", "Anonymous"}
        assert str(ds.PatientID).strip() == ""
