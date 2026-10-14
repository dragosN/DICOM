import { useState } from 'react'
import {
  loadDemoStudy,
  uploadStudy,
  type DemoSample,
} from './api/studies'
import { MeshViewer } from './components/MeshViewer'
import { SliceViewer } from './components/SliceViewer'
import { StudyMeta } from './components/StudyMeta'
import { UploadPanel } from './components/UploadPanel'
import { ValidationIssues } from './components/ValidationIssues'
import type { StudySummary } from './types'

export default function App() {
  const [study, setStudy] = useState<StudySummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function runIngest(action: () => Promise<StudySummary>) {
    setBusy(true)
    setError(null)
    try {
      const result = await action()
      setStudy(result)
    } catch (err) {
      setStudy(null)
      setError(err instanceof Error ? err.message : 'Ingest failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleUpload(file: File) {
    await runIngest(() => uploadStudy(file, true))
  }

  async function handleDemo(sample: DemoSample) {
    await runIngest(() => loadDemoStudy(sample, true))
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="brand">DICOM Portfolio</p>
          <h1>CT + mesh viewer</h1>
        </div>
        <p className="header-note">
          Upload a series, validate geometry, window/level axial slices, then
          clip and measure the demo bone mesh.
        </p>
      </header>

      <main className="layout">
        <aside className="sidebar">
          <UploadPanel
            busy={busy}
            onUpload={handleUpload}
            onLoadDemo={handleDemo}
          />
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
            <div className="viewers-row">
              <SliceViewer study={study} />
              <MeshViewer />
            </div>
          ) : (
            <section className="panel empty-stage">
              <h2>No study loaded</h2>
              <p className="muted">
                Upload <code>good_series.zip</code> with the API running on
                port 8000. Vite proxies <code>/api</code> → backend. After
                ingest, axial CT and the bone mesh appear side by side.
              </p>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}
