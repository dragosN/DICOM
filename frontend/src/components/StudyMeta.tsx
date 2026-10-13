import type { StudySummary } from '../types'

function fmt(n: number | undefined | null, digits = 2): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—'
  return n.toFixed(digits)
}

function formatIop(iop: number[] | null): string {
  if (!iop || iop.length < 6) return '—'
  const row = iop.slice(0, 3).map((v) => fmt(v, 0)).join(', ')
  const col = iop.slice(3, 6).map((v) => fmt(v, 0)).join(', ')
  return `row [${row}] · col [${col}]`
}

type StudyMetaProps = {
  study: StudySummary
}

export function StudyMeta({ study }: StudyMetaProps) {
  const [rowSp, colSp, sliceSp] = study.spacing_mm ?? [null, null, null]
  const shape = study.shape_ijk

  return (
    <section className="panel meta-panel">
      <div className="panel-header">
        <h2>Study</h2>
        <span className={`badge ${study.ok ? 'ok' : 'bad'}`}>
          {study.ok ? 'valid' : 'issues'}
        </span>
      </div>
      <dl className="meta-grid">
        <div>
          <dt>ID</dt>
          <dd>
            <code>{study.id}</code>
          </dd>
        </div>
        <div>
          <dt>Slices</dt>
          <dd>{study.slice_count}</dd>
        </div>
        <div>
          <dt>Spacing (row, col, slice)</dt>
          <dd>
            {fmt(rowSp)} × {fmt(colSp)} × {fmt(sliceSp)} mm
          </dd>
        </div>
        <div>
          <dt>Shape (i, j, k)</dt>
          <dd>{shape ? shape.join(' × ') : '—'}</dd>
        </div>
        <div>
          <dt>IOP (LPS)</dt>
          <dd className="mono">{formatIop(study.iop)}</dd>
        </div>
        <div>
          <dt>Origin LPS</dt>
          <dd className="mono">
            {study.origin_lps
              ? study.origin_lps.map((v) => fmt(v, 1)).join(', ')
              : '—'}
          </dd>
        </div>
        <div>
          <dt>NIfTI</dt>
          <dd>{study.nifti_ready ? 'ready' : 'not available'}</dd>
        </div>
        <div>
          <dt>De-identified</dt>
          <dd>{study.deidentified ? 'yes' : 'no'}</dd>
        </div>
      </dl>
    </section>
  )
}
