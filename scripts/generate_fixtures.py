#!/usr/bin/env python3
"""Generate synthetic CT DICOM fixtures for offline demos and tests.

Creates:
  fixtures/dicom/good_series/     — consistent 8-slice axial stack
  fixtures/dicom/missing_slice/   — same stack with one middle slice removed
  fixtures/dicom/mixed_series/    — two SeriesInstanceUID values mixed together
  fixtures/dicom/good_series.zip  — zipped good series for upload demos

Geometry (known ground truth for tests):
  IOP = [1, 0, 0, 0, 1, 0]  (axial, LPS)
  IPP origin = [-8, -8, 0], slice step 2.0 mm along +Z
  PixelSpacing = [1.0, 1.0] mm, 16x16 pixels
  RescaleSlope=1, RescaleIntercept=-1024
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import (
    ExplicitVRLittleEndian,
    CTImageStorage,
    generate_uid,
    PYDICOM_IMPLEMENTATION_UID,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "dicom"

ROWS = 16
COLS = 16
NUM_SLICES = 8
PIXEL_SPACING = (1.0, 1.0)  # row, col
SLICE_SPACING = 2.0
IOP = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
ORIGIN = np.array([-8.0, -8.0, 0.0], dtype=np.float64)
SLOPE = 1.0
INTERCEPT = -1024.0


def _file_meta() -> FileMetaDataset:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    return meta


def make_slice(
    *,
    instance_number: int,
    z_index: int,
    series_uid: str,
    study_uid: str,
    frame_uid: str,
    patient_name: str = "Fixture^CT",
    patient_id: str = "FIX-001",
) -> FileDataset:
    meta = _file_meta()
    sop_uid = meta.MediaStorageSOPInstanceUID
    ds = FileDataset(
        f"CT_{instance_number:03d}.dcm",
        {},
        file_meta=meta,
        preamble=b"\0" * 128,
    )
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = sop_uid
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.FrameOfReferenceUID = frame_uid

    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = "19700101"
    ds.PatientSex = "O"
    ds.StudyDate = "20240101"
    ds.StudyTime = "120000"
    ds.Modality = "CT"
    ds.SeriesNumber = 1
    ds.InstanceNumber = instance_number
    ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]

    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = ROWS
    ds.Columns = COLS
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1  # signed
    ds.RescaleIntercept = INTERCEPT
    ds.RescaleSlope = SLOPE
    ds.WindowCenter = 40
    ds.WindowWidth = 400

    ds.ImageOrientationPatient = IOP
    ipp = ORIGIN + np.array([0.0, 0.0, z_index * SLICE_SPACING])
    ds.ImagePositionPatient = [float(x) for x in ipp]
    ds.PixelSpacing = list(PIXEL_SPACING)
    ds.SliceThickness = SLICE_SPACING
    ds.SpacingBetweenSlices = SLICE_SPACING

    # Synthetic intensity: brighter "bone" disk near center, air elsewhere.
    yy, xx = np.mgrid[0:ROWS, 0:COLS]
    cy, cx = (ROWS - 1) / 2.0, (COLS - 1) / 2.0
    radius = 4.0 + 0.3 * z_index
    disk = ((xx - cx) ** 2 + (yy - cy) ** 2) <= radius**2
    # Stored values such that HU = stored * slope + intercept
    # Air HU ≈ -1000 → stored ≈ 24; bone HU ≈ 400 → stored ≈ 1424
    pixels = np.full((ROWS, COLS), 24, dtype=np.int16)
    pixels[disk] = 1424
    ds.PixelData = pixels.tobytes()
    return ds


def write_series(directory: Path, datasets: list[FileDataset]) -> None:
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    for ds in datasets:
        path = directory / f"CT_{int(ds.InstanceNumber):03d}.dcm"
        ds.save_as(path, write_like_original=False)


def build_good_series() -> list[FileDataset]:
    study_uid = generate_uid()
    series_uid = generate_uid()
    frame_uid = generate_uid()
    return [
        make_slice(
            instance_number=i + 1,
            z_index=i,
            series_uid=series_uid,
            study_uid=study_uid,
            frame_uid=frame_uid,
        )
        for i in range(NUM_SLICES)
    ]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    good = build_good_series()
    good_dir = OUT / "good_series"
    write_series(good_dir, good)
    print(f"Wrote {len(good)} slices → {good_dir}")

    # Geometric gap: skip z_index 3 (between instance 3 and 5)
    study_uid = generate_uid()
    series_uid = generate_uid()
    frame_uid = generate_uid()
    missing_datasets = [
        make_slice(
            instance_number=n,
            z_index=z,
            series_uid=series_uid,
            study_uid=study_uid,
            frame_uid=frame_uid,
        )
        for n, z in zip([1, 2, 3, 5, 6, 7, 8], [0, 1, 2, 4, 5, 6, 7], strict=True)
    ]
    missing_dir = OUT / "missing_slice"
    write_series(missing_dir, missing_datasets)
    print(f"Wrote {len(missing_datasets)} slices (gap) → {missing_dir}")

    # Mixed series: good series + one slice with different SeriesInstanceUID
    mixed_study = generate_uid()
    series_a = generate_uid()
    series_b = generate_uid()
    frame_uid = generate_uid()
    mixed = [
        make_slice(
            instance_number=i + 1,
            z_index=i,
            series_uid=series_a if i < NUM_SLICES - 1 else series_b,
            study_uid=mixed_study,
            frame_uid=frame_uid,
        )
        for i in range(NUM_SLICES)
    ]
    mixed_dir = OUT / "mixed_series"
    write_series(mixed_dir, mixed)
    print(f"Wrote {len(mixed)} slices (mixed series) → {mixed_dir}")

    zip_path = OUT / "good_series.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(good_dir.glob("*.dcm")):
            zf.write(path, arcname=path.name)
    print(f"Wrote zip → {zip_path}")

    # Ground-truth sidecar for geometry tests
    meta_path = OUT / "good_series_expected.json"
    meta_path.write_text(
        "{\n"
        f'  "rows": {ROWS},\n'
        f'  "cols": {COLS},\n'
        f'  "num_slices": {NUM_SLICES},\n'
        f'  "pixel_spacing": [{PIXEL_SPACING[0]}, {PIXEL_SPACING[1]}],\n'
        f'  "slice_spacing": {SLICE_SPACING},\n'
        f'  "iop": {IOP},\n'
        f'  "origin_lps": {ORIGIN.tolist()},\n'
        f'  "slope": {SLOPE},\n'
        f'  "intercept": {INTERCEPT},\n'
        f'  "bone_hu": {1424 * SLOPE + INTERCEPT},\n'
        f'  "air_hu": {24 * SLOPE + INTERCEPT}\n'
        "}\n",
        encoding="utf-8",
    )
    print(f"Wrote expected metadata → {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
