from __future__ import annotations

import base64
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from intranet_assistant.api.schemas import ChatRequest, ChatResponse, TranscribeResponse, VoiceRequest, VoiceResponse
from intranet_assistant.core.config import load_settings
from intranet_assistant.core.factory import AppContainer


def create_app() -> FastAPI:
    config_path = os.getenv("INTRANET_ASSISTANT_CONFIG", "config.yaml")
    container = AppContainer(load_settings(config_path))
    app = FastAPI(title="Intranet Voice Assistant", version="0.1.0")
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {
            "ok": True,
            "tools": container.tools.names(),
            "llm_provider": container.settings.llm.provider,
            "asr_provider": container.settings.asr.provider,
            "tts_provider": container.settings.tts.provider,
        }

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        result = await container.agent.chat(request.message, session_id=request.session_id)
        return ChatResponse(
            session_id=result.session_id,
            reply=result.reply,
            tool_results=result.tool_results,
        )

    @app.post("/v1/transcribe", response_model=TranscribeResponse)
    async def transcribe(file: UploadFile = File(...)) -> TranscribeResponse:
        audio = await file.read()
        try:
            transcript = await container.asr.transcribe(audio, filename=file.filename)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"ASR service failed: {exc}") from exc
        return TranscribeResponse(transcript=transcript)

    @app.post("/v1/voice", response_model=VoiceResponse)
    async def voice(request: VoiceRequest) -> VoiceResponse:
        audio = base64.b64decode(request.audio_base64)
        try:
            transcript = await container.asr.transcribe(audio, filename=request.filename)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"ASR service failed: {exc}") from exc
        result = await container.agent.chat(transcript, session_id=request.session_id)
        try:
            speech = await container.tts.synthesize(result.reply) if result.reply else b""
        except Exception:
            speech = b""
        return VoiceResponse(
            session_id=result.session_id,
            transcript=transcript,
            reply=result.reply,
            audio_base64=base64.b64encode(speech).decode("ascii") if speech else None,
        )

    return app
