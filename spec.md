# GA4 Agentic Data Analysis App — Spec (v2)

> v2 replaces the first draft (kept in `spec.original.md`). It records the decisions agreed before implementation.
> Items marked **[verify]** are checked against the real data in Phase 0. Items marked **[Mary]** may change once the recruiter answers our questions.

---

## 1. Objective

A standalone chat app where a user asks questions about Google's GA4 ecommerce demo dataset and gets:

1. Answers computed from real BigQuery results, never invented numbers
2. A chart when it helps, plus the underlying table and SQL ("show your work")
3. A short written narrative that separates facts from interpretation
4. Follow-up questions answered in the context of the conversation

Time-box: ~8 hours. Correctness and a clear, defensible agent loop matter more than breadth or visual polish.

---

## 2. Stack and deployment

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript, hand-written components | Single-page chat with no SSR or SEO needs; Vite is the fastest dev loop |
| Charts | Recharts | Declarative, React-native, covers our three chart types |
| Markdown | `react-markdown` | Narrative formatting only **[Mary: confirm utility libs are OK]** |
| Backend | Python + FastAPI | The author's strongest language, for the live extension |
| LLM | Gemini via **raw REST over `httpx`** (no `google-genai` SDK) **[Mary]** | Key already available; see §2.1 |
| Data | BigQuery `google-cloud-bigquery` client | Official client; supports dry runs and byte caps |
| Hosting | One Vercel project: static Vite build + FastAPI function under `/api` | One deploy; Vercel runs FastAPI natively; streaming works; 300s default timeout |

### 2.1 Why raw HTTP instead of the Gemini SDK

The rule allows "raw HTTP or a vendor SDK's messages endpoint". `google-genai` is allowed if used only for `generate_content`, but it also ships **automatic function calling**: given Python callables, it runs the tool loop itself. That is exactly the part we must write by hand. Calling `POST .../models/{model}:generateContent` directly with `httpx`:

- removes any doubt for reviewers (no hidden loop that we had to remember to disable)
- makes the request/response JSON fully visible, which helps debugging and the interview walkthrough
- costs about the same amount of code (~80 lines including retries)

All Gemini-specific code lives in `app/llm/gemini.py`, so switching providers (e.g. to Claude if Mary prefers) changes one module.

### 2.2 Stateless backend

Vercel functions don't reliably share memory between requests, so the server keeps **no conversation state**:

- **Within a turn:** the full native tool-calling transcript (including Gemini `thoughtSignature` parts, which go back verbatim) lives in memory only for the duration of the request. *Verified in Phase 0:* signatures arrive on the first function-call part of each response (also on final text), and follow-up turns built from plain-text history (no signatures) work correctly.
- **Across turns:** the browser stores a compact history and sends it with every request (§7).

Benefits: works on serverless, nothing is lost on restart, and the context stays small by design. The client can only send plain text (no fake tool calls), so a tampered history can't forge tool results.

---

## 3. Architecture

```text
Browser (React)
  │  POST /api/chat {question, history[]}  →  text/event-stream
  ▼
FastAPI  (/api/chat)
  └─ agent loop  (app/agent/loop.py)
       ├─ LLM: Gemini generateContent (app/llm/gemini.py)
       ├─ tool run_sql      → guard (dry run) → BigQuery → result store (per request)
       └─ tool create_chart → validate against stored result → chart event
  prompts: system.md + ga4_notes.md (all dataset-specific knowledge lives here)
```

---

## 4. Agent loop (the core)

```text
contents = render(history) + [user question]
for iteration in 1..MAX_ITERATIONS (10):
    response = gemini.generate(system, contents, tools)
    contents.append(response.content)                 # verbatim, keeps thoughtSignature
    calls = response.function_calls
    if not calls:
        return final text                              # answer
    results = [execute(call) for call in calls]        # Gemini may return several calls at once
    contents.append(one user turn with all functionResponses)
    emit progress events
# cap reached:
response = gemini.generate(..., tool calling disabled, "summarize what you found so far")
return final text
```

Rules:

- **Parallel calls:** every function call in a response gets a response, sent back together in one turn.
- **Tool failures never crash the request.** Exceptions, SQL errors and validation errors go back to the model as `{"error": "..."}` so it can correct itself.
- **Iteration cap** of 10, then one final call with tool calling disabled (`toolConfig.functionCallingConfig.mode = NONE`) to force an answer.
- **Finish reasons:** `MAX_TOKENS`, `SAFETY` and similar endings produce a clear user-facing error, not a silent empty answer.
- **Result size sent to the model:** at most `MODEL_MAX_ROWS` (100) rows, plus `row_count` and `truncated: true|false`. The prompt tells the model to aggregate in SQL instead of paging.

