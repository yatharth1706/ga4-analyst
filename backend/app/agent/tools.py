"""The two tools the model can call: what it sees (declarations) and what runs (Toolbox)."""

import logging
from collections.abc import Generator
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from app.agent.events import Event
from app.bigquery.client import QueryError, QueryResult
from app.llm.gemini import FunctionCall

log = logging.getLogger(__name__)

CHART_TYPES = ("bar", "line", "kpi")
NUMERIC_TYPES = {"INTEGER", "INT64", "FLOAT", "FLOAT64", "NUMERIC", "BIGNUMERIC"}
MAX_BAR_ROWS = 50

DECLARATIONS = [
    {
        "name": "run_sql",
        "description": (
            "Run one read-only BigQuery Standard SQL SELECT against the GA4 dataset. "
            "Returns a query_id, the columns, the first rows, the total row_count and "
            "whether rows were truncated. On failure returns an error: fix the SQL and retry."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single SELECT statement."},
                "purpose": {
                    "type": "string",
                    "description": "Short label shown to the user, e.g. 'Revenue by month'.",
                },
            },
            "required": ["sql", "purpose"],
        },
    },
    {
        "name": "create_chart",
        "description": (
            "Show a chart of a successful query's result. The chart uses that query's rows; "
            "you only choose the columns. Use bar for categories, line for time series, "
            "kpi for a single headline number."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query_id": {"type": "string"},
                "type": {"type": "string", "enum": list(CHART_TYPES)},
                "title": {"type": "string"},
                "x": {
                    "type": "string",
                    "description": "Column for categories or time. Required for bar and line; omit for kpi.",
                },
                "y": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "1-3 numeric columns to plot. For kpi, exactly one.",
                },
            },
            "required": ["query_id", "type", "title", "y"],
        },
    },
]


class QueryRunner(Protocol):
    def run(self, sql: str) -> QueryResult: ...


@dataclass
class ExecutedQuery:
    query_id: str
    purpose: str
    sql: str
    result: QueryResult


class ChartError(Exception):
    pass


class Toolbox:
    """Executes the model's tool calls for one chat turn and remembers successful queries."""

    def __init__(self, runner: QueryRunner, model_max_rows: int):
        self._runner = runner
        self._model_max_rows = model_max_rows
        self._query_count = 0
        self.queries: dict[str, ExecutedQuery] = {}

    def execute(self, call: FunctionCall) -> Generator[Event, None, dict[str, Any]]:
        """Yields progress events while the tool runs; returns the response for the model."""
        handlers = {"run_sql": self._run_sql, "create_chart": self._create_chart}
        handler = handlers.get(call.name)
        if handler is None:
            return {"error": f"Unknown tool: {call.name}"}
        try:
            return (yield from handler(call.args))
        except Exception:
            log.exception("tool %s crashed", call.name)
            return {"error": f"{call.name} failed with an internal error."}

    def _run_sql(self, args: dict[str, Any]) -> Generator[Event, None, dict[str, Any]]:
        self._query_count += 1
        query_id = f"q{self._query_count}"
        sql = args.get("sql", "")
        purpose = args.get("purpose", "")
        yield Event("query_started", {"query_id": query_id, "purpose": purpose, "sql": sql})

        try:
            result = self._runner.run(sql)
        except QueryError as error:
            yield Event("query_error", {"query_id": query_id, "error": str(error)})
            return {"query_id": query_id, "error": str(error)}

        self.queries[query_id] = ExecutedQuery(query_id, purpose, sql, result)
        yield Event(
            "query_result",
            {
                "query_id": query_id,
                "columns": [asdict(column) for column in result.columns],
                "rows": result.rows,
                "row_count": result.row_count,
                "truncated": result.truncated,
                "bytes_processed": result.bytes_processed,
                "duration_ms": result.duration_ms,
            },
        )
        rows_for_model = result.rows[: self._model_max_rows]
        return {
            "query_id": query_id,
            "columns": [f"{column.name} ({column.type})" for column in result.columns],
            "rows": rows_for_model,
            "row_count": result.row_count,
            "truncated": result.row_count > len(rows_for_model),
        }

    def _create_chart(self, args: dict[str, Any]) -> Generator[Event, None, dict[str, Any]]:
        try:
            chart = validate_chart(args, self.queries)
        except ChartError as error:
            return {"error": str(error)}
        yield Event("chart", chart)
        return {"ok": True}


def validate_chart(args: dict[str, Any], queries: dict[str, ExecutedQuery]) -> dict[str, Any]:
    """Checks a chart request against the actual query result, so a bad spec never reaches the UI."""
    query_id = args.get("query_id")
    query = queries.get(query_id)
    if query is None:
        raise ChartError(f"Unknown query_id '{query_id}'. Use the query_id of a successful run_sql.")

    chart_type = args.get("type")
    if chart_type not in CHART_TYPES:
        raise ChartError(f"type must be one of {list(CHART_TYPES)}.")
    title = (args.get("title") or "").strip()
    if not title:
        raise ChartError("title is required.")

    x = None if chart_type == "kpi" else args.get("x") or None
    y = list(args.get("y") or [])
    column_types = {column.name: column.type for column in query.result.columns}
    unknown = [name for name in [x, *y] if name and name not in column_types]
    if unknown:
        raise ChartError(f"Columns {unknown} are not in {query_id}. Available: {list(column_types)}.")
    if not 1 <= len(y) <= 3:
        raise ChartError("y must list 1 to 3 columns.")
    non_numeric = [name for name in y if column_types[name] not in NUMERIC_TYPES]
    if non_numeric:
        raise ChartError(f"y columns must be numeric; {non_numeric} are not.")
    if query.result.truncated:
        raise ChartError("The result has more rows than were fetched. Aggregate further before charting.")

    row_count = query.result.row_count
    if chart_type == "kpi":
        if len(y) != 1 or row_count != 1:
            raise ChartError("A kpi chart needs a single-row result and exactly one y column.")
    elif not x:
        raise ChartError(f"A {chart_type} chart needs an x column.")
    elif chart_type == "bar" and row_count > MAX_BAR_ROWS:
        raise ChartError(f"Too many bars ({row_count}); limit the query to {MAX_BAR_ROWS} rows.")

    return {"query_id": query_id, "type": chart_type, "title": title, "x": x, "y": y}
