"""Lightweight DICOM tag de-identification (PHI in tags only).

Burned-in pixel PHI is out of scope for v1 — documented as a known gap.
"""

from __future__ import annotations

from typing import Sequence

from pydicom.dataset import Dataset

# Common direct identifiers — blanked on ingest when deid_mode is enabled.
PHI_TAGS = (
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "OtherPatientIDs",
    "OtherPatientNames",
    "PatientAddress",
    "PatientTelephoneNumbers",
)


def deidentify_datasets(datasets: Sequence[Dataset]) -> None:
    """Blank selected PHI tags in-place."""
    for ds in datasets:
        for tag in PHI_TAGS:
            if hasattr(ds, tag):
                try:
                    setattr(ds, tag, "")
                except Exception:
                    # Some tags may be type-constrained; skip quietly.
                    pass
        if hasattr(ds, "PatientIdentityRemoved"):
            ds.PatientIdentityRemoved = "YES"
