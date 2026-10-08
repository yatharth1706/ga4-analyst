import json

import pytest
from fastapi.testclient import TestClient

from app.agent.loop import Agent
from app.main import app, get_agent
from tests.fakes import REVENUE_BY_DEVICE, FakeLLM, FakeRunner, sql, text_reply, tool_reply


@pytest.fixture
def client():
    llm = FakeLLM(tool_reply(sql("SELECT device")), text_reply("Desktop leads."))
    runner = FakeRunner({"SELECT device": REVENUE_BY_DEVICE})
    app.dependency_overrides[get_agent] = lambda: Agent(llm, runner, model_max_rows=100)
    yield TestClient(app)
    app.dependency_overrides.clear()


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        event_line, data_line = block.split("\n")
        events.append((event_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))))
    return events


def test_chat_streams_agent_events(client):
    response = client.post("/api/chat", json={"question": "Revenue by device?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["query_started", "query_result", "answer", "done"]
    assert events[-1][1]["turn"]["answer"] == "Desktop leads."


def test_empty_question_is_rejected(client):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422


def test_unexpected_error_mid_stream_becomes_an_error_event(client):
    class BrokenAgent:
        def run(self, question, history):
            yield from ()
            raise RuntimeError("boom")

    app.dependency_overrides[get_agent] = BrokenAgent

    events = parse_sse(client.post("/api/chat", json={"question": "Hi"}).text)

    assert events == [
        ("error", {"message": "Something went wrong on our side. Please retry.", "retryable": True})
    ]
