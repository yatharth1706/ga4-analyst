import type { AssistantMessage as Message } from '../lib/types'
import { Chart } from './Chart'
import { ChartBoundary } from './ChartBoundary'
import { Markdown } from './Markdown'
import { QuerySteps } from './QuerySteps'

type Props = { message: Message; onRetry: () => void }

export function AssistantMessage({ message, onRetry }: Props) {
  const resultFor = (queryId: string) => message.steps.find((step) => step.id === queryId)?.result

  return (
    <article className="message assistant">
      {message.steps.length > 0 && <QuerySteps steps={message.steps} />}

      {message.status === 'running' && !message.answer && (
        <p className="working">
          <span className="spinner" /> {message.steps.length ? 'Analyzing…' : 'Thinking…'}
        </p>
      )}

      {message.answer && <Markdown text={message.answer} />}

      {message.charts.map((spec, index) => (
        <ChartBoundary key={`${spec.query_id}-${index}`}>
          <Chart spec={spec} result={resultFor(spec.query_id)} />
        </ChartBoundary>
      ))}

      {message.error && (
        <div className="error-notice" role="alert">
          <p>{message.error.message}</p>
          {message.error.retryable && (
            <button type="button" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      )}
    </article>
  )
}
