from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel


app = FastAPI(title="Mock ASR")


class TranscribeResponse(BaseModel):
    text: str


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("zh"),
) -> TranscribeResponse:
    await file.read()
    return TranscribeResponse(text=f"这是一个语音识别占位结果，语言是 {language}，文件名是 {file.filename}")
