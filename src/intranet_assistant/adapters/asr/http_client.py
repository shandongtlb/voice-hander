from __future__ import annotations

import httpx

from intranet_assistant.core.config import AsrSettings


class HttpAsrClient:
    def __init__(self, settings: AsrSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    async def transcribe(self, audio: bytes, *, filename: str | None = None) -> str:
        files = {
            "file": (
                filename or "audio.wav",
                audio,
                "audio/wav",
            )
        }
        data = {"language": self.settings.language}
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/transcribe", data=data, files=files)
            response.raise_for_status()
            payload = response.json()

        text = payload.get("text")
        if not isinstance(text, str):
            raise ValueError("ASR response must include a string 'text' field.")
        return text
