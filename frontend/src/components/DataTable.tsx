import { formatValue } from '../lib/format'
import type { QueryResult } from '../lib/types'

const NUMERIC = new Set(['INTEGER', 'INT64', 'FLOAT', 'FLOAT64', 'NUMERIC', 'BIGNUMERIC'])

export function DataTable({ result }: { result: QueryResult }) {
  if (result.rows.length === 0) return <p className="muted">No rows returned.</p>
  const cellClass = result.columns.map((column) => (NUMERIC.has(column.type) ? 'numeric' : undefined))

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {result.columns.map((column, index) => (
              <th key={column.name} className={cellClass[index]}>
                {column.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, index) => (
                <td key={index} className={cellClass[index]}>
                  {formatValue(value, result.columns[index].name)}
                </td>
              ))}
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
