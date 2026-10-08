import { describe, expect, it } from 'vitest'
import { parseSseBlock } from './api'

describe('parseSseBlock', () => {
  it('parses an event name and its JSON data', () => {
    const block = 'event: query_started\ndata: {"query_id": "q1", "purpose": "Revenue", "sql": "SELECT 1"}'
    expect(parseSseBlock(block)).toEqual({
      type: 'query_started',
      data: { query_id: 'q1', purpose: 'Revenue', sql: 'SELECT 1' },
    })
  })

  it('ignores blocks without an event or data line', () => {
    expect(parseSseBlock(': keep-alive')).toBeNull()
    expect(parseSseBlock('event: answer')).toBeNull()
  })
})
