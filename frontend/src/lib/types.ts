// Mirrors the server-sent events emitted by backend/app/agent (tools.py and loop.py).

export type Column = { name: string; type: string }

export type QueryResult = {
  columns: Column[]
  rows: unknown[][]
  row_count: number
  truncated: boolean
  bytes_processed: number
  duration_ms: number
}

export type ChartSpec = {
  query_id: string
  type: 'bar' | 'line' | 'kpi'
  title: string
  x: string | null
  y: string[]
}

export type Turn = { question: string; answer: string; queries: unknown[] }

export type ServerEvent =
  | { type: 'query_started'; data: { query_id: string; purpose: string; sql: string } }
  | { type: 'query_result'; data: QueryResult & { query_id: string } }
  | { type: 'query_error'; data: { query_id: string; error: string } }
  | { type: 'chart'; data: ChartSpec }
  | { type: 'answer'; data: { text: string } }
  | { type: 'done'; data: { turn: Turn } }
  | { type: 'error'; data: Failure }

export type Failure = { message: string; retryable: boolean }

export type QueryStep = {
  id: string
  purpose: string
  sql: string
  status: 'running' | 'done' | 'error'
  result?: QueryResult
  error?: string
}

export type UserMessage = { role: 'user'; id: string; text: string }

export type AssistantMessage = {
  role: 'assistant'
  id: string
  question: string
  status: 'running' | 'done' | 'error'
  steps: QueryStep[]
  charts: ChartSpec[]
  answer: string | null
  error: Failure | null
}

export type Message = UserMessage | AssistantMessage
