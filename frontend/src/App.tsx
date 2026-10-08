import { useEffect, useReducer, useRef } from 'react'
import { AssistantMessage } from './components/AssistantMessage'
import { Composer } from './components/Composer'
import { EmptyState } from './components/EmptyState'
import { ChatError, streamChat } from './lib/api'
import { conversationReducer, initialState, isBusy } from './lib/conversation'

export default function App() {
  const [state, dispatch] = useReducer(conversationReducer, initialState)
  const busy = isBusy(state)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [state.messages])

  const send = async (question: string) => {
    try {
      await streamChat(question, state.history, (event) => dispatch({ type: 'event', event }))
    } catch (error) {
      const failure =
        error instanceof ChatError ? error : { message: 'Something went wrong. Please retry.', retryable: true }
      dispatch({ type: 'failed', failure: { message: failure.message, retryable: failure.retryable } })
    }
  }

  const ask = (question: string) => {
    dispatch({ type: 'ask', question, userId: crypto.randomUUID(), assistantId: crypto.randomUUID() })
    void send(question)
  }

  const retry = (question: string) => {
    dispatch({ type: 'retry' })
    void send(question)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>GA4 Analyst</h1>
        {state.messages.length > 0 && (
          <button type="button" className="secondary" onClick={() => dispatch({ type: 'reset' })} disabled={busy}>
            New chat
          </button>
        )}
      </header>

      <main className="conversation">
        {state.messages.length === 0 && <EmptyState onPick={ask} />}
        {state.messages.map((message) =>
          message.role === 'user' ? (
            <p key={message.id} className="message user">
              {message.text}
            </p>
          ) : (
            <AssistantMessage key={message.id} message={message} onRetry={() => retry(message.question)} />
          ),
        )}
        <div ref={bottomRef} />
      </main>

      <footer className="app-footer">
        <Composer disabled={busy} onSubmit={ask} />
      </footer>
    </div>
  )
}
