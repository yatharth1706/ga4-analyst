"""The compact conversation history the browser keeps and sends back with each question.

The server is stateless: each past turn is the question, the answer, and the queries
behind it (SQL plus a small preview), which is enough context for follow-ups.
"""

import json
from typing import Any

from pydantic import BaseModel, Field

from app.agent.tools import ExecutedQuery
from app.llm import gemini

MAX_TURNS_SENT_TO_MODEL = 10
PREVIEW_ROWS = 10
MAX_QUERIES_PER_TURN = 10
MAX_TEXT_CHARS = 10_000


class QueryRecord(BaseModel):
    purpose: str = Field(max_length=MAX_TEXT_CHARS)
    sql: str = Field(max_length=MAX_TEXT_CHARS)
    columns: list[str] = Field(max_length=100)
    preview: list[list[Any]] = Field(max_length=PREVIEW_ROWS)
    row_count: int


class Turn(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    answer: str = Field(max_length=MAX_TEXT_CHARS)
    queries: list[QueryRecord] = Field(default_factory=list, max_length=MAX_QUERIES_PER_TURN)


def to_contents(history: list[Turn]) -> list[dict[str, Any]]:
    contents = []
    for turn in history[-MAX_TURNS_SENT_TO_MODEL:]:
        contents.append(gemini.user_text(turn.question))
        contents.append(gemini.model_text(_answer_with_query_notes(turn)))
    return contents


def summarize_turn(question: str, answer: str, queries: list[ExecutedQuery]) -> Turn:
    return Turn(
        question=question,
        answer=answer[:MAX_TEXT_CHARS],
        queries=[
            QueryRecord(
                purpose=query.purpose[:MAX_TEXT_CHARS],
                sql=query.sql[:MAX_TEXT_CHARS],
                columns=[column.name for column in query.result.columns],
                preview=query.result.rows[:PREVIEW_ROWS],
                row_count=query.result.row_count,
            )
            for query in queries[:MAX_QUERIES_PER_TURN]
        ],
    )


def _answer_with_query_notes(turn: Turn) -> str:
    if not turn.queries:
        return turn.answer
    lines = [turn.answer, "", "[Queries behind this answer]"]
    for query in turn.queries:
        lines += [
            f"- {query.purpose}",
            f"  SQL: {query.sql}",
            f"  Result: {query.row_count} rows, columns {query.columns}, "
            f"first rows {json.dumps(query.preview)}",
        ]
    return "\n".join(lines)
