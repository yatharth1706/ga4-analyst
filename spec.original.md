# GA4 Agentic Data Analysis App

## 1. Objective

Build a standalone conversational data-analysis application using Google's public GA4 ecommerce demo dataset in BigQuery.

The application should allow a user to ask natural-language questions about the dataset and receive:

1. Accurate analysis based on actual BigQuery data
2. Relevant visualizations when useful
3. A written narrative explaining the findings
4. Follow-up questions in the same conversation, with context preserved

The application should feel like a normal conversational data analyst.

This is an ~8-hour technical assessment. Prioritize correctness, reliability, clean architecture, and thoughtful engineering over breadth or visual polish.

---

# 2. Core Requirements

The application must support:

### Conversational analysis

Example:

User:
> What were our top 10 products by revenue?

Assistant:
> [analysis + chart]

User:
> What about just December?

Assistant:
> [December analysis + chart]

User:
> How does that compare with November?

Assistant:
> [comparison + chart]

The assistant must understand follow-up questions using conversation history.

---

# 3. Dataset

Use Google's public GA4 ecommerce demo dataset:

`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`

Dataset documentation:

https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset

The application is specifically optimized for this dataset unless the requirements are clarified otherwise.

Do NOT build a generic multi-dataset platform.

The architecture should nevertheless keep dataset-specific concerns reasonably isolated so another dataset could theoretically be added later.

---

# 4. High-Level Architecture

Use a simple architecture:

```text
┌─────────────────────────────────────────────┐
│                  Frontend                   │
│                                             │
│  Chat UI                                    │
│  Messages                                   │
│  Charts                                     │
│  Loading / error states                     │
└──────────────────────┬──────────────────────┘
                       │
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────┐
│                  Backend                    │
│                                             │
│  Chat API                                   │
│      │                                      │
│      ▼                                      │
│  Agent Loop                                 │
│      │                                      │
│      ├── LLM                                │
│      ├── Schema Tool                        │
│      └── SQL Execution Tool                 │
│                                             │
│      ▼                                      │
│  BigQuery                                   │
└─────────────────────────────────────────────┘
```

Keep the implementation simple and maintainable.

Avoid unnecessary infrastructure.

Do NOT introduce:

- LangChain
- LlamaIndex
- AutoGen
- CrewAI
- Agent frameworks
- Vector databases
- Redis
- Kafka
- Temporal
- Kubernetes
- Microservices

unless there is a compelling reason.

The assignment specifically requires implementing the agentic loop ourselves.

---

# 5. Agentic Loop

This is the most important part of the implementation.

Implement the agent loop manually using the chosen LLM provider's raw HTTP API or official SDK messages/tool-calling API.

Conceptually:

```python
messages = conversation_history

while True:
    response = llm.chat(
        messages=messages,
        tools=available_tools
    )

    if response.contains_tool_call:
        tool_result = execute_tool(response.tool_call)

        messages.append(response)
        messages.append(tool_result)

        continue

    return response
```

The loop should allow the model to:

1. Understand the user's question
2. Decide whether it needs additional information
3. Inspect schema if necessary
4. Generate SQL
5. Execute SQL
6. Inspect the result
7. Decide whether another query is necessary
8. Recover from SQL errors
9. Produce the final analysis

Do not implement this as a fixed pipeline such as:

```text
question → SQL → answer
```

The LLM should be able to make multiple tool calls when necessary.

---

# 6. Agent Tools

Keep the initial tool set small.

## Tool 1: get_schema

Purpose:

Allow the agent to inspect the available GA4 dataset schema.

Return useful information such as:

- table name
- columns
- data types
- nested/repeated fields
- useful field descriptions where available

The tool should expose enough information for the LLM to correctly construct GA4 BigQuery queries.

Schema-specific knowledge can also be included in the system prompt if useful.

---

## Tool 2: execute_sql

Purpose:

Execute a read-only SQL query against BigQuery.

Input:

```json
{
  "sql": "SELECT ..."
}
```

Return:

```json
{
  "success": true,
  "columns": [...],
  "rows": [...]
}
```

or:

```json
{
  "success": false,
  "error": "..."
}
```

The agent should receive SQL errors and have the opportunity to correct the query.

Example:

```text
LLM
 ↓
SQL
 ↓
BigQuery
 ↓
SQL ERROR
 ↓
LLM
 ↓
corrected SQL
 ↓
BigQuery
 ↓
result
```

---

# 7. SQL Safety

The application must never execute arbitrary write operations generated by the model.

Only read-only queries are allowed.

At minimum reject:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- MERGE
- TRUNCATE
- multiple SQL statements

Preferably validate that the query is a single SELECT statement.

Also enforce reasonable:

- result row limits
- query timeout
- BigQuery query limits where available

Never expose service-account credentials to the frontend.

---

# 8. SQL Generation

The model should be instructed:

