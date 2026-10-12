"""Filesystem-backed study store under backend/data/."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


@dataclass
class StudyRecord:
    id: str
    ok: bool
    slice_count: int
    series_uid: str | None
    spacing_mm: tuple[float, float, float] | None
    iop: list[float] | None
    origin_lps: list[float] | None
    shape_ijk: tuple[int, int, int] | None
    deidentified: bool
    nifti_ready: bool
    issues: list[dict]
    directory: Path

    @property
    def nifti_path(self) -> Path:
        return self.directory / "volume.nii.gz"

    @property
    def volume_path(self) -> Path:
        return self.directory / "volume_hu.npy"

    def load_volume(self) -> NDArray[np.float64]:
        return np.load(self.volume_path)


class StudyStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else DATA_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def new_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def study_dir(self, study_id: str) -> Path:
        return self.root / study_id

    def save(
        self,
        *,
        study_id: str,
        ok: bool,
        slice_count: int,
        series_uid: str | None,
        spacing_mm: tuple[float, float, float] | None,
        iop: list[float] | None,
        origin_lps: list[float] | None,
        shape_ijk: tuple[int, int, int] | None,
        deidentified: bool,
        nifti_ready: bool,
        issues: list[dict],
        volume: NDArray[np.floating] | None = None,
    ) -> StudyRecord:
        directory = self.study_dir(study_id)
        directory.mkdir(parents=True, exist_ok=True)
        meta = {
            "id": study_id,
            "ok": ok,
            "slice_count": slice_count,
            "series_uid": series_uid,
            "spacing_mm": list(spacing_mm) if spacing_mm else None,
            "iop": iop,
            "origin_lps": origin_lps,
            "shape_ijk": list(shape_ijk) if shape_ijk else None,
            "deidentified": deidentified,
            "nifti_ready": nifti_ready,
            "issues": issues,
        }
        (directory / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        if volume is not None:
            np.save(directory / "volume_hu.npy", np.asarray(volume, dtype=np.float64))
        return self.get(study_id)

    def get(self, study_id: str) -> StudyRecord:
        directory = self.study_dir(study_id)
        meta_path = directory / "meta.json"
        if not meta_path.exists():
            raise KeyError(study_id)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        spacing = meta.get("spacing_mm")
        shape = meta.get("shape_ijk")
        return StudyRecord(
            id=meta["id"],
            ok=meta["ok"],
            slice_count=meta["slice_count"],
            series_uid=meta.get("series_uid"),
            spacing_mm=tuple(spacing) if spacing else None,
            iop=meta.get("iop"),
            origin_lps=meta.get("origin_lps"),
            shape_ijk=tuple(shape) if shape else None,
            deidentified=meta.get("deidentified", False),
            nifti_ready=meta.get("nifti_ready", False),
            issues=meta.get("issues", []),
            directory=directory,
        )

    def delete(self, study_id: str) -> None:
        directory = self.study_dir(study_id)
        if directory.exists():
            shutil.rmtree(directory)


store = StudyStore()
