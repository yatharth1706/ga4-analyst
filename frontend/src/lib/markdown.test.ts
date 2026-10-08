import { describe, expect, it } from 'vitest'
import { parseInline, parseMarkdown } from './markdown'

describe('parseMarkdown', () => {
  it('splits paragraphs and bullet lists', () => {
    const blocks = parseMarkdown('Desktop leads.\n\n*   **Desktop:** $97,752\n- Mobile: $60,450\n\n*Note: Dec 2020 only.*')
    expect(blocks.map((block) => block.kind)).toEqual(['paragraph', 'list', 'paragraph'])
    expect(blocks[1]).toMatchObject({ kind: 'list', ordered: false })
    expect(blocks[2]).toEqual({ kind: 'paragraph', content: [{ kind: 'italic', text: 'Note: Dec 2020 only.' }] })
  })

  it('joins wrapped lines into one paragraph and supports numbered lists', () => {
    const blocks = parseMarkdown('Line one\nline two\n1. First\n2. Second')
    expect(blocks[0]).toEqual({ kind: 'paragraph', content: [{ kind: 'text', text: 'Line one line two' }] })
    expect(blocks[1]).toMatchObject({ kind: 'list', ordered: true })
  })

  it('treats markup as text, never HTML', () => {
    expect(parseInline('<img src=x onerror=alert(1)>')).toEqual([{ kind: 'text', text: '<img src=x onerror=alert(1)>' }])
  })
})

describe('parseInline', () => {
  it('handles bold, italic and code', () => {
    expect(parseInline('**$5,665** in *Dec* for `(not set)`')).toEqual([
      { kind: 'bold', text: '$5,665' },
      { kind: 'text', text: ' in ' },
      { kind: 'italic', text: 'Dec' },
      { kind: 'text', text: ' for ' },
      { kind: 'code', text: '(not set)' },
    ])
  })

  it('leaves a lone asterisk alone', () => {
    expect(parseInline('5 * 3 = 15')).toEqual([{ kind: 'text', text: '5 * 3 = 15' }])
  })
})
