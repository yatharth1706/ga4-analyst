# GA4 Analyst

A chat app where you can ask questions about Google's [GA4 ecommerce demo dataset](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset). For every question it writes SQL, runs it on BigQuery, and replies with a short answer, a chart when useful, and the queries it ran. You can ask follow-up questions like a normal chat.

Live demo: https://ga4-analyst.vercel.app

Try these one after another: "What were the top 5 products by revenue?", then "What about just December?", then "How does that compare with November?"

My assumptions, what I cut, where I got stuck and what I would do next are in [DECISIONS.md](DECISIONS.md).

## How it works

```text
Browser (React)
  │  POST /api/chat {question, history}  →  streamed events
  ▼
FastAPI
  └─ Agent loop (backend/app/agent/loop.py)
       ├─ Gemini over plain HTTP (backend/app/llm/gemini.py)
       ├─ run_sql      → dry run → BigQuery (backend/app/bigquery/client.py)
       └─ create_chart → checked against the query result
```

1. The browser sends the question along with a short history of the earlier questions and answers.
2. The backend sends the conversation and the two tools to Gemini.
3. If Gemini asks for tools, the backend runs them and sends the results back. This repeats until Gemini replies with text, which is the answer.
4. Every step is streamed to the browser, so you can see each query start and finish.

The loop is written by hand, without any agent framework or SDK. It stops after 10 rounds, and if it gets there it asks Gemini once more without tools so you still get an answer.

### Tools

- `run_sql`: runs one read-only query and returns the columns, up to 100 rows and the total row count. If the query fails, the error goes back to the model so it can fix it.
- `create_chart`: makes a bar, line or KPI chart from an earlier query. It only refers to the query by its ID, and the frontend draws it from the rows it already received, so a chart can't show numbers that BigQuery didn't return.

### Safety

Every query is dry-run first. It only runs if BigQuery says it is a single `SELECT` that scans less than 3 GB. The real query also has a cost limit, a 30 second timeout and a limit of 500 rows. The service account only has the BigQuery Job User role.

## The dataset

Three months (1 Nov 2020 to 31 Jan 2021) of GA4 events from the Google Merchandise Store: around 4.3M events, 270K users and $362K revenue.

The model gets a guide to this dataset in [ga4_notes.md](backend/app/agent/prompts/ga4_notes.md). It covers the tricky parts, for example that revenue gets counted twice if you sum it after unnesting items, that `traffic_source` is the first source of the user and not of the purchase, and that product view counts are inflated because each view event has several products in it.

## Run locally

You need Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22+, a Gemini API key, and a Google Cloud project (the free BigQuery sandbox is enough). Create a service account with the BigQuery Job User role and download a JSON key. Keep the key file outside this repo.

Backend:

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173.

### Environment variables (`backend/.env`)

| Variable | What it is |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | For example `gemini-3.8-flash` |
| `GOOGLE_CLOUD_PROJECT` | The Google Cloud project that runs the queries |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local only: path to the key file |
| `GCP_SERVICE_ACCOUNT_JSON` | Deployed only: the contents of the key file |

## Tests

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm test && npm run build
```

The backend tests use a fake Gemini and a fake BigQuery client, so they run offline. They cover the loop, error recovery, the SQL safety checks, chart checks and the API.

There is also an eval script that runs 10 real questions through the real agent and checks the key numbers against SQL I wrote by hand:

```bash
cd backend && uv run python -m evals.run_evals
```

All numeric checks pass in the latest run. The results are in [evals/report.md](backend/evals/report.md).

## Deployment

The app runs on Vercel as one project with two services, set up in [vercel.json](vercel.json). The frontend serves `/` and FastAPI serves `/api/*`. On Vercel, set `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_CLOUD_PROJECT` and `GCP_SERVICE_ACCOUNT_JSON`.

## Project layout

```text
backend/app/
  main.py              API endpoints
  config.py            environment variables
  agent/loop.py        the agent loop
  agent/tools.py       run_sql and create_chart
  agent/history.py     conversation history
  agent/prompts/       system prompt and dataset guide
  llm/gemini.py        Gemini client
  bigquery/client.py   running queries safely
backend/tests/         unit tests
backend/evals/         eval questions and results
frontend/src/
  components/          chat UI, query steps, tables, charts
  lib/                 API client, chat state, formatting
```

## Limitations

- Conversations are not saved. Refreshing the page starts a new chat.
- Answers take around 20 to 45 seconds.
- Made-up numbers are only checked in the evals, not live in the app.
- It is built for this one dataset.

## How I built this

I used Claude Code as a coding assistant. I made the design decisions (listed in [DECISIONS.md](DECISIONS.md)), checked the dataset facts and eval answers against BigQuery myself, and reviewed all the code.