**Row limits (two numbers only):**

| Limit | Default | Applies to |
|---|---|---|
| `BQ_MAX_ROWS` | 500 | Rows fetched from BigQuery and kept for the request: shown in the UI table and used for charts |
| `MODEL_MAX_ROWS` | 100 | The first N of those rows, sent back to the model in the tool result |

`row_count` is always the true total, so both the model and the UI know when results were cut.
- **Retries:** the HTTP layer retries 429/5xx up to 2 times with backoff. Everything else surfaces as an error event.

---

## 5. Tools

Only two tools. Dataset knowledge goes in the prompt (§6), not in a schema-dump tool.

### 5.1 `run_sql`

```json
// input
{ "sql": "SELECT ...", "purpose": "Top 10 products by item revenue, Dec 2020" }
// success
{ "query_id": "q1", "columns": [{"name": "item_name", "type": "STRING"}, ...],
  "rows": [...≤100...], "row_count": 10, "truncated": false, "bytes_processed": 123456 }
// failure
{ "query_id": "q2", "error": "Unrecognized name: revenue at [3:5]" }
```

`purpose` is shown to the user as the step label.

**Guard (`app/bigquery/guard.py`), in order:**

1. **Dry run.** Reject unless the job's statement type is `SELECT`. This rejects DML, DDL, scripts and multi-statement queries using BigQuery's own parser rather than a regex.
2. **Byte cap.** Reject if the dry-run estimate exceeds `BQ_MAX_BYTES_BILLED`. The same cap is also set as `maximum_bytes_billed` on the real job.
3. **Run** with a job timeout (`BQ_TIMEOUT_SECONDS`, default 30) and fetch at most `BQ_MAX_ROWS` rows (see §4).
4. **Least privilege.** The service account has only *BigQuery Job User* on our project (the public dataset is already readable by everyone), so it cannot write anywhere.

Values are converted to JSON-safe types (`Decimal` → float, dates → ISO strings).

### 5.2 `create_chart`

```json
{ "query_id": "q1", "type": "bar|line|kpi", "title": "...",
  "x": "item_name", "y": ["revenue"] }
```

- `bar` / `line`: `x` is one column; `y` is 1–3 numeric columns (comparisons such as Nov vs Dec are pivoted in SQL into two `y` columns).
- `kpi`: single-row result; `y[0]` is the value; `x` is omitted.
- **Validation:** the query exists and succeeded, columns exist, `y` columns are numeric, `kpi` has one row, `bar` has ≤ 50 rows. On failure the error goes back to the model.
- **The chart carries no data.** The backend attaches the rows from the stored query result. A chart can't show a number BigQuery didn't return.
- No chart is required. Every successful query is also shown as a table, so the model charts only when it helps.

---

## 6. Prompts (`app/agent/prompts/`)

### 6.1 `system.md` — behaviour

- Role: data analyst for the Google Merchandise Store's GA4 export.
- Every number in the answer must come from a query result in this conversation. Never estimate.
- Use as many queries as needed; on an error, read it and fix the SQL.
- Prefer aggregated, small results; always filter dates with `_TABLE_SUFFIX`.
- Narrative: lead with the answer, then 2–4 supporting points, then caveats. Keep facts separate from interpretation; no causal claims.
- **Clarification rule:** ask a question only when it's unclear *what* to analyse (e.g. "What performed best?"). When only the *metric* is unclear (e.g. "top products"), pick the standard one (revenue), say so in one line, and offer alternatives.
- Call `create_chart` when a chart adds something a table doesn't.

### 6.2 `ga4_notes.md` — dataset knowledge (verified in Phase 0; `backend/app/agent/prompts/ga4_notes.md` is now the source of truth)

- Table: `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`, one table per day (`events_YYYYMMDD`), location `US`.
- Range **2020-11-01 → 2021-01-31**. "December" = Dec 2020; relative dates ("last month") are anchored to 2021-01-31.
- Users = `user_pseudo_id`. Sessions = (`user_pseudo_id`, `ga_session_id` from `event_params`).
- The `event_params` unnest pattern for string and int values.
- Revenue:
  - Order revenue: `ecommerce.purchase_revenue_in_usd` on `event_name = 'purchase'`.
  - Item revenue: `items.item_revenue_in_usd` after `UNNEST(items)`.
  - **Never sum order revenue after unnesting items** (double counting).
