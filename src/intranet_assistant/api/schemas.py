from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_results: list[dict] = []


class VoiceRequest(BaseModel):
    audio_base64: str
    filename: str | None = "audio.wav"
    session_id: str | None = None


class VoiceResponse(BaseModel):
    session_id: str
    transcript: str
    reply: str
    audio_base64: str | None = None
