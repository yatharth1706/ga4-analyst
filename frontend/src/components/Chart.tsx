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

type Row = { [column: string]: unknown }

type PlotProps = { spec: ChartSpec; rows: Row[] }

// If the spec doesn't match its query's columns, skip the chart; the data table still shows the result.
export function Chart({ spec, result }: { spec: ChartSpec; result: QueryResult | undefined }) {
  if (!result || !fitsResult(spec, result)) return null
  const rows = toRows(result)

  return (
    <figure className="chart">
      <figcaption>{spec.title}</figcaption>
      {spec.type === 'kpi' && <p className="kpi-value">{formatValue(rows[0][spec.y[0]], spec.y[0])}</p>}
      {spec.type === 'bar' && <BarPlot spec={spec} rows={rows} />}
      {spec.type === 'line' && <LinePlot spec={spec} rows={rows} />}
    </figure>
  )
}

// Horizontal bars, so long category names such as product titles stay readable.
function BarPlot({ spec, rows }: PlotProps) {
  const x = spec.x as string
  const longestLabel = Math.max(...rows.map((row) => String(row[x]).length))
  return (
    <ResponsiveContainer width="100%" height={rows.length * 36 + 60}>
      <BarChart data={rows} layout="vertical" margin={{ right: 16 }}>
        <CartesianGrid stroke="var(--grid)" horizontal={false} />
        <XAxis type="number" tickFormatter={compactTick(spec)} {...axisStyle} />
        <YAxis type="category" dataKey={x} width={Math.min(240, longestLabel * 7 + 8)} interval={0} {...axisStyle} />
        <Tooltip {...tooltipStyle} formatter={tooltipFormatter} />
        {spec.y.length > 1 && <Legend formatter={columnLabel} />}
        {spec.y.map((column, index) => (
          <Bar key={column} dataKey={column} fill={SERIES_COLORS[index]} maxBarSize={24} radius={[0, 4, 4, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

function LinePlot({ spec, rows }: PlotProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={rows} margin={{ right: 16 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey={spec.x as string} {...axisStyle} />
        <YAxis tickFormatter={compactTick(spec)} {...axisStyle} />
        <Tooltip {...tooltipStyle} formatter={tooltipFormatter} />
        {spec.y.length > 1 && <Legend formatter={columnLabel} />}
        {spec.y.map((column, index) => (
          <Line key={column} dataKey={column} stroke={SERIES_COLORS[index]} strokeWidth={2} dot={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

const axisStyle = { stroke: 'var(--grid)', tick: { fill: 'var(--text-muted)', fontSize: 12 }, tickLine: false }

const tooltipStyle = {
  contentStyle: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 },
}

function compactTick(spec: ChartSpec) {
  return (value: unknown) => formatValue(value, spec.y[0], { compact: true })
}

function tooltipFormatter(value: unknown, name: unknown): [string, string] {
  return [formatValue(value, String(name)), columnLabel(String(name))]
}

function fitsResult(spec: ChartSpec, result: QueryResult): boolean {
  const columns = new Set(result.columns.map((column) => column.name))
  const needed = spec.type === 'kpi' ? spec.y.slice(0, 1) : [spec.x ?? '', ...spec.y]
  return result.rows.length > 0 && needed.length > 0 && needed.every((column) => columns.has(column))
}

function toRows(result: QueryResult): Row[] {
  return result.rows.map((values) =>
    Object.fromEntries(result.columns.map((column, index) => [column.name, values[index]])),
  )
}
