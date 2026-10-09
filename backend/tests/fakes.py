"""Scripted stand-ins for Gemini and BigQuery, so agent tests run offline and deterministically."""

from typing import Any

from app.bigquery.client import Column, QueryError, QueryResult
from app.llm.gemini import FunctionCall, LLMError, Reply


def text_reply(text: str) -> Reply:
    return Reply(content={"role": "model", "parts": [{"text": text}]}, text=text, function_calls=[])


def tool_reply(*calls: tuple[str, dict[str, Any]]) -> Reply:
    function_calls = [FunctionCall(name, args) for name, args in calls]
    parts = [{"functionCall": {"name": name, "args": args}} for name, args in calls]
    return Reply(content={"role": "model", "parts": parts}, text="", function_calls=function_calls)


def sql(query: str, purpose: str = "test query") -> tuple[str, dict[str, Any]]:
    return ("run_sql", {"sql": query, "purpose": purpose})


def chart(query_id: str, chart_type: str, x: str | None, y: list[str]) -> tuple[str, dict[str, Any]]:
    return ("create_chart", {"query_id": query_id, "type": chart_type, "title": "Chart", "x": x, "y": y})


def result(columns: dict[str, str], rows: list[list[Any]], row_count: int | None = None) -> QueryResult:
    return QueryResult(
        columns=[Column(name, column_type) for name, column_type in columns.items()],
        rows=rows,
        row_count=len(rows) if row_count is None else row_count,
        bytes_processed=1000,
        duration_ms=5,
    )


REVENUE_BY_DEVICE = result(
    {"device": "STRING", "revenue": "FLOAT"},
    [["desktop", 208815.0], ["mobile", 146768.0], ["tablet", 6582.0]],
)


class FakeLLM:
    """Returns the scripted replies in order and records every request."""

    def __init__(self, *replies: Reply | LLMError):
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    def generate(self, system, contents, tools, allow_tool_calls=True) -> Reply:
        self.requests.append(
            {"system": system, "contents": list(contents), "allow_tool_calls": allow_tool_calls}
        )
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class FakeRunner:
    """Maps SQL text to a result (or a QueryError message) and records what ran."""

    def __init__(self, results: dict[str, QueryResult | str]):
        self._results = results
        self.executed: list[str] = []

    def run(self, sql: str) -> QueryResult:
        self.executed.append(sql)
        outcome = self._results[sql]
        if isinstance(outcome, str):
            raise QueryError(outcome)
        return outcome
