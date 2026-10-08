import type { Failure, ServerEvent, Turn } from './types'

const CONNECT_TIMEOUT_MS = 20_000
// The server streams an event at least every query or model call; a longer silence means it's stuck.
const IDLE_TIMEOUT_MS = 150_000

export class ChatError extends Error implements Failure {
  readonly retryable: boolean

  constructor(message: string, retryable: boolean) {
    super(message)
    this.retryable = retryable
  }
}

/**
 * Sends a question and calls `onEvent` for each server-sent event as it arrives.
 * EventSource only supports GET, so the stream is read from fetch's body directly.
 */
export async function streamChat(
  question: string,
  history: Turn[],
  onEvent: (event: ServerEvent) => void,
): Promise<void> {
  // A hung connection would otherwise leave the chat spinning forever.
  const controller = new AbortController()
  let timer = setTimeout(() => controller.abort(), CONNECT_TIMEOUT_MS)
  const restartIdleTimer = () => {
    clearTimeout(timer)
    timer = setTimeout(() => controller.abort(), IDLE_TIMEOUT_MS)
  }

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
      signal: controller.signal,
    })
    if (!response.ok || !response.body) throw errorForStatus(response.status)
    await readEvents(response.body, onEvent, restartIdleTimer)
  } catch (error) {
    if (error instanceof ChatError) throw error
    if (controller.signal.aborted) throw new ChatError('The server stopped responding. Please retry.', true)
    throw new ChatError('Could not reach the server. Check your connection and retry.', true)
  } finally {
    clearTimeout(timer)
  }
}

async function readEvents(
  body: NonNullable<Response['body']>,
  onEvent: (event: ServerEvent) => void,
  onChunk: () => void,
): Promise<void> {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  let finished = false
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    onChunk()
    buffer += value
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const event = parseSseBlock(block)
      if (!event) continue
      onEvent(event)
      finished ||= event.type === 'done' || event.type === 'error'
    }
  }
  if (!finished) {
    throw new ChatError('The connection closed before the answer was finished.', true)
  }
}

export function parseSseBlock(block: string): ServerEvent | null {
  let type = ''
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) type = line.slice('event: '.length)
    else if (line.startsWith('data: ')) data += line.slice('data: '.length)
  }
  if (!type || !data) return null
  return { type, data: JSON.parse(data) } as ServerEvent
}

function errorForStatus(status: number): ChatError {
  if (status === 422) return new ChatError('That question could not be sent. Try shortening it.', false)
  if (status >= 502) return new ChatError('The server is unavailable right now. Please retry.', true)
  return new ChatError(`The server returned an error (${status}). Please retry.`, status >= 500)
}
