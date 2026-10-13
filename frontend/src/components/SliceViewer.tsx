import { useEffect, useState } from 'react'
import { sliceUrl } from '../api/studies'
import type { StudySummary } from '../types'

type SliceViewerProps = {
  study: StudySummary
}

export function SliceViewer({ study }: SliceViewerProps) {
  const maxZ = Math.max(0, (study.shape_ijk?.[2] ?? study.slice_count) - 1)
  const [z, setZ] = useState(() => Math.floor(maxZ / 2))
  const [center, setCenter] = useState(40)
  const [width, setWidth] = useState(400)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setZ(Math.floor(maxZ / 2))
    setLoading(true)
    setError(null)
  }, [study.id, maxZ])

  const url = study.nifti_ready
    ? sliceUrl(study.id, z, center, width)
    : null

  return (
    <section className="panel slice-panel">
      <div className="panel-header">
        <h2>Axial slice</h2>
        <span className="muted mono">
          z={z}/{maxZ} · WL {center}/{width}
        </span>
      </div>

      {!study.nifti_ready && (
        <p className="warn-text">
          Volume not available — fix validation errors and re-upload.
        </p>
      )}

      {url && (
        <div className="slice-stage">
          {loading && <div className="slice-loading">Loading slice…</div>}
          {error && <div className="warn-text">{error}</div>}
          <img
            key={url}
            src={url}
            alt={`Axial slice ${z}`}
            className="slice-image"
            onLoad={() => {
              setLoading(false)
              setError(null)
            }}
            onError={() => {
              setLoading(false)
              setError('Failed to load slice image')
            }}
            onLoadStart={() => setLoading(true)}
          />
        </div>
      )}

      <div className="controls">
        <label>
          <span>Slice index</span>
          <input
            type="range"
            min={0}
            max={maxZ}
            value={Math.min(z, maxZ)}
            disabled={!study.nifti_ready}
            onChange={(e) => setZ(Number(e.target.value))}
          />
        </label>
        <label>
          <span>Window center (HU)</span>
          <input
            type="range"
            min={-1000}
            max={1000}
            step={1}
            value={center}
            disabled={!study.nifti_ready}
            onChange={(e) => setCenter(Number(e.target.value))}
          />
        </label>
        <label>
          <span>Window width (HU)</span>
          <input
            type="range"
            min={1}
            max={2000}
            step={1}
            value={width}
            disabled={!study.nifti_ready}
            onChange={(e) => setWidth(Number(e.target.value))}
          />
        </label>
        <div className="wl-presets">
          <button
            type="button"
            disabled={!study.nifti_ready}
            onClick={() => {
              setCenter(40)
              setWidth(400)
            }}
          >
            Soft tissue
          </button>
          <button
            type="button"
            disabled={!study.nifti_ready}
            onClick={() => {
              setCenter(400)
              setWidth(1500)
            }}
          >
            Bone
          </button>
          <button
            type="button"
            disabled={!study.nifti_ready}
            onClick={() => {
              setCenter(-600)
              setWidth(1500)
            }}
          >
            Lung
          </button>
        </div>
      </div>
    </section>
  )
}
