from __future__ import annotations

import httpx

from intranet_assistant.core.config import AsrSettings


class HttpAsrClient:
    def __init__(self, settings: AsrSettings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")

    async def transcribe(self, audio: bytes, *, filename: str | None = None) -> str:
        upload_name = filename or "audio.wav"
        files = {
            "file": (
                upload_name,
                audio,
                _guess_audio_content_type(upload_name),
            )
        }
        data = {"language": self.settings.language}
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds, trust_env=False) as client:
            response = await client.post(f"{self.base_url}/transcribe", data=data, files=files)
            response.raise_for_status()
            payload = response.json()

        text = payload.get("text")
        if not isinstance(text, str):
            raise ValueError("ASR response must include a string 'text' field.")
        return text


def _guess_audio_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".webm"):
        return "audio/webm"
    if lower.endswith(".m4a") or lower.endswith(".mp4"):
        return "audio/mp4"
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".ogg") or lower.endswith(".opus"):
        return "audio/ogg"
    return "audio/wav"
