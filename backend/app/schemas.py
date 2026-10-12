"""API response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ValidationIssueOut(BaseModel):
    code: str
    message: str
    severity: str
    requirement_id: str | None = None


class StudySummary(BaseModel):
    id: str
    ok: bool
    slice_count: int
    series_uid: str | None = None
    spacing_mm: tuple[float, float, float] | None = None
    iop: list[float] | None = None
    origin_lps: list[float] | None = None
    shape_ijk: tuple[int, int, int] | None = None
    deidentified: bool = False
    nifti_ready: bool = False
    issues: list[ValidationIssueOut] = Field(default_factory=list)


class StudyCreateResponse(StudySummary):
    pass
