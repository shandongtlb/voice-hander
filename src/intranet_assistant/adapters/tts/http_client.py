from __future__ import annotations

import httpx

from intranet_assistant.core.config import TtsSettings


class HttpTtsClient:
    def __init__(self, settings: TtsSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    async def synthesize(self, text: str) -> bytes:
        payload = {"text": text, "voice": self.settings.voice}
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/synthesize", json=payload)
            response.raise_for_status()
            return response.content