- Never invent numerical values
- Quantitative claims must come from actual query results
- Inspect schema when necessary
- Use appropriate GA4 event names
- Correctly handle nested/repeated fields using UNNEST
- Prefer efficient queries
- Avoid unnecessarily large result sets
- Use aggregations when appropriate
- Limit results when possible
- Clearly distinguish facts from interpretations

Example:

Bad:

> Revenue was approximately $200K.

if the model never queried revenue.

Good:

```text
SQL → BigQuery → result → analysis
```

---

# 9. System Prompt

Create a dedicated system prompt rather than embedding instructions throughout the code.

The prompt should establish the model as a GA4 ecommerce data analyst.

Core principles:

```text
You are an expert data analyst working with Google's GA4 ecommerce demo dataset.

Your responsibility is to answer user questions using actual data from BigQuery.

Never invent numbers.

For quantitative questions, retrieve the necessary data using SQL before answering.

You may use the provided tools to inspect the schema and execute SQL.

You may execute multiple queries if necessary.

If a query fails, inspect the error and correct the query.

If the available result is insufficient to answer the question, perform another analysis.

Use conversation history to understand follow-up questions.

When a visualization would meaningfully improve understanding, provide visualization metadata.

Clearly distinguish observed facts from interpretations or hypotheses.

Do not claim causality unless the available data supports it.
```

The exact prompt can be refined during implementation.

---

# 10. Structured Final Response

The final agent response should be structured rather than returning arbitrary frontend code.

Conceptually:

```json
{
  "narrative": "Revenue increased by 18% between November and December...",
  "visualizations": [
    {
      "type": "line",
      "title": "Revenue by Month",
      "x": "month",
      "y": "revenue"
    }
  ]
}
```

The exact schema can be adapted to the chosen LLM.

The frontend is responsible for rendering the visualization.

The model should NOT generate JavaScript/React code for charts.

---

# 11. Visualization System

Use a visualization library for rendering charts.

Do not build chart primitives manually.

Initially support a small number of useful chart types:

- line chart
- bar chart
- optionally pie/donut
- KPI/stat card

Prefer a small reliable visualization system over supporting many chart types.

Example visualization specification:

```json
{
  "type": "bar",
  "title": "Top Products by Revenue",
  "x": "product_name",
  "y": "revenue"
}
```

The frontend should validate the visualization specification before rendering.

If the data is not appropriate for a chart, do not force a visualization.

A simple table may sometimes be more useful than a chart.

---

# 12. Conversational Context

Each conversation should maintain message history.

At minimum preserve:

```text
user message
assistant response
tool call
tool result
assistant response
...
```

Follow-up questions must have access to previous conversation context.

Example:

```text
User:
What were our top products?

Assistant:
...

User:
What about December?

Assistant:
...
```

The second question should be interpreted in the context of the first.

Do not build a separate vector-memory system.

Normal conversation history is sufficient for this scope.

---

# 13. Frontend

Build a simple custom chat interface.

The UI should contain:

- conversation area
- user messages
- assistant messages
- charts
- tables where appropriate
- loading state
- error state
- input box
- submit/send button
- ability to continue the conversation

Visual polish is secondary to functionality.

Do not use pre-built UI/component libraries.

If React/Next.js is permitted, use it as the application framework but implement the actual UI components yourself.

Avoid:

- Shadcn UI
- Material UI
- Ant Design
- Chakra
- pre-built AI chat interfaces
- dashboard templates

Lightweight utility libraries such as Markdown rendering or syntax highlighting may be used if permitted by the assessment requirements.

---

# 14. Suggested Frontend Structure

Keep it simple.

Possible structure:

```text
frontend/
├── components/
│   ├── Chat.tsx
│   ├── Message.tsx
│   ├── ChatInput.tsx
│   ├── Chart.tsx
│   ├── DataTable.tsx
│   └── LoadingState.tsx
│
├── lib/
│   └── api.ts
│
└── app/
    └── page.tsx
```

Adapt based on the selected framework.

---

# 15. Backend Structure

Prefer a small, obvious architecture.

Possible structure:

```text
backend/
├── agent/
│   ├── agent.py
│   ├── prompts.py
│   └── tools.py
│
├── bigquery/
│   ├── client.py
│   └── schema.py
│
├── conversations/
│   └── service.py
│
├── api/
│   └── chat.py
│
└── main.py
```

Do not create abstractions simply for the sake of abstraction.

The agent loop should be easy for another engineer to understand.

---

# 16. Example Questions the Application Should Handle

Test at least these categories.

### Basic aggregation

> How many users visited the store?

### Product analysis

> What were the top 10 products by revenue?

### Time series

> How did revenue change over time?

### Comparison

> Compare revenue between November and December.

### Segmentation

> Which traffic source generated the most revenue?

### Device analysis

> How does revenue differ between mobile and desktop users?

### Ecommerce analysis

> Which products generated the most purchases?

### Multi-step reasoning

> Which products had high views but relatively low purchase rates?

### Follow-up

