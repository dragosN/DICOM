import type { StudySummary } from '../types'

const API_BASE = '/api'

export async function uploadStudy(
  file: File,
  deidentify = true,
): Promise<StudySummary> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/studies?deidentify=${deidentify}`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Upload failed (${res.status})`)
  }
  return res.json() as Promise<StudySummary>
}

export async function getStudy(id: string): Promise<StudySummary> {
  const res = await fetch(`${API_BASE}/studies/${id}`)
  if (!res.ok) {
    throw new Error(`Study not found (${res.status})`)
  }
  return res.json() as Promise<StudySummary>
}

export type DemoSample = 'synthetic' | 'tcia'

export async function loadDemoStudy(
  sample: DemoSample,
  deidentify = true,
): Promise<StudySummary> {
  const res = await fetch(
    `${API_BASE}/studies/demo/${sample}?deidentify=${deidentify}`,
    { method: 'POST' },
  )
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Demo load failed (${res.status})`)
  }
  return res.json() as Promise<StudySummary>
}

/** Build a cache-busting slice URL for the given window/level. */
export function sliceUrl(
  studyId: string,
  z: number,
  center: number,
  width: number,
): string {
  const params = new URLSearchParams({
    center: String(center),
    width: String(width),
  })
  return `${API_BASE}/studies/${studyId}/slices/${z}?${params.toString()}`
}
