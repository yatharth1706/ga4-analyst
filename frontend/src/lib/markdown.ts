/**
 * A deliberately small markdown parser for the model's answers.
 * The system prompt limits answers to paragraphs, bullet lists, bold and italics,
 * so that is all we support; anything else renders as plain text.
 * It produces data, not HTML, so model output can never inject markup.
 */

export type Inline = { kind: 'text' | 'bold' | 'italic' | 'code'; text: string }

export type Block =
  | { kind: 'paragraph'; content: Inline[] }
  | { kind: 'list'; ordered: boolean; items: Inline[][] }

const BULLET = /^\s*[-*+]\s+(.*)$/
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/
const HEADING = /^#{1,6}\s+(.*)$/
const INLINE = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)/

export function parseMarkdown(text: string): Block[] {
  const blocks: Block[] = []
  let paragraph: string[] = []

  const closeParagraph = () => {
    if (paragraph.length) blocks.push({ kind: 'paragraph', content: parseInline(paragraph.join(' ')) })
    paragraph = []
  }
  const addListItem = (ordered: boolean, item: string) => {
    closeParagraph()
    const last = blocks.at(-1)
    if (last?.kind === 'list' && last.ordered === ordered) last.items.push(parseInline(item))
    else blocks.push({ kind: 'list', ordered, items: [parseInline(item)] })
  }

  for (const line of text.split('\n')) {
    const bullet = BULLET.exec(line)
    const numbered = NUMBERED.exec(line)
    const heading = HEADING.exec(line)
    if (bullet) addListItem(false, bullet[1])
    else if (numbered) addListItem(true, numbered[1])
    else if (!line.trim()) closeParagraph()
    else if (heading) {
      closeParagraph()
      blocks.push({ kind: 'paragraph', content: [{ kind: 'bold', text: heading[1] }] })
    } else paragraph.push(line.trim())
  }
  closeParagraph()
  return blocks
}

export function parseInline(text: string): Inline[] {
  return text
    .split(INLINE)
    .filter(Boolean)
    .map((piece): Inline => {
      if (piece.startsWith('**') && piece.endsWith('**') && piece.length > 4) return { kind: 'bold', text: piece.slice(2, -2) }
      if (piece.startsWith('`') && piece.endsWith('`') && piece.length > 2) return { kind: 'code', text: piece.slice(1, -1) }
      if (piece.startsWith('*') && piece.endsWith('*') && piece.length > 2) return { kind: 'italic', text: piece.slice(1, -1) }
      return { kind: 'text', text: piece }
    })
}
