import httpx
import pytest

from app.llm import gemini
from app.llm.gemini import FunctionCall, GeminiClient, LLMError


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(gemini.time, "sleep", lambda _: None)


def client_with(responses: list[httpx.Response]) -> tuple[GeminiClient, list[httpx.Request]]:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return responses[len(requests) - 1]

    return GeminiClient("key", "model", transport=httpx.MockTransport(handler)), requests


def candidate(parts: list[dict], finish_reason: str = "STOP") -> httpx.Response:
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": finish_reason}]},
    )


def test_parses_text_and_function_calls():
    parts = [
        {"text": "thinking...", "thought": True},
        {"functionCall": {"name": "run_sql", "args": {"sql": "SELECT 1"}}, "thoughtSignature": "abc"},
        {"functionCall": {"name": "run_sql", "args": {"sql": "SELECT 2"}}},
    ]
    client, _ = client_with([candidate(parts)])

    reply = client.generate("system", [], tools=[])

    assert reply.text == ""
    assert [call.args["sql"] for call in reply.function_calls] == ["SELECT 1", "SELECT 2"]
    assert reply.content["parts"][1]["thoughtSignature"] == "abc"


def test_sends_key_in_header_and_disables_tools_when_asked():
    client, requests = client_with([candidate([{"text": "done"}])])

    client.generate("system", [], tools=[], allow_tool_calls=False)

    assert requests[0].headers["x-goog-api-key"] == "key"
    assert "key" not in str(requests[0].url)
    assert b'"mode":"NONE"' in requests[0].content


def test_retries_rate_limits_then_succeeds():
    client, requests = client_with([httpx.Response(429), httpx.Response(503), candidate([{"text": "ok"}])])

    assert client.generate("system", [], tools=[]).text == "ok"
    assert len(requests) == 3


def test_gives_up_after_retries_with_retryable_error():
    client, _ = client_with([httpx.Response(429)] * 3)

    with pytest.raises(LLMError) as error:
        client.generate("system", [], tools=[])
    assert error.value.retryable


def test_client_errors_are_not_retried():
    client, requests = client_with([httpx.Response(400)])

    with pytest.raises(LLMError):
        client.generate("system", [], tools=[])
    assert len(requests) == 1


def test_malformed_function_call_is_retried():
    client, _ = client_with([candidate([], "MALFORMED_FUNCTION_CALL"), candidate([{"text": "ok"}])])

    assert client.generate("system", [], tools=[]).text == "ok"


def test_max_tokens_is_an_error():
    client, _ = client_with([candidate([{"text": "partial"}], "MAX_TOKENS")])

    with pytest.raises(LLMError, match="too long"):
        client.generate("system", [], tools=[])


def test_function_responses_answer_every_call_in_one_turn():
    calls = [FunctionCall("run_sql", {}, id="a"), FunctionCall("create_chart", {})]

    turn = gemini.function_responses([(calls[0], {"rows": []}), (calls[1], {"ok": True})])

    assert turn["role"] == "user"
    assert [part["functionResponse"]["name"] for part in turn["parts"]] == ["run_sql", "create_chart"]
    assert turn["parts"][0]["functionResponse"]["id"] == "a"
    assert "id" not in turn["parts"][1]["functionResponse"]
