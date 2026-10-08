"""The agent loop: the model calls tools until it can answer, and progress streams out as events."""

import logging
from collections.abc import Iterator
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


def _load_system_prompt() -> str:
    return "\n\n".join((PROMPTS_DIR / name).read_text() for name in ("system.md", "ga4_notes.md"))


class Agent:
    def __init__(self, llm: LLM, runner: QueryRunner, max_iterations: int = MAX_ITERATIONS):
        self._llm = llm
        self._runner = runner
        self._max_iterations = max_iterations
        self._system_prompt = _load_system_prompt()

    def run(self, question: str, past_turns: list[history.Turn]) -> Iterator[Event]:
        log.info("question=%r history_turns=%d", question, len(past_turns))
        toolbox = Toolbox(self._runner)
        contents = history.to_contents(past_turns) + [gemini.user_text(question)]

        try:
            for _ in range(self._max_iterations):
                reply = self._llm.generate(self._system_prompt, contents, DECLARATIONS)
                contents.append(reply.content)
                if not reply.function_calls:
                    break  # plain text: this is the answer

                results = []
                for call in reply.function_calls:
                    result = yield from toolbox.execute(call)  # streams query events as it runs
                    log.info("tool=%s args=%s error=%s", call.name, call.args, result.get("error"))
                    results.append((call, result))
                contents.append(gemini.function_responses(results))

            if reply.function_calls:
                # Out of rounds: ask once more with tools disabled, so it must answer.
                system = f"{self._system_prompt}\n\n{WRAP_UP_INSTRUCTION}"
                reply = self._llm.generate(system, contents, DECLARATIONS, allow_tool_calls=False)

            if not reply.text:
                raise LLMError("The AI returned an empty answer. Please retry.", retryable=True)
        except LLMError as error:
            log.warning("llm error: %s", error)
            yield Event("error", {"message": str(error), "retryable": error.retryable})
            return

        yield Event("answer", {"text": reply.text})
        turn = history.summarize_turn(question, reply.text, list(toolbox.queries.values()))
        yield Event("done", {"turn": turn.model_dump()})
