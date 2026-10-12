"""Volume conversion (DICOM series → NIfTI)."""

from app.convert.nifti import ConversionResult, series_to_nifti, series_to_volume

__all__ = ["ConversionResult", "series_to_nifti", "series_to_volume"]
