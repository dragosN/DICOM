# Requirements (lightweight)

**Intended use:** Educational / interview portfolio demonstration of DICOM geometry validation and visualization. **Not** Software as a Medical Device (SaMD). Not for diagnosis, treatment, or clinical decision-making.

| ID | Statement | Priority |
|----|-----------|----------|
| REQ-GEO-001 | System shall derive patient-frame geometry (IOP, IPP, PixelSpacing) required for conversion. | Must |
| REQ-GEO-002 | System shall build an LPS voxel→patient affine and convert explicitly to RAS for NIfTI. | Must |
| REQ-GEO-003 | System shall apply RescaleSlope/RescaleIntercept to produce Hounsfield units when present. | Must |
| REQ-GEO-004 | Round-trip DICOM→NIfTI shall preserve spacing and orientation within test tolerances. | Must |
| REQ-VAL-001 | System shall reject or flag uploads containing mixed `SeriesInstanceUID` values. | Must |
| REQ-VAL-002 | System shall flag inconsistent PixelSpacing / Rows / Columns within a series. | Must |
| REQ-VAL-003 | System shall flag inconsistent `ImageOrientationPatient` within a series. | Must |
| REQ-VAL-004 | System shall detect missing-slice gaps along the stack normal. | Must |
| REQ-DEID-001 | When de-identify mode is enabled, PatientName/PatientID (and listed PHI tags) shall be blanked on ingest. | Should |
| REQ-VIEW-001 | Viewer shall display axial slices with adjustable window center/width. | Should |
| REQ-VIEW-002 | Viewer shall load a mesh, support orbit, clipping, and a two-point distance measurement. | Should |
| REQ-VIEW-003 | Measurement readout shall state that mesh units are not patient-space mm unless co-registered. | Should |
