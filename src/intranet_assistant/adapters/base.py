from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_api_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            payload["content"] = self.content
        if self.name is not None:
            payload["name"] = self.name
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            payload["tool_calls"] = self.tool_calls
        return payload


@dataclass
class LlmResponse:
    message: ChatMessage
    raw: dict[str, Any] = field(default_factory=dict)


class LlmClient(Protocol):
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        ...


class AsrClient(Protocol):
    async def transcribe(self, audio: bytes, *, filename: str | None = None) -> str:
        ...


class TtsClient(Protocol):
    async def synthesize(self, text: str) -> bytes:
        ...
