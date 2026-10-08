"""The agent loop: the model calls tools until it can answer, and progress streams out as events."""

import logging
import time
import uuid
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any, Protocol

from app.agent import history
from app.agent.events import Event
from app.agent.tools import DECLARATIONS, QueryRunner, Toolbox
from app.llm import gemini
from app.llm.gemini import LLMError, Reply

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
MAX_ITERATIONS = 10
WRAP_UP_INSTRUCTION = (
    "You have reached the limit of tool calls for this question. Answer now using only "
    "the query results you already have, and say what you could not check."
)


class LLM(Protocol):
    def generate(
        self,
        system: str,
        contents: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        allow_tool_calls: bool = True,
    ) -> Reply: ...


def load_system_prompt() -> str:
    return "\n\n".join((PROMPTS_DIR / name).read_text() for name in ("system.md", "ga4_notes.md"))


class Agent:
    def __init__(
        self, llm: LLM, runner: QueryRunner, model_max_rows: int, max_iterations: int = MAX_ITERATIONS
    ):
        self._llm = llm
        self._runner = runner
        self._model_max_rows = model_max_rows
        self._max_iterations = max_iterations
        self._system_prompt = load_system_prompt()

    def run(self, question: str, past_turns: list[history.Turn]) -> Iterator[Event]:
        """Answers one question, yielding progress events and finishing with `done` or `error`."""
        turn_id = uuid.uuid4().hex[:8]
        started = time.monotonic()
        log.info("turn=%s question=%r history_turns=%d", turn_id, question, len(past_turns))

        toolbox = Toolbox(self._runner, self._model_max_rows)
        contents = history.to_contents(past_turns) + [gemini.user_text(question)]
        try:
            answer = yield from self._loop(turn_id, contents, toolbox)
        except LLMError as error:
            log.warning("turn=%s llm_error=%r", turn_id, str(error))
            yield Event("error", {"message": str(error), "retryable": error.retryable})
            return

        log.info(
            "turn=%s done in %.1fs, queries=%d", turn_id, time.monotonic() - started, len(toolbox.queries)
        )
        yield Event("answer", {"text": answer})
        summary = history.summarize_turn(question, answer, list(toolbox.queries.values()))
        yield Event("done", {"turn": summary.model_dump()})

    def _loop(
        self, turn_id: str, contents: list[dict[str, Any]], toolbox: Toolbox
    ) -> Generator[Event, None, str]:
        for iteration in range(1, self._max_iterations + 1):
            reply = self._generate(turn_id, iteration, self._system_prompt, contents)
            contents.append(reply.content)
            if not reply.function_calls:
                return _final_text(reply)

            results = []
            for call in reply.function_calls:
                result = yield from toolbox.execute(call)
                log.info("turn=%s tool=%s args=%s result=%s", turn_id, call.name, call.args, _brief(result))
                results.append((call, result))
            contents.append(gemini.function_responses(results))

        log.warning("turn=%s hit the %d-iteration limit, forcing an answer", turn_id, self._max_iterations)
        system = f"{self._system_prompt}\n\n{WRAP_UP_INSTRUCTION}"
        reply = self._generate(turn_id, self._max_iterations + 1, system, contents, allow_tool_calls=False)
        return _final_text(reply)

    def _generate(
        self,
        turn_id: str,
        iteration: int,
        system: str,
        contents: list[dict[str, Any]],
        allow_tool_calls: bool = True,
    ) -> Reply:
        started = time.monotonic()
        reply = self._llm.generate(system, contents, DECLARATIONS, allow_tool_calls=allow_tool_calls)
        log.info(
            "turn=%s iteration=%d llm=%.1fs tool_calls=%d tokens_in=%s tokens_out=%s",
            turn_id,
            iteration,
            time.monotonic() - started,
            len(reply.function_calls),
            reply.usage.get("promptTokenCount"),
            reply.usage.get("candidatesTokenCount"),
        )
        return reply


def _final_text(reply: Reply) -> str:
    if not reply.text:
        raise LLMError("The AI returned an empty answer. Please retry.", retryable=True)
    return reply.text


def _brief(result: dict[str, Any]) -> str:
    if "error" in result:
        return f"error: {result['error']}"
    if "row_count" in result:
        return f"{result['query_id']} rows={result['row_count']}"
    return "ok"
