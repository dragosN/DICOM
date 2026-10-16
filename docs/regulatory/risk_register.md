# Risk register (ISO 14971–style, portfolio)

**Context:** Demo software only. Risks below are framed as if this were clinical tooling, to show hazard analysis habits—not because the product is intended for clinical use.

| ID | Hazard | Cause | Harm (hypothetical) | Severity | Probability | Risk | Mitigation | Residual |
|----|--------|-------|---------------------|----------|-------------|------|------------|----------|
| R-01 | Wrong laterality / flipped anatomy | LPS↔RAS sign error | Mis-side procedure planning | Critical | Medium (if untested) | High | Explicit LPS→RAS helper; unit tests on affine signs / round-trip | Low |
| R-02 | Wrong scale (mm) | PixelSpacing / spacing axis mistake | Incorrect distance / implant size | Critical | Medium | High | Spacing from DICOM tags; NIfTI header check in tests; UI disclaimer on mesh mm | Medium |
| R-03 | Partial / wrong series | Mixed SeriesInstanceUID or gaps | Incomplete volume, false anatomy | Serious | Medium | High | Validation flags; reject mixed series; gap detection | Low |
| R-04 | PHI exposure | Unredacted DICOM tags | Privacy breach | Serious | Medium | High | Optional de-identify on ingest; demo fixtures use synthetic/TCIA-cleared data | Low |
| R-05 | Misinterpreted demo as clinical | Marketing / UI ambiguity | Inappropriate clinical use | Critical | Low | Medium | Intended-use statement in README + API root; “not for diagnosis” | Low |
| R-06 | Window/level misread | Extreme WC/WW defaults | Missed soft-tissue contrast (demo) | Minor | Medium | Low | User-adjustable WC/WW; sensible CT bone preset | Low |

**Risk acceptance:** For this portfolio demo, residual risks R-01–R-05 are accepted only because intended use excludes clinical decisions. Any productization would require full SaMD QMS, clinical evaluation, and IEC 62304 Class B/C process.
