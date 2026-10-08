const MONEY_COLUMN = /revenue|usd|price|sales|aov|order_value/i
// "revenue_share" or "revenue_pct_change" are ratios, not dollars.
const RATIO_COLUMN = /share|pct|percent|rate|ratio/i

const full = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

export function formatValue(value: unknown, column = '', options: { compact?: boolean } = {}): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value !== 'number') return String(value)
  const text = (options.compact ? compact : full).format(value)
  const isMoney = MONEY_COLUMN.test(column) && !RATIO_COLUMN.test(column)
  return isMoney ? `$${text}` : text
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes >= 1e6) return `${Math.round(bytes / 1e6)} MB`
  return `${Math.max(1, Math.round(bytes / 1e3))} KB`
}

export function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

export function columnLabel(column: string): string {
  const words = column.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}
