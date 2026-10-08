# Decision log

## Assumptions

- **React is allowed; "no UI library" means no component or chat-UI kits.** *Confirmed with Mary.* Every component is hand-written. The only UI-side library is Recharts, since the task allows visualization libraries. I wrote a small markdown parser rather than using `react-markdown`.
- **Optimise for this dataset, not a generic analyst.** *Confirmed with Mary as my call.* All dataset knowledge lives in one prompt file (`ga4_notes.md`), so pointing the app at another dataset means mostly a new notes file.
- **Any LLM provider is fine** ("bring your own key"). I used Gemini because I had a key.
- **Dates are relative to the data.** "Our store" is the Google Merchandise Store, and "last month" is anchored to the dataset's last day, 2021-01-31.
- **Revenue = all `purchase` events, without de-duplicating transaction IDs.** About 300 IDs repeat and about 900 purchases have no usable ID, so de-duplicating would treat purchases inconsistently. The model mentions the caveat when it matters.
- **Channel questions use `traffic_source`**, the user's *first-touch* source. The session-level source covers only about a third of events. The model says so.

## Key decisions

- **A hand-written loop over raw HTTP, no SDK.** Gemini's SDK can run tool calls automatically, which is the part the task asks us to write. Raw requests make that unambiguous and keep every request and response visible.
- **SQL safety from BigQuery itself, not a regex.** A dry run must report a single `SELECT` scanning under 3 GB before anything runs; the real job also has a billing cap, a timeout and a row limit. The service account can only run queries.
- **Charts point at a query's result and carry no data of their own.** The backend validates each chart spec and attaches the real rows, so a chart can't show a number BigQuery didn't return. A bad spec goes back to the model to fix.
- **A curated dataset guide in the prompt, instead of a "read the schema" tool.** The traps below aren't visible in a schema. Every fact in the guide was checked against the data.
- **A stateless backend.** The browser sends a compact history (question, answer, SQL, a few preview rows) with each question. That works on serverless hosting, and the client can't forge tool results.
- **Streaming progress events instead of a spinner.** Answers take 20–45 s, so the user watches each query start and finish.
- **`gemini-3.8-flash`.** Three models gave identical answers on the test questions; Flash was the fastest.

## Where I got stuck

- **The data has traps.** Product view events carry about 7 products each, so some shirts showed 28K views and 0 purchases. Product IDs don't match across event types, and privacy placeholders cover about a third of revenue by traffic source. *Fix:* the dataset guide tells the model how to handle each one and to state the caveat.
- **The first answer took 55 s.** The model ran four queries one after another, at 5–8 s each. *Fix:* the prompt asks for the fewest queries and to batch independent ones, which brought it to 1 query and 22 s.
- **Proving the numbers are right.** *Fix:* an eval runner sends 10 golden questions through the real agent and checks the key numbers against hand-written SQL (all pass). It also flags numbers the model computed itself. Asking for derived numbers to be computed in SQL removed most of those.
- **The chat could spin forever** when the server was unreachable. *Fix:* the client times out and offers Retry.
- **Deployment:** Vercel didn't detect the FastAPI service until its entrypoint was declared, and the key file's contents had been put in a variable that Google's library reads as a file path. *Fix:* both corrected; the key was rotated.

## Cut

- **Running parallel tool calls concurrently.** They run one after another.
- **Word-by-word answer streaming.**
- **Saved conversations, authentication** (the link is shared only with reviewers; the free tiers cap what misuse could cost), **dark mode** and other polish.
- **Live checking of invented numbers.** For now it runs only in the evals.

## With 40 more hours

1. **Ground every number at runtime.** After the answer, match each figure against the query results, then ask the model to fix any that don't match or flag them in the UI. The detection already exists in the evals.
2. **Speed.** Run batched queries concurrently, cache results by SQL, and stream the answer text. Target: under 10 s for common questions.
3. **A small semantic layer.** Define revenue, sessions, conversion rate and attribution once, as tested SQL building blocks the model combines, instead of re-deriving them in every query. That removes the most common class of SQL mistakes.
4. **A bigger eval set run on every change.** 50+ questions, including follow-up chains, plus an AI judge for caveats and narrative quality, so prompt changes can't silently make answers worse.
5. **Swappable LLM providers.** Use our own message types instead of Gemini's format, then compare Gemini and Claude on the eval set.
6. **Product features:** saved and shareable conversations, editing a query's SQL and re-running it, CSV export, and per-user cost limits.
