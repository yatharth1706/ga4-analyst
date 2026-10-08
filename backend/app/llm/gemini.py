"""Gemini over raw HTTP (generateContent), plus builders for its message format.

All Gemini-specific code lives in this module. The agent loop treats the
conversation (`contents`) as an opaque list built with the helpers at the bottom.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAYS_SECONDS = (0, 1, 3)


class LLMError(Exception):
    """The model call failed. The message is safe to show the user."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class FunctionCall:
    name: str
    args: dict[str, Any]
    id: str | None = None


@dataclass
class Reply:
    content: dict[str, Any]  # the model turn exactly as returned, to append to the conversation
    text: str
    function_calls: list[FunctionCall]
    usage: dict[str, Any] = field(default_factory=dict)


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 90,
        transport: httpx.BaseTransport | None = None,
    ):
        self._url = API_URL.format(model=model)
        self._http = httpx.Client(
            timeout=timeout_seconds, headers={"x-goog-api-key": api_key}, transport=transport
        )

    def generate(
        self,
        system: str,
        contents: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        allow_tool_calls: bool = True,
    ) -> Reply:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "tools": [{"functionDeclarations": tools}],
            "toolConfig": {
                "functionCallingConfig": {"mode": "AUTO" if allow_tool_calls else "NONE"}
            },
        }
        return _parse_reply(self._post(body))

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        last_error = LLMError("The AI service did not respond.", retryable=True)
        for delay in RETRY_DELAYS_SECONDS:
            time.sleep(delay)
            try:
                response = self._http.post(self._url, json=body)
            except httpx.TransportError as error:
                log.warning("gemini transport error: %s", error)
                last_error = LLMError("Could not reach the AI service.", retryable=True)
                continue

            if response.status_code != 200:
                log.warning("gemini http %s: %s", response.status_code, response.text[:500])
                last_error = _http_error(response.status_code)
                if response.status_code in RETRYABLE_STATUS:
                    continue
                raise last_error

            data = response.json()
            if _finish_reason(data) == "MALFORMED_FUNCTION_CALL":
                # Occasional model glitch; the same request usually succeeds on retry.
                log.warning("gemini returned a malformed function call, retrying")
                last_error = LLMError("The AI produced an invalid tool call.", retryable=True)
                continue
            return data
        raise last_error


def _http_error(status: int) -> LLMError:
    if status == 429:
        return LLMError("The AI service is rate-limited right now. Please retry shortly.", retryable=True)
    if status >= 500:
        return LLMError("The AI service had a temporary error. Please retry.", retryable=True)
    return LLMError("The AI service rejected the request.")


def _finish_reason(data: dict[str, Any]) -> str | None:
    candidates = data.get("candidates") or [{}]
    return candidates[0].get("finishReason")


def _parse_reply(data: dict[str, Any]) -> Reply:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = data.get("promptFeedback", {}).get("blockReason", "no answer returned")
        raise LLMError(f"The AI did not answer ({reason}).")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason", "STOP")
    if finish_reason == "MAX_TOKENS":
        raise LLMError("The answer got too long to finish. Try a narrower question.", retryable=True)
    if finish_reason != "STOP":
        raise LLMError(f"The AI stopped unexpectedly ({finish_reason}).", retryable=True)

    content = candidate.get("content") or {"role": "model", "parts": []}
    parts = content.get("parts", [])
    text = "".join(part["text"] for part in parts if "text" in part and not part.get("thought"))
    calls = [
        FunctionCall(
            name=part["functionCall"]["name"],
            args=part["functionCall"].get("args", {}),
            id=part["functionCall"].get("id"),
        )
        for part in parts
        if "functionCall" in part
    ]
    return Reply(content=content, text=text.strip(), function_calls=calls, usage=data.get("usageMetadata", {}))


def user_text(text: str) -> dict[str, Any]:
    return {"role": "user", "parts": [{"text": text}]}


def model_text(text: str) -> dict[str, Any]:
    return {"role": "model", "parts": [{"text": text}]}


def function_responses(results: list[tuple[FunctionCall, dict[str, Any]]]) -> dict[str, Any]:
    """All responses to one model turn go back together, in a single user turn."""
    parts = []
    for call, result in results:
        response = {"name": call.name, "response": result}
        if call.id:
            response["id"] = call.id
        parts.append({"functionResponse": response})
    return {"role": "user", "parts": parts}
