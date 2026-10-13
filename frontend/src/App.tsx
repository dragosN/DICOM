import { useState } from 'react'
import { uploadStudy } from './api/studies'
import { SliceViewer } from './components/SliceViewer'
import { StudyMeta } from './components/StudyMeta'
import { UploadPanel } from './components/UploadPanel'
import { ValidationIssues } from './components/ValidationIssues'
import type { StudySummary } from './types'

export default function App() {
  const [study, setStudy] = useState<StudySummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload(file: File) {
    setBusy(true)
    setError(null)
    try {
      const result = await uploadStudy(file, true)
      setStudy(result)
    } catch (err) {
      setStudy(null)
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="brand">DICOM Portfolio</p>
          <h1>CT series viewer</h1>
        </div>
        <p className="header-note">
          Day 2 — upload, validate geometry, window/level axial slices.
          Mesh viewer comes next.
        </p>
      </header>

      <main className="layout">
        <aside className="sidebar">
          <UploadPanel busy={busy} onUpload={handleUpload} />
          {error && <p className="error-banner">{error}</p>}
          {study && (
            <>
              <StudyMeta study={study} />
              <ValidationIssues issues={study.issues} />
            </>
          )}
        </aside>

        <div className="main-stage">
          {study ? (
            <SliceViewer study={study} />
          ) : (
            <section className="panel empty-stage">
              <h2>No study loaded</h2>
              <p className="muted">
                Upload <code>good_series.zip</code> with the API running on
                port 8000. Vite proxies <code>/api</code> → backend.
              </p>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}
