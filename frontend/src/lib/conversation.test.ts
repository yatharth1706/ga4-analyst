import { describe, expect, it } from 'vitest'
import { conversationReducer, initialState, isBusy, type Action, type ConversationState } from './conversation'
import type { AssistantMessage, ServerEvent } from './types'

const ask: Action = { type: 'ask', question: 'Revenue by device?', userId: 'u1', assistantId: 'a1' }
const result = { columns: [{ name: 'n', type: 'INTEGER' }], rows: [[1]], row_count: 1, truncated: false, bytes_processed: 10, duration_ms: 5 }
const turn = { question: 'Revenue by device?', answer: 'Desktop leads.', queries: [] }

function run(...actions: Action[]): ConversationState {
  return actions.reduce(conversationReducer, initialState)
}

const event = (e: ServerEvent): Action => ({ type: 'event', event: e })
const lastAnswer = (state: ConversationState) => state.messages.at(-1) as AssistantMessage

describe('conversationReducer', () => {
  it('adds the question and a running answer', () => {
    const state = run(ask)
    expect(state.messages.map((message) => message.role)).toEqual(['user', 'assistant'])
    expect(isBusy(state)).toBe(true)
  })

  it('tracks query steps from start to result or error', () => {
    const state = run(
      ask,
      event({ type: 'query_started', data: { query_id: 'q1', purpose: 'Bad', sql: 'SELECT x' } }),
      event({ type: 'query_error', data: { query_id: 'q1', error: 'Unrecognized name: x' } }),
      event({ type: 'query_started', data: { query_id: 'q2', purpose: 'Good', sql: 'SELECT n' } }),
      event({ type: 'query_result', data: { query_id: 'q2', ...result } }),
    )
    const steps = lastAnswer(state).steps
    expect(steps.map((step) => step.status)).toEqual(['error', 'done'])
    expect(steps[1].result?.rows).toEqual([[1]])
  })

  it('stores the compact turn as history when the answer is done', () => {
    const state = run(ask, event({ type: 'answer', data: { text: 'Desktop leads.' } }), event({ type: 'done', data: { turn } }))
    expect(lastAnswer(state).status).toBe('done')
    expect(state.history).toEqual([turn])
    expect(isBusy(state)).toBe(false)
  })

  it('retry clears a failed answer and keeps the history unchanged', () => {
    const failed = run(
      ask,
      event({ type: 'query_started', data: { query_id: 'q1', purpose: 'p', sql: 's' } }),
      { type: 'failed', failure: { message: 'Network down', retryable: true } },
    )
    expect(lastAnswer(failed).error?.message).toBe('Network down')

    const retried = conversationReducer(failed, { type: 'retry' })
    expect(lastAnswer(retried)).toMatchObject({ status: 'running', steps: [], error: null, question: 'Revenue by device?' })
    expect(retried.history).toEqual([])
  })
})
