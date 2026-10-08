import logging
import secrets
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.events import Event
from app.agent.history import Turn
from app.agent.loop import Agent
from app.bigquery.client import BigQueryRunner
from app.config import Settings, load_settings
from app.llm.gemini import GeminiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="GA4 Analyst")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    history: list[Turn] = Field(default_factory=list, max_length=50)


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def get_agent() -> Agent:
    settings = get_settings()
    return Agent(
        llm=GeminiClient(settings.gemini_api_key, settings.gemini_model),
        runner=BigQueryRunner(settings),
        model_max_rows=settings.model_max_rows,
        max_iterations=settings.max_iterations,
    )


def check_access_code(
    settings: Annotated[Settings, Depends(get_settings)],
    x_access_code: Annotated[str | None, Header()] = None,
) -> None:
    if settings.access_code and not secrets.compare_digest(x_access_code or "", settings.access_code):
        raise HTTPException(status_code=401, detail="Invalid access code.")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", dependencies=[Depends(check_access_code)])
def chat(request: ChatRequest, agent: Annotated[Agent, Depends(get_agent)]) -> StreamingResponse:
    events = agent.run(request.question.strip(), request.history)
    return StreamingResponse(
        _to_sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _to_sse(events: Iterator[Event]) -> Iterator[str]:
    try:
        for event in events:
            yield event.to_sse()
    except Exception:
        # The response has already started streaming, so errors must travel as an event.
        log.exception("unexpected error while answering")
        yield Event("error", {"message": "Something went wrong on our side. Please retry.", "retryable": True}).to_sse()
