from __future__ import annotations

from typing import Any

import httpx

from intranet_assistant.adapters.base import ChatMessage, LlmResponse
from intranet_assistant.core.config import LlmSettings


class OpenAICompatibleLlmClient:
    def __init__(self, settings: LlmSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [message.to_api_dict() for message in messages],
            "temperature": self.settings.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        api_message = choice["message"]
        return LlmResponse(
            message=ChatMessage(
                role=api_message.get("role", "assistant"),
                content=api_message.get("content"),
                tool_calls=api_message.get("tool_calls"),
            ),
            raw=data,
        )
