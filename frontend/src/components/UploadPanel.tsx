type UploadPanelProps = {
  busy: boolean
  onUpload: (file: File) => void
}

export function UploadPanel({ busy, onUpload }: UploadPanelProps) {
  return (
    <section className="panel upload-panel">
      <h2>Ingest CT series</h2>
      <p className="muted">
        Upload a ZIP of DICOM instances. The API validates spacing/orientation,
        converts to NIfTI, and serves axial slices.
      </p>
      <label className={`file-button ${busy ? 'disabled' : ''}`}>
        <input
          type="file"
          accept=".zip,application/zip"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) onUpload(file)
            e.target.value = ''
          }}
        />
        {busy ? 'Uploading…' : 'Choose DICOM ZIP'}
      </label>
      <p className="hint">
        Try <code>fixtures/dicom/good_series.zip</code> from the repo.
      </p>
    </section>
  )
}
