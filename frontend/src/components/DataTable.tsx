import { formatValue } from '../lib/format'
import type { QueryResult } from '../lib/types'

const NUMERIC = new Set(['INTEGER', 'INT64', 'FLOAT', 'FLOAT64', 'NUMERIC', 'BIGNUMERIC'])

export function DataTable({ result }: { result: QueryResult }) {
  if (result.rows.length === 0) return <p className="muted">No rows returned.</p>

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {result.columns.map((column) => (
              <th key={column.name} className={NUMERIC.has(column.type) ? 'numeric' : undefined}>
                {column.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, columnIndex) => {
                const column = result.columns[columnIndex]
                return (
                  <td key={columnIndex} className={NUMERIC.has(column.type) ? 'numeric' : undefined}>
                    {typeof value === 'object' && value !== null ? JSON.stringify(value) : formatValue(value, column.name)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {result.truncated && (
        <p className="muted small">
          Showing {result.rows.length.toLocaleString()} of {result.row_count.toLocaleString()} rows.
        </p>
      )}
    </div>
  )
}
