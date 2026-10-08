const MONEY_COLUMN = /revenue|usd|price|sales|aov|order_value/i

const integer = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

/** Formats a value for display, using the column name to spot money. */
export function formatValue(value: unknown, column = '', options: { compact?: boolean } = {}): string {
  if (value === null || value === undefined) return '—'
  if (typeof value !== 'number') return String(value)
  const digits = options.compact ? compact : Number.isInteger(value) || Math.abs(value) >= 100 ? integer : decimal
  const text = digits.format(value)
  return MONEY_COLUMN.test(column) ? `$${text}` : text
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes >= 1e6) return `${Math.round(bytes / 1e6)} MB`
  return `${Math.max(1, Math.round(bytes / 1e3))} KB`
}

export function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

/** Readable axis/legend label from a column name: "dec_revenue" → "Dec revenue". */
export function columnLabel(column: string): string {
  const words = column.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}
