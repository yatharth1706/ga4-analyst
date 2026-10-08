import { formatBytes, formatDuration } from '../lib/format'
import type { QueryStep } from '../lib/types'
import { DataTable } from './DataTable'

export function QuerySteps({ steps }: { steps: QueryStep[] }) {
  return (
    <ol className="steps">
      {steps.map((step) => (
        <li key={step.id} className={`step step-${step.status}`}>
          <details>
            <summary>
              <StatusIcon status={step.status} />
              <span className="step-purpose">{step.purpose || 'Query'}</span>
              <span className="step-meta">{stepMeta(step)}</span>
            </summary>
            <pre className="sql">
              <code>{step.sql}</code>
            </pre>
            {step.status === 'error' && <p className="query-error">{step.error}</p>}
            {step.result && <DataTable result={step.result} />}
          </details>
        </li>
      ))}
    </ol>
  )
}

function StatusIcon({ status }: { status: QueryStep['status'] }) {
  if (status === 'running') return <span className="spinner" aria-label="Running" />
  return (
    <span className="step-icon" aria-label={status === 'done' ? 'Succeeded' : 'Failed'}>
      {status === 'done' ? '✓' : '✕'}
    </span>
  )
}

function stepMeta(step: QueryStep): string {
  if (step.status === 'running') return 'running…'
  if (step.status === 'error') return 'failed'
  const { result } = step
  if (!result) return ''
  const rows = `${result.row_count.toLocaleString()} ${result.row_count === 1 ? 'row' : 'rows'}`
  return `${rows} · ${formatDuration(result.duration_ms)} · ${formatBytes(result.bytes_processed)} scanned`
}
