import json
from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    """A progress update streamed to the browser while the agent works."""

    type: str
    data: dict[str, Any]

    def to_sse(self) -> str:
        return f"event: {self.type}\ndata: {json.dumps(self.data)}\n\n"
