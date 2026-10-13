export type ValidationIssue = {
  code: string
  message: string
  severity: 'error' | 'warning' | string
  requirement_id: string | null
}

export type StudySummary = {
  id: string
  ok: boolean
  slice_count: number
  series_uid: string | null
  spacing_mm: [number, number, number] | null
  iop: number[] | null
  origin_lps: number[] | null
  shape_ijk: [number, number, number] | null
  deidentified: boolean
  nifti_ready: boolean
  issues: ValidationIssue[]
}
