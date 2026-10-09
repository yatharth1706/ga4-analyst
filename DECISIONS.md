# Decision log

## Assumptions

- React is fine as long as I write the UI components myself (Mary confirmed). The only UI-side library is Recharts for charts. For markdown in answers I wrote a small parser instead of using `react-markdown`.
- The app only needs to work well for this GA4 dataset (Mary said it's my call). All dataset knowledge is in one prompt file, `ga4_notes.md`, so another dataset would mostly need a new notes file.
- Any LLM provider is okay since we bring our own key. I used Gemini because I already had a key.
- The data covers only 1 Nov 2020 to 31 Jan 2021, so "last month" etc. is calculated from 31 Jan 2021.
- Revenue is the sum of all `purchase` events. I did not de-duplicate transaction IDs because around 300 IDs repeat and around 900 purchases have no proper ID, so de-duplicating would treat purchases inconsistently. The model mentions this when it matters.
- Traffic source questions use `traffic_source`, which is the source that first brought the user, not the session where they bought. Session-level source is filled on only a third of events. The model mentions this too.

## Key decisions

- I wrote the agent loop myself and call Gemini over plain HTTP. The Gemini SDK can run tool calls automatically, which is the part the task wants us to build, so I didn't use it at all.
- SQL safety comes from BigQuery, not regex. Every query is dry-run first and only runs if BigQuery says it is a single `SELECT` scanning under 3 GB. The real query also has a cost limit, a 30 second timeout and a row limit, and the service account can only run queries.
- A chart only points to a query result by its ID and carries no numbers. The backend checks the chart against the real result and the frontend draws it from the rows it already has, so a chart can't show a number BigQuery didn't return. If the chart request is wrong, the error goes back to the model to fix.
- Instead of a schema tool, I put a dataset guide in the prompt. The tricky parts of this data are not visible in the schema, and I checked every fact in the guide against the data.
- The backend stores nothing. The browser sends a short history with each question (question, answer, SQL and a few rows), which works well on Vercel.
- The UI shows each query as it starts and finishes, since answers take 20 to 45 seconds.
- Row limits: BigQuery returns up to 500 rows for the table and charts, the model sees only 100 so it aggregates in SQL, history keeps 10 rows per query, and bar charts are limited to 50 rows.
- Model is `gemini-3.8-flash`. Three models gave the same numbers on my test questions and Flash was the fastest.

## Where I got stuck

- The data has traps. Each product view event has around 7 products, so some shirts showed 28K views and 0 purchases. Product IDs don't match between views and purchases, and placeholders like `<Other>` cover about a third of revenue by traffic source. I added all of this to the dataset guide.
- The first answer took 55 seconds because the model ran four queries one by one. I changed the prompt to use fewer queries and ask for independent ones together, and the same question took 1 query and 22 seconds.
- I wanted proof that the numbers are correct. I wrote an eval script that runs 10 fixed questions through the real agent and compares key numbers with SQL I wrote by hand. All pass. It also catches numbers the model calculated itself, and asking it to calculate percentages in SQL fixed most of those.
- When the server was down, the chat kept loading forever. Now the browser times out and shows a Retry button.
- On Vercel, the backend was not picked up until I set its entrypoint. I had also put the service account key in the wrong environment variable. I fixed both and created a new key.

## Cut

- Batched queries run one after another, not in parallel.
- The answer text comes at once, not word by word.
- No saved chats or login (the link is only for reviewers and free tiers limit misuse), no dark mode or extra UI polish.
- The check for made-up numbers only runs in the evals, not live.

## With 40 more hours

1. Check every number in the answer against the query results before showing it, and ask the model to fix anything that doesn't match.
2. Make it faster: run queries in parallel, cache results and stream the answer. Aim for under 10 seconds.
3. Define metrics like revenue, sessions and conversion rate once as tested SQL pieces that the model reuses, to avoid common SQL mistakes.
4. A bigger eval set (50+ questions with follow-ups) that runs on every change, with an AI judge for the written answer.
5. Support other LLM providers through my own message format, and compare Gemini and Claude on the evals.
6. Saved and shareable chats, editing and re-running a query's SQL, CSV export and a cost limit per user.
