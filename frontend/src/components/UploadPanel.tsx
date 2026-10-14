import type { DemoSample } from '../api/studies'

type UploadPanelProps = {
  busy: boolean
  onUpload: (file: File) => void
  onLoadDemo: (sample: DemoSample) => void
}

export function UploadPanel({ busy, onUpload, onLoadDemo }: UploadPanelProps) {
  return (
    <section className="panel upload-panel">
      <h2>Ingest CT series</h2>
      <p className="muted">
        Load a real TCIA phantom CT, the tiny synthetic fixture, or upload your
        own DICOM ZIP.
      </p>

      <div className="wl-presets" style={{ marginTop: '0.5rem' }}>
        <button
          type="button"
          disabled={busy}
          onClick={() => onLoadDemo('tcia')}
        >
          {busy ? 'Loading…' : 'Load TCIA sample'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onLoadDemo('synthetic')}
        >
          Load synthetic
        </button>
      </div>

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
        {busy ? 'Working…' : 'Choose DICOM ZIP'}
      </label>
      <p className="hint">
        TCIA sample requires{' '}
        <code>uv run python ../scripts/download_tcia_sample.py</code> once
        (CC-Radiomics-Phantom, CC BY 3.0).
      </p>
    </section>
  )
}