- Funnel events: `view_item`, `add_to_cart`, `begin_checkout`, `purchase`, etc.
- `traffic_source.*` = the source that **first acquired the user**, not the session's source. State this caveat in channel answers. Check whether session-level `source`/`medium` exist in `event_params`.
- Device: `device.category`. Geography: `geo.country`.
- Obfuscation: placeholders such as `<Other>` and `(data deleted)`; mention them when they appear in results.
- Column reference: a curated list of the fields above with types (not a full schema dump).

---

## 7. API contract

### Request

```json
POST /api/chat
{
  "question": "What about December?",
  "history": [
    { "question": "Top 5 products by revenue?",
      "answer": "…narrative…",
      "queries": [ { "purpose": "...", "sql": "...", "columns": ["item_name","revenue"],
                     "preview": [["Google Hoodie", 1234.5], "...≤10 rows"], "row_count": 5 } ] }
  ]
}
```

- History is rendered into earlier user/model turns: the model turn contains the answer plus a short "queries run" note (SQL + preview), so follow-ups can reuse the filters and definitions.
- Limits: last 10 turns, each field size-capped, request ≤ 200 KB. Over the limit, the oldest turns are dropped.

### Response: `text/event-stream`

| Event | Payload |
|---|---|
| `step` | `{query_id, purpose, sql}` — query started |
| `query_result` | `{query_id, columns, rows (≤ BQ_MAX_ROWS), row_count, truncated, bytes_processed, duration_ms}` |
| `query_error` | `{query_id, error}` (the model will usually retry) |
| `chart` | `{query_id, type, title, x, y}` |
| `answer` | `{text}` (markdown) |
| `done` | `{turn}` — the compact history entry for the client to store |
| `error` | `{message, retryable}` — friendly message; details only in server logs |

