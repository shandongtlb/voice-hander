from __future__ import annotations

from fastapi import FastAPI, Response
from pydantic import BaseModel


app = FastAPI(title="Mock TTS")


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "default"


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest) -> Response:
    return Response(
        content=b"",
        media_type="audio/wav",
        headers={"X-Mock-TTS": "true", "X-Voice": request.voice},
    )
