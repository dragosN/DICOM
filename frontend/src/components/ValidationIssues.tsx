import type { ValidationIssue } from '../types'

type ValidationIssuesProps = {
  issues: ValidationIssue[]
}

export function ValidationIssues({ issues }: ValidationIssuesProps) {
  if (issues.length === 0) {
    return (
      <section className="panel issues-panel">
        <h2>Validation</h2>
        <p className="ok-text">No issues — geometry and series identity look consistent.</p>
      </section>
    )
  }

  return (
    <section className="panel issues-panel">
      <h2>Validation</h2>
      <ul className="issue-list">
        {issues.map((issue, idx) => (
          <li key={`${issue.code}-${idx}`} className={`issue ${issue.severity}`}>
            <div className="issue-top">
              <span className="issue-code">{issue.code}</span>
              {issue.requirement_id && (
                <span className="req-id">{issue.requirement_id}</span>
              )}
            </div>
            <p>{issue.message}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
