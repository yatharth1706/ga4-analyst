import { useState, type FormEvent, type KeyboardEvent } from 'react'

type Props = { disabled: boolean; onSubmit: (question: string) => void }

export function Composer({ disabled, onSubmit }: Props) {
  const [text, setText] = useState('')
  const question = text.trim()

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    if (!question || disabled) return
    onSubmit(question)
    setText('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) submit(event)
  }

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask about revenue, products, traffic sources, devices…"
        aria-label="Your question"
        rows={1}
        maxLength={2000}
      />
      <button type="submit" disabled={disabled || !question}>
        {disabled ? 'Working…' : 'Send'}
      </button>
    </form>
  )
}
