const EXAMPLES = [
  'What were the top 10 products by revenue?',
  'How did revenue change over time?',
  'Compare revenue between November and December.',
  'How does revenue differ between mobile and desktop users?',
  'Which traffic source generated the most revenue?',
  'Which products had high views but relatively low purchase rates?',
]

export function EmptyState({ onPick }: { onPick: (question: string) => void }) {
  return (
    <section className="empty-state">
      <h2>Ask about the Google Merchandise Store</h2>
      <p className="muted">
        GA4 web analytics from Nov 2020 to Jan 2021: visitors, products, purchases, devices and traffic
        sources. Every answer is computed with SQL on BigQuery, and you can open each query to see it.
      </p>
      <div className="examples">
        {EXAMPLES.map((question) => (
          <button key={question} type="button" onClick={() => onPick(question)}>
            {question}
          </button>
        ))}
      </div>
    </section>
  )
}
