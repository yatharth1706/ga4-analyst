import { describe, expect, it } from 'vitest'
import { formatValue } from './format'

describe('formatValue', () => {
  it('shows money columns in dollars', () => {
    expect(formatValue(13788, 'revenue')).toBe('$13,788')
    expect(formatValue(160555, 'dec_revenue', { compact: true })).toBe('$160.6K')
  })

  it('does not treat revenue ratios as money', () => {
    expect(formatValue(0.29, 'revenue_share')).toBe('0.29')
    expect(formatValue(11.3, 'revenue_pct_change')).toBe('11.3')
  })

  it('shows missing values as a dash', () => {
    expect(formatValue(null)).toBe('—')
  })
})