The frontend reads the stream with `fetch` + `ReadableStream` (EventSource doesn't support POST). Answer text arrives in one piece; word-by-word streaming is out of scope.

---

## 8. Frontend

```text
frontend/src/
  App.tsx                 layout, conversation state (useReducer)
  components/
    MessageList.tsx
    UserMessage.tsx
    AssistantMessage.tsx  steps → charts → narrative
    StepList.tsx          collapsible: purpose, SQL, duration, bytes, DataTable
    Chart.tsx             Recharts bar/line; delegates kpi
    KpiCard.tsx
    DataTable.tsx
    Composer.tsx          input + send; disabled while a turn is running
    ErrorNotice.tsx       message + Retry
  lib/
    api.ts                POST + SSE parsing → typed events
    types.ts              event and message types (mirror §7)
```

- States: idle, running (live steps), done, error (retry resends the same question with the same history).
- If a chart spec doesn't match its data, fall back to the table. Never crash the message.
- Minimal hand-written CSS. No component libraries.

---

## 9. Backend layout

```text
backend/
  app/
    main.py               FastAPI app, /api/chat, /api/health, access-code check
    config.py             env vars → settings
    agent/
      loop.py             §4
      tools.py            declarations + handlers for run_sql / create_chart
      history.py          compact history ⇄ Gemini contents
      prompts/system.md, ga4_notes.md
    llm/gemini.py         REST client: request building, retries, response parsing
    bigquery/
      client.py           run query, convert values
      guard.py            dry run, statement type, byte cap
  tests/
  evals/
    golden.yaml           questions + reference SQL + key values
    run_evals.py
```

No base classes or registries unless a second implementation actually exists.

---

## 10. Errors

| Case | Behaviour |
|---|---|
| SQL error | Returned to the model; it retries. The user sees the failed step in the step list |
| Guard rejection | Same as an SQL error, with a clear reason |
| Empty result | The model says no matching data was found and what it checked |
| Gemini 429/5xx | 2 retries, then an `error` event with `retryable: true` |
| Gemini safety/max-tokens finish | `error` event with a plain explanation |
| Iteration cap | Forced summary turn (§4) |
| Invalid chart | Validation error to the model; the frontend falls back to the table if one slips through |
| Network failure mid-stream | Frontend shows the error with Retry |

Credentials, stack traces and raw BigQuery job details never reach the client.

---

## 11. Configuration

```text
GEMINI_API_KEY=
GEMINI_MODEL=                 # chosen in Phase 0 from the models the key can access
GOOGLE_CLOUD_PROJECT=         # project that runs (and is billed for) query jobs
GOOGLE_APPLICATION_CREDENTIALS=  # local: path to the service-account key file (outside the repo)
GCP_SERVICE_ACCOUNT_JSON=     # deploy only: the key file contents
BQ_LOCATION=US
BQ_MAX_BYTES_BILLED=3000000000    # 3 GB: full scan is 3.6 GB; the heaviest realistic query (event_params over all days) is ~1.4 GB
BQ_TIMEOUT_SECONDS=30
BQ_MAX_ROWS=500
MODEL_MAX_ROWS=100
APP_ACCESS_CODE=              # optional; when set, /api/chat requires it (protects the API key on the public link)
```

`.env.example` committed; `.env` git-ignored.

---

## 12. Observability

One structured log line per event: `request_id`, `iteration`, `tool`, `purpose`, `sql`, `status`, `bytes_processed`, `duration_ms`, LLM latency and token counts. No secrets, no full result rows.

---

## 13. Testing

**Unit tests (pytest), with fakes and no network:**

- Guard: rejects non-`SELECT` statement types, scripts and over-cap byte estimates; accepts a valid `SELECT`.
- Loop with a scripted fake LLM:
  - single tool call → answer
  - parallel calls answered in one turn
  - SQL error → corrected query
  - chart validation error → corrected chart
  - iteration cap → forced summary
- History rendering: size caps and turn dropping.
- One API test: `/api/chat` streams the expected event sequence with fakes.

**Golden evals (`evals/`), run against real BigQuery and Gemini.** Priority: the questions and reference SQL are core (written in Phase 0; they're how we check the dataset notes and answer correctness). The `run_evals.py` runner is lower priority than a working product and is the first thing cut after deploy.

- ~8 questions covering the categories below, each with hand-written reference SQL.
- `run_evals.py` computes the reference values, runs the agent, checks the key value appears in the answer or result rows (±1%), and prints a pass/fail table.

Question categories: total users · top products by revenue · revenue over time · Nov vs Dec · revenue by traffic source · mobile vs desktop · high views but low purchase rate · a 3-turn follow-up chain (top 5 → December → vs November) · an ambiguous question ("What performed best?").

**Manual checks:** send a question, see the steps live, chart renders, follow-up works, error + retry, mobile width.

---

## 14. Scope

**In:** everything above.

**Cut / deferred** (each goes in the decision log):

- Word-by-word answer streaming
- Saved conversations, auth and accounts (the access code is the only gate)
- Query result cache
- Pie charts and other chart types
- Stop/cancel button
- Automatic check that each number in the narrative matches a query result (40h list)
- Generic multi-dataset support (dataset knowledge is isolated in `ga4_notes.md` + `GA4` table constants, nothing more)

**Never:** LangChain/LlamaIndex/agent frameworks, Gemini automatic function calling, UI component libraries, vector stores or RAG.

---

## 15. Plan (~8h)

| Phase | Time | Output |
|---|---|---|
| 0. Setup + data check | 0.75h | GCP auth, model choice, verify §6.2, golden questions + reference SQL |
| 1. Backend core | 2.5h | BigQuery client + guard, Gemini client, loop, tools, SSE endpoint, unit tests |
| 2. Frontend | 2h | Chat, stream handling, step list, charts, tables, markdown, errors |
| 3. Prompt + eval tuning | 1.5h | Run evals, refine prompts and notes |
| 4. Docs + deploy | 1.25h | README, decision log, Vercel deploy, access code |

**If behind, cut in this order:** deploy → `run_evals.py` runner (run the golden questions by hand instead) → progress streaming (fall back to one JSON response).

---

## 16. Assumptions

- "Our store" = Google Merchandise Store; revenue is in USD; dates are relative to the dataset's range.
- React counts as a framework; "no UI library" means no component or chat-UI kits **[Mary]**.
- Chart and markdown libraries are allowed **[Mary]**.
- Any LLM provider is acceptable; Gemini because the key is already available **[Mary]**.
- Single-user demo scale; no persistence needed.
- BigQuery sandbox (no billing) is enough; usage stays far under the free tier.

---

## 17. Deliverables

- **README:** overview, architecture diagram, agent loop walkthrough, tools, dataset notes, local setup, env vars, deploy steps, design decisions, limitations, future work.
- **`DECISIONS.md` (one page):** assumptions, cuts, where we got stuck and what we did about it, the next 40 hours. Updated as we go, not written at the end.
