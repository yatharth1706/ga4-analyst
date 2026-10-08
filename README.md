# GA4 Analyst

A chat app for asking data questions about Google's [GA4 ecommerce demo dataset](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset). Each answer is computed with SQL on BigQuery and comes back as a short written analysis, a chart when one helps, and the queries and data behind it. Follow-up questions keep the context of the conversation.

**Live demo:** https://ga4-analyst.vercel.app

Try, in order: *"What were the top 5 products by revenue?"* → *"What about just December?"* → *"How does that compare with November?"*

Assumptions, cuts, problems hit and what I'd do next are in [DECISIONS.md](DECISIONS.md).

## How it works

```text
Browser (React)
  │  POST /api/chat {question, history}  →  streamed events (server-sent events)
  ▼
FastAPI
  └─ Agent loop                                    backend/app/agent/loop.py
       ├─ Gemini generateContent, raw HTTP          backend/app/llm/gemini.py
       ├─ tool run_sql      → dry run → BigQuery    backend/app/bigquery/client.py
       └─ tool create_chart → checked against the query's real result
```

1. The browser sends the question plus a compact history of earlier turns (question, answer, and the SQL behind it with a few preview rows).
2. The agent loop sends the conversation, the system prompt and the two tool definitions to Gemini.
3. If Gemini asks for tools, every call in that turn is executed and all results go back in one message. Gemini can run several queries, read the results, fix a failed query, and decide when it has enough.
4. When Gemini replies with text instead of tool calls, that text is the answer.
5. Each step is streamed to the browser as it happens: `query_started`, `query_result` / `query_error`, `chart`, `answer`, `done` (or `error`).

The loop is written by hand: no agent framework, and no SDK feature that runs tools automatically. It stops after 10 rounds of tool calls; if it gets there, one last request with tools disabled forces an answer from what it has.

### Tools

| Tool | What it does |
|---|---|
| `run_sql(sql, purpose)` | Runs one read-only query. Returns a `query_id`, the columns, up to 100 rows, the total row count and whether rows were cut. Errors come back as messages the model can fix. |
| `create_chart(query_id, type, title, x, y)` | Draws a bar, line or KPI chart from an earlier query's result. The chart never carries numbers itself: the backend attaches the real rows, so it can't show data BigQuery didn't return. A bad spec (unknown column, text column as a value, too many bars) is sent back to the model to correct. |

### Safety

Every query is first **dry-run** by BigQuery. It runs only if BigQuery reports a single `SELECT` statement scanning under 3 GB. The checks use BigQuery's own parser, not keyword matching. The real job also has a 3 GB billing cap, a 30-second timeout and a 500-row fetch limit, and the service account has only the *BigQuery Job User* role.

## The dataset

`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`: three months (2020-11-01 to 2021-01-31) of GA4 events from the Google Merchandise Store. About 4.3M events, 270K users and $362K of revenue. Each row is one event (a page view, an add-to-cart, a purchase...).

The model gets a hand-written guide to the dataset, [ga4_notes.md](backend/app/agent/prompts/ga4_notes.md). Every fact in it was checked against the data. It covers the traps that otherwise produce confident wrong answers:

- **Two levels of revenue.** Order revenue must not be summed after unnesting items, or it gets counted once per item.
- **`traffic_source` is first-touch.** It records how the user was *first* acquired, not the source of the session that bought.
- **Inflated product views.** `view_item` events carry about 7 products each, so per-product view counts and conversion rates are only useful for comparing products.
- **Product IDs don't match across event types.** Join on product name instead.
- **Privacy placeholders.** Values like `<Other>` and `(data deleted)` cover about a third of revenue by traffic source.

## Run it locally

**You need:** Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22+, a Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey)), and a Google Cloud project. The free BigQuery sandbox is enough.

**BigQuery access:** in the Cloud Console, create a service account with the **BigQuery Job User** role, add a JSON key, and save the key file **outside this repo**.

**Backend**

```bash
cd backend
cp .env.example .env      # then fill in the values below
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a second terminal; Vite forwards `/api` to the backend)

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173
```

### Environment variables (`backend/.env`)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Gemini API key |
| `GEMINI_MODEL` | Model name, e.g. `gemini-3.8-flash` |
| `GOOGLE_CLOUD_PROJECT` | The Google Cloud project that runs (and is billed for) the queries |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local only: path to the service-account key file |
| `GCP_SERVICE_ACCOUNT_JSON` | Deployed only: the key file's JSON contents, used instead of a file path |

## Tests and evals

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm test && npm run build
```

- **Backend unit tests** use a scripted fake LLM and a fake BigQuery client, so they run offline. They cover the loop (parallel tool calls, retry after an SQL error, chart corrections, the iteration cap), the safety checks (non-SELECT and over-budget queries never run), error messages, history and the streaming endpoint.
- **Frontend tests** cover the stream parser, the conversation state and the markdown parser.

**Golden questions:** `uv run python -m evals.run_evals` runs 10 real questions through the real agent, Gemini and BigQuery included. It checks the key numbers against hand-written reference SQL, and flags *ungrounded* numbers: figures in an answer that no query returned. Latest run: 8/8 numeric checks pass, and the clarifying-question and caveat cases were checked by hand. See [evals/report.md](backend/evals/report.md).

## Deployment

One Vercel project serves both parts using [Services](https://vercel.com/docs/services), configured in [vercel.json](vercel.json): the Vite build answers `/` and FastAPI answers `/api/*`. Set `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_CLOUD_PROJECT` and `GCP_SERVICE_ACCOUNT_JSON` in the Vercel project settings. Don't set `GOOGLE_APPLICATION_CREDENTIALS` there.

The backend keeps no state between requests, because the browser sends the history with each question. That's why it runs fine as serverless functions.

## Project layout

```text
backend/
  app/
    main.py              POST /api/chat (streaming), GET /api/health
    config.py            environment variables
    agent/
      loop.py            the agent loop
      tools.py           run_sql and create_chart: definitions, execution, chart validation
      history.py         compact conversation history ⇄ model context
      events.py          the streamed events
      prompts/           system.md (behaviour) and ga4_notes.md (dataset guide)
    llm/gemini.py        the only Gemini-specific code
    bigquery/client.py   dry run, limits, running queries, error cleanup
  tests/                 unit tests, with fakes.py
  evals/                 golden.yaml, run_evals.py, report.md
frontend/src/
  App.tsx                layout; connects the stream to the conversation state
  components/            chat, query steps, data table, charts, input box
  lib/                   api.ts (stream client), conversation.ts (state), markdown.ts, format.ts, types.ts
```

## Limitations

- **No saved conversations or accounts.** A reload starts a fresh chat.
- **Answers take about 20–45 seconds.** Each BigQuery round trip with its dry run takes 4–8 s, and parallel tool calls run one after another.
- **Ungrounded-number detection runs only in the evals.** In the app, a number the model computes itself isn't flagged yet.
- **Built for this one dataset.** The dataset knowledge sits in one prompt file, but the app isn't a general analysis tool.

## How this was built

I used Claude Code as a coding assistant throughout. I made the design decisions (listed with their reasons in [DECISIONS.md](DECISIONS.md)), checked the dataset facts and the eval answers against BigQuery myself, and reviewed every module.
