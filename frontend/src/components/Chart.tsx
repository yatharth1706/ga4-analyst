import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { columnLabel, formatValue } from '../lib/format'
import type { ChartSpec, QueryResult } from '../lib/types'

const SERIES_COLORS = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)']
const LONG_LABEL = 12

type Row = { [column: string]: unknown }

/**
 * Renders a chart spec against the rows of the query it references.
 * Returns nothing if the spec doesn't fit the data; the table in the query steps still shows it.
 */
export function Chart({ spec, result }: { spec: ChartSpec; result: QueryResult | undefined }) {
  if (!result || !fitsResult(spec, result)) return null
  const rows = toRows(result)

  return (
    <figure className="chart">
      <figcaption>{spec.title}</figcaption>
      {spec.type === 'kpi' ? (
        <p className="kpi-value">{formatValue(rows[0]?.[spec.y[0]], spec.y[0])}</p>
      ) : (
        <ResponsiveContainer width="100%" height={chartHeight(spec, rows)}>
          {spec.type === 'line' ? <LinePlot spec={spec} rows={rows} /> : <BarPlot spec={spec} rows={rows} />}
        </ResponsiveContainer>
      )}
    </figure>
  )
}

function BarPlot({ spec, rows }: { spec: ChartSpec; rows: Row[] }) {
  const x = spec.x as string
  const horizontal = hasLongLabels(rows, x)
  return (
    <BarChart data={rows} layout={horizontal ? 'vertical' : 'horizontal'} margin={{ left: 8, right: 16 }}>
      <CartesianGrid stroke="var(--grid)" horizontal={!horizontal} vertical={horizontal} />
      {horizontal ? (
        <>
          <XAxis type="number" tickFormatter={(value) => formatValue(value, spec.y[0], { compact: true })} {...axisStyle} />
          <YAxis type="category" dataKey={x} width={labelWidth(rows, x)} interval={0} {...axisStyle} />
        </>
      ) : (
        <>
          <XAxis dataKey={x} {...axisStyle} />
          <YAxis tickFormatter={(value) => formatValue(value, spec.y[0], { compact: true })} {...axisStyle} />
        </>
      )}
      <Tooltip {...tooltipStyle} formatter={tooltipFormatter} />
      {spec.y.length > 1 && <Legend formatter={columnLabel} />}
      {spec.y.map((column, index) => (
        <Bar
          key={column}
          dataKey={column}
          name={column}
          fill={SERIES_COLORS[index]}
          maxBarSize={24}
          radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}
        />
      ))}
    </BarChart>
  )
}

function LinePlot({ spec, rows }: { spec: ChartSpec; rows: Row[] }) {
  return (
    <LineChart data={rows} margin={{ left: 8, right: 16 }}>
      <CartesianGrid stroke="var(--grid)" vertical={false} />
      <XAxis dataKey={spec.x as string} {...axisStyle} />
      <YAxis tickFormatter={(value) => formatValue(value, spec.y[0], { compact: true })} {...axisStyle} />
      <Tooltip {...tooltipStyle} formatter={tooltipFormatter} />
      {spec.y.length > 1 && <Legend formatter={columnLabel} />}
      {spec.y.map((column, index) => (
        <Line
          key={column}
          dataKey={column}
          name={column}
          stroke={SERIES_COLORS[index]}
          strokeWidth={2}
          dot={rows.length <= 31}
          activeDot={{ r: 5 }}
        />
      ))}
    </LineChart>
  )
}

const axisStyle = {
  stroke: 'var(--grid)',
  tick: { fill: 'var(--text-muted)', fontSize: 12 },
  tickLine: false,
}

const tooltipStyle = {
  contentStyle: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 },
  labelStyle: { color: 'var(--text)' },
  itemStyle: { color: 'var(--text)' },
}

function tooltipFormatter(value: unknown, name: unknown): [string, string] {
  return [formatValue(value, String(name)), columnLabel(String(name))]
}

function fitsResult(spec: ChartSpec, result: QueryResult): boolean {
  const names = new Set(result.columns.map((column) => column.name))
  const needed = spec.type === 'kpi' ? spec.y.slice(0, 1) : [spec.x ?? '', ...spec.y]
  return needed.length > 0 && needed.every((column) => names.has(column)) && result.rows.length > 0
}

function toRows(result: QueryResult): Row[] {
  return result.rows.map((row) =>
    Object.fromEntries(result.columns.map((column, index) => [column.name, row[index]])),
  )
}

function hasLongLabels(rows: Row[], x: string): boolean {
  return rows.some((row) => String(row[x]).length > LONG_LABEL)
}

function labelWidth(rows: Row[], x: string): number {
  const longest = Math.max(...rows.map((row) => String(row[x]).length))
  return Math.min(240, longest * 7 + 8)
}

function chartHeight(spec: ChartSpec, rows: Row[]): number {
  const horizontalBars = spec.type === 'bar' && hasLongLabels(rows, spec.x as string)
  return horizontalBars ? Math.max(160, rows.length * 36 + 40) : 300
}
