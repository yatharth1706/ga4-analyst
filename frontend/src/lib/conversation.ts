import type { AssistantMessage, Failure, Message, QueryStep, ServerEvent, Turn } from './types'

export type ConversationState = {
  messages: Message[]
  history: Turn[]
}

export type Action =
  | { type: 'ask'; question: string; userId: string; assistantId: string }
  | { type: 'retry' }
  | { type: 'event'; event: ServerEvent }
  | { type: 'failed'; failure: Failure }
  | { type: 'reset' }

export const initialState: ConversationState = { messages: [], history: [] }

export function conversationReducer(state: ConversationState, action: Action): ConversationState {
  switch (action.type) {
    case 'ask':
      return {
        ...state,
        messages: [
          ...state.messages,
          { role: 'user', id: action.userId, text: action.question },
          newAssistantMessage(action.assistantId, action.question),
        ],
      }
    case 'retry':
      return updateLastAnswer(state, (message) => newAssistantMessage(message.id, message.question))
    case 'failed':
      return updateLastAnswer(state, (message) => ({ ...message, status: 'error', error: action.failure }))
    case 'event':
      return applyEvent(state, action.event)
    case 'reset':
      return initialState
  }
}

export function isBusy(state: ConversationState): boolean {
  const last = state.messages.at(-1)
  return last?.role === 'assistant' && last.status === 'running'
}

function applyEvent(state: ConversationState, event: ServerEvent): ConversationState {
  switch (event.type) {
    case 'query_started': {
      const step: QueryStep = {
        id: event.data.query_id,
        purpose: event.data.purpose,
        sql: event.data.sql,
        status: 'running',
      }
      return updateLastAnswer(state, (message) => ({ ...message, steps: [...message.steps, step] }))
    }
    case 'query_result': {
      const { query_id, ...result } = event.data
      return updateStep(state, query_id, { status: 'done', result })
    }
    case 'query_error':
      return updateStep(state, event.data.query_id, { status: 'error', error: event.data.error })
    case 'chart':
      return updateLastAnswer(state, (message) => ({ ...message, charts: [...message.charts, event.data] }))
    case 'answer':
      return updateLastAnswer(state, (message) => ({ ...message, answer: event.data.text }))
    case 'done':
      return {
        ...updateLastAnswer(state, (message) => ({ ...message, status: 'done' })),
        history: [...state.history, event.data.turn],
      }
    case 'error':
      return updateLastAnswer(state, (message) => ({ ...message, status: 'error', error: event.data }))
    default:
      return state
  }
}

function newAssistantMessage(id: string, question: string): AssistantMessage {
  return { role: 'assistant', id, question, status: 'running', steps: [], charts: [], answer: null, error: null }
}

function updateLastAnswer(
  state: ConversationState,
  update: (message: AssistantMessage) => AssistantMessage,
): ConversationState {
  const last = state.messages.at(-1)
  if (last?.role !== 'assistant') return state
  return { ...state, messages: [...state.messages.slice(0, -1), update(last)] }
}

function updateStep(state: ConversationState, stepId: string, changes: Partial<QueryStep>): ConversationState {
  return updateLastAnswer(state, (message) => ({
    ...message,
    steps: message.steps.map((step) => (step.id === stepId ? { ...step, ...changes } : step)),
  }))
}
