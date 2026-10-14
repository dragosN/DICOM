#!/usr/bin/env python3
"""Download a public CT series from The Cancer Imaging Archive (TCIA / NBIA).

Default: smallest-ish series from CC-Radiomics-Phantom (CC-BY 3.0).
Produces:
  fixtures/dicom/tcia_sample/          — extracted DICOM instances
  fixtures/dicom/tcia_sample.zip       — uploadable ZIP for the viewer
  fixtures/dicom/tcia_sample_meta.json — provenance for the README / interviews

Usage:
  cd backend && uv run python ../scripts/download_tcia_sample.py
  uv run python ../scripts/download_tcia_sample.py --max-slices 48
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "fixtures" / "dicom" / "tcia_sample"
OUT_ZIP = ROOT / "fixtures" / "dicom" / "tcia_sample.zip"
OUT_META = ROOT / "fixtures" / "dicom" / "tcia_sample_meta.json"

NBIA = "https://services.cancerimagingarchive.net/nbia-api/services/v1"

# Philips Brilliance phantom CT — ~123 slices, CC-BY 3.0 via TCIA
DEFAULT_SERIES_UID = "1.3.6.1.4.1.14519.5.2.1.4020.5263.137125892409456229662234563386"
DEFAULT_COLLECTION = "CC-Radiomics-Phantom"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "dicom-portfolio/0.1"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def download_series(series_uid: str, dest_zip: Path) -> None:
    url = f"{NBIA}/getImage?SeriesInstanceUID={series_uid}"
    print(f"Downloading {url}")
    print("(TCIA ZIPs are often 50–100MB — this can take a few minutes)")
    data = _get(url)
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    dest_zip.write_bytes(data)
    print(f"Wrote {dest_zip} ({len(data) / 1e6:.1f} MB)")


def _sort_key_dicom(path: Path) -> tuple[float, str]:
    """Sort by ImagePositionPatient along Z when possible (pydicom optional at download time)."""
    try:
        import pydicom

        ds = pydicom.dcmread(path, stop_before_pixels=True, force=True)
        if hasattr(ds, "ImagePositionPatient"):
            # Axial stacks: use superior coordinate; fall back to instance number
            z = float(ds.ImagePositionPatient[2])
            return (z, path.name)
        if hasattr(ds, "InstanceNumber"):
            return (float(ds.InstanceNumber), path.name)
    except Exception:
        pass
    return (0.0, path.name)


def extract_and_thin(src_zip: Path, out_dir: Path, max_slices: int | None) -> list[Path]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="tcia_") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(src_zip, "r") as zf:
            zf.extractall(tmp_path)

        dicoms = [
            p
            for p in tmp_path.rglob("*")
            if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in {"", ".dcm"}
        ]
        # NBIA often ships extensionless DICOM files
        if not dicoms:
            dicoms = [p for p in tmp_path.rglob("*") if p.is_file() and not p.name.startswith(".")]

        dicoms = sorted(dicoms, key=_sort_key_dicom)

        if max_slices and len(dicoms) > max_slices:
            # Contiguous mid-stack window keeps spacing valid (no artificial gaps)
            start = max(0, (len(dicoms) - max_slices) // 2)
            chosen = dicoms[start : start + max_slices]
            print(f"Keeping mid-stack window {len(chosen)}/{len(dicoms)} slices (IPP-sorted)")
            dicoms = chosen
        else:
            print(f"Keeping all {len(dicoms)} files (IPP-sorted)")

        written: list[Path] = []
        for i, src in enumerate(dicoms, start=1):
            dest = out_dir / f"CT_{i:04d}.dcm"
            shutil.copy2(src, dest)
            written.append(dest)
        return written


def write_upload_zip(files: list[Path], zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, arcname=path.name)
    print(f"Wrote upload zip → {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series-uid", default=DEFAULT_SERIES_UID)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument(
        "--max-slices",
        type=int,
        default=48,
        help="Evenly subsample to this many slices (0 = keep all). Default 48 for demo speed.",
    )
    parser.add_argument(
        "--raw-zip",
        type=Path,
        default=ROOT / "fixtures" / "dicom" / "tcia_sample_raw.zip",
        help="Cache path for the full NBIA ZIP",
    )
    args = parser.parse_args()
    max_slices = None if args.max_slices == 0 else args.max_slices

    if not args.raw_zip.exists():
        download_series(args.series_uid, args.raw_zip)
    else:
        print(f"Using cached raw zip: {args.raw_zip}")

    files = extract_and_thin(args.raw_zip, OUT_DIR, max_slices)
    if not files:
        print("No DICOM files found in archive", file=sys.stderr)
        return 1

    write_upload_zip(files, OUT_ZIP)
    meta = {
        "source": "TCIA / NBIA",
        "collection": args.collection,
        "series_instance_uid": args.series_uid,
        "license": "CC BY 3.0",
        "license_uri": "https://creativecommons.org/licenses/by/3.0/",
        "collection_doi": "https://doi.org/10.7937/K9/TCIA.2017.zuzrml5b",
        "slice_count": len(files),
        "max_slices_option": args.max_slices,
        "paths": {
            "directory": str(OUT_DIR.relative_to(ROOT)),
            "zip": str(OUT_ZIP.relative_to(ROOT)),
            "raw_zip": str(args.raw_zip.relative_to(ROOT)),
        },
    }
    OUT_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_META}")
    print("Upload fixtures/dicom/tcia_sample.zip in the viewer, or POST /studies/demo/tcia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
