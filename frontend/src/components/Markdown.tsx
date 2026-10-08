import { parseMarkdown, type Inline } from '../lib/markdown'

export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      {parseMarkdown(text).map((block, index) => {
        if (block.kind === 'paragraph') return <p key={index}>{renderInline(block.content)}</p>
        const List = block.ordered ? 'ol' : 'ul'
        return (
          <List key={index}>
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex}>{renderInline(item)}</li>
            ))}
          </List>
        )
      })}
    </div>
  )
}

function renderInline(pieces: Inline[]) {
  return pieces.map((piece, index) => {
    switch (piece.kind) {
      case 'bold':
        return <strong key={index}>{piece.text}</strong>
      case 'italic':
        return <em key={index}>{piece.text}</em>
      case 'code':
        return <code key={index}>{piece.text}</code>
      case 'text':
        return piece.text
    }
  })
}