```text
What were the top 5 products by revenue?
```

Follow-up:

```text
What about December?
```

Follow-up:

```text
How does that compare with November?
```

### Clarification

Test ambiguous questions such as:

> What performed best?

The agent should ask for clarification if the metric is genuinely ambiguous rather than arbitrarily selecting one.

---

# 17. Error Handling

The application should gracefully handle:

### SQL errors

The agent gets the error and can retry.

### LLM errors

Return a useful user-facing error.

### BigQuery errors

Do not expose sensitive credentials or implementation details.

### Empty results

The assistant should explain that no matching data was found.

### Invalid visualization

Do not crash the chat. Fall back to narrative/table output.

### Network/API failure

Display a useful retryable error.

---

# 18. Loading / Agent Progress

If practical, expose useful progress to the user.

For example:

```text
Analyzing your question...
Querying GA4 data...
Comparing results...
Preparing analysis...
```

Do not over-engineer streaming if it would compromise the core implementation.

---

# 19. Configuration

Use environment variables for credentials/configuration.

Example:

```text
LLM_API_KEY=
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=
```

Never commit credentials.

Provide:

```text
.env.example
```

---

# 20. Deployment

The application should ideally be deployable as a standalone application.

The exact hosting provider is flexible.

Document:

1. Environment variables
2. BigQuery setup
3. LLM API key setup
4. Local development
5. Deployment instructions

If deployment takes significant time, prioritize getting the core application working first.

---

# 21. Testing

Do not attempt exhaustive testing within the timebox.

Focus on high-value tests.

At minimum test:

### Agent

- tool selection
- multi-step tool calls
- SQL error recovery
- final response parsing

### SQL safety

- reject write statements
- reject multiple statements
- accept valid SELECT queries

### API

- successful chat
- invalid request
- downstream error

### Frontend

Manually verify:

- sending a question
- receiving analysis
- rendering a chart
- follow-up question
- loading state
- error state

---

# 22. Observability / Debugging

For development, log enough information to debug the agent:

```text
conversation_id
user question
tool called
tool arguments
tool result status
SQL execution time
LLM turn number
```

Do not log secrets.

Keep production logs concise.

---

# 23. Scope Constraints

This is an ~8-hour implementation.

Do NOT spend time building:

- authentication
- user accounts
- multi-tenancy
- arbitrary dataset ingestion
- RAG
- embeddings
- vector databases
- multi-agent systems
- complex workflow engines
- real-time collaboration
- advanced permissions
- sophisticated design systems
- elaborate animations

Prioritize:

1. Agent loop
2. Correct SQL
3. BigQuery integration
4. Conversational follow-ups
5. Useful visualizations
6. Good narrative answers
7. Error handling
8. Clean code

---

# 24. Engineering Principles

The implementation should be:

- simple
- explicit
- maintainable
- easy to debug
- easy to explain in an interview

Avoid unnecessary abstractions.

Prefer straightforward code over clever code.

Do not generate large amounts of boilerplate.

Do not create abstractions unless they solve a real problem.

The code will be reviewed manually and discussed during a technical interview.

Every major architectural decision should be explainable.

---

# 25. Definition of Done

The MVP is complete when a user can:

1. Open the application
2. Ask a natural-language question about GA4 data
3. See the system analyze the question
4. See actual BigQuery-derived results
5. Receive a written explanation
6. Receive an appropriate visualization when useful
7. Ask a follow-up question
8. Receive a context-aware answer
9. Recover gracefully from SQL/query errors
10. Run the application using documented setup instructions

---

# 26. README Requirements

The README should contain:

## Overview

What the application does.

## Architecture

Include a simple architecture diagram.

## Agent Loop

Explain:

```text
User
→ LLM
→ Tool
→ Tool Result
→ LLM
→ ...
→ Final Answer
```

## Tools

Explain each tool.

## Dataset

Explain the GA4 dataset and relevant schema considerations.

## Running locally

Step-by-step setup.

## Environment variables

Document required configuration.

## Design decisions

Briefly explain important choices.

## Limitations

Explicitly describe what was intentionally not built.

## Future improvements

Describe what would be built with more time.

---

# 27. Decision Log

Create a one-page decision log covering:

### Assumptions

What was assumed and why.

### Cut / Deprioritized

What was intentionally not built.

### Problems

Where implementation got stuck.

### Resolution

How the problem was solved.

### Additional 40 Hours

What would be improved with another 40 hours.

Keep this concise and honest.

---

# 28. Important Implementation Rule

Do not blindly implement every detail in this specification.

Use engineering judgment.

If a requirement conflicts with another requirement, prioritize:

1. Correctness
2. Security
3. Core agent functionality
4. Conversational experience
5. Visualization
6. UI polish

Before introducing a dependency, ask whether it materially improves the implementation.

The goal is not to build the largest application possible.

The goal is to build a small, reliable, well-engineered agentic data-analysis application that can be defended in a technical interview.