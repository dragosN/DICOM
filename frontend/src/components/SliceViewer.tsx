import { useEffect, useRef, useState } from 'react'
import { sliceUrl } from '../api/studies'
import { FullscreenButton } from './FullscreenButton'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { usePanelFullscreen } from '../hooks/usePanelFullscreen'
import type { StudySummary } from '../types'

type SliceViewerProps = {
  study: StudySummary
}

export function SliceViewer({ study }: SliceViewerProps) {
  const maxZ = Math.max(0, (study.shape_ijk?.[2] ?? study.slice_count) - 1)

  // Slider UI updates immediately; image fetch uses debounced values.
  const [z, setZ] = useState(() => Math.floor(maxZ / 2))
  const [center, setCenter] = useState(40)
  const [width, setWidth] = useState(400)

  const debouncedZ = useDebouncedValue(z, 80)
  const debouncedCenter = useDebouncedValue(center, 120)
  const debouncedWidth = useDebouncedValue(width, 120)

  const [src, setSrc] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)
  const { active: fullscreen, toggle: toggleFullscreen } = usePanelFullscreen()

  useEffect(() => {
    setZ(Math.floor(maxZ / 2))
    setError(null)
  }, [study.id, maxZ])

  useEffect(() => {
    if (!study.nifti_ready) {
      setSrc(null)
      return
    }

    const nextUrl = sliceUrl(
      study.id,
      debouncedZ,
      debouncedCenter,
      debouncedWidth,
    )
    const id = ++requestId.current
    setBusy(true)

    const preloader = new Image()
    preloader.onload = () => {
      if (id !== requestId.current) return
      setSrc(nextUrl)
      setBusy(false)
      setError(null)
    }
    preloader.onerror = () => {
      if (id !== requestId.current) return
      setBusy(false)
      setError('Failed to load slice image')
    }
    preloader.src = nextUrl

    return () => {
      preloader.onload = null
      preloader.onerror = null
    }
  }, [study.id, study.nifti_ready, debouncedZ, debouncedCenter, debouncedWidth])

  const isTiny =
    !!study.shape_ijk &&
    Math.max(study.shape_ijk[0], study.shape_ijk[1]) <= 64

  return (
    <section className={`panel slice-panel${fullscreen ? ' is-fullscreen' : ''}`}>
      <div className="panel-header">
        <h2>Axial slice</h2>
        <div className="panel-header-actions">
          <span className="muted mono">
            z={z}/{maxZ} · WL {center}/{width}
            {busy ? ' · …' : ''}
          </span>
          <FullscreenButton active={fullscreen} onToggle={toggleFullscreen} />
        </div>
      </div>

      {!study.nifti_ready && (
        <p className="warn-text">
          Volume not available — fix validation errors and re-upload.
        </p>
      )}

      {study.nifti_ready && (
        <div className={`slice-stage${busy ? ' is-busy' : ''}`}>
          {error && <div className="warn-text">{error}</div>}
          {src ? (
            <img
              src={src}
              alt={`Axial slice ${debouncedZ}`}
              className={`slice-image${isTiny ? ' is-synthetic' : ''}`}
              draggable={false}
            />
          ) : (
            <div className="slice-loading">Loading slice…</div>
          )}
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
