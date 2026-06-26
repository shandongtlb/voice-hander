# Intranet Voice Assistant

Offline-first scaffold for a Windows intranet assistant. The first version is intentionally simple inside a heavier architecture:

- ASR, LLM, and TTS are separate adapters.
- The central model uses an OpenAI-compatible API, such as Ollama at `http://127.0.0.1:11434/v1`.
- Tool execution is local and policy checked.
- Audit logs are written to SQLite.
- Windows GUI automation is isolated behind tool modules.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[windows]
Copy-Item config.example.yaml config.yaml
.\start.ps1
```

After the first setup, start it with:

```powershell
.\start.ps1
```

Start the Vue voice UI in another terminal:

```powershell
.\start-frontend.ps1
```

Open `http://127.0.0.1:5173`, allow microphone access, then use the record button. The browser sends short audio chunks to `/v1/transcribe`; the recognized text is accumulated in the draft box and can be sent to `/v1/chat`.

Useful options:

```powershell
.\start.ps1 -Port 18081
.\start.ps1 -Config config.yaml -Reload
.\start.ps1 -Install
```

The Python entry point is also available:

```powershell
intranet-assistant serve --config config.yaml
```

For OCR on Windows, use Python 3.11 or 3.12 so `rapidocr-onnxruntime` can be installed. Python 3.14 can run the desktop automation, screenshot, keyboard/mouse, and OpenCV tools, but the current OCR package does not publish compatible wheels yet.

Send a text request:

```powershell
.\scripts\chat.ps1 -Message "Say hello. If you need tools, ask first."
```

Send an audio file through ASR, chat, and optional TTS:

```powershell
.\scripts\voice.ps1 -AudioPath .\data\sample.wav
```

The `/v1/voice` flow is:

```text
audio file -> ASR /transcribe -> transcript text -> /v1/chat agent loop -> TTS /synthesize
```

For local ASR/TTS development without real models, start mock services in two extra terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn scripts.mock_asr:app --host 127.0.0.1 --port 8101
.\.venv\Scripts\python.exe -m uvicorn scripts.mock_tts:app --host 127.0.0.1 --port 8102
```

Windows PowerShell 5.1 can mangle Chinese text when JSON strings are sent without an explicit UTF-8 body. Use `scripts/chat.ps1`, PowerShell 7, or send UTF-8 bytes manually.

## Service Boundaries

```text
voice gateway
  -> ASR adapter
  -> agent core
       -> LLM adapter
       -> policy engine
       -> tool registry
       -> audit store
  -> TTS adapter
```

The current scaffold keeps these pieces in one repository, but each boundary can become a separate service later.

## Current Features

- OpenAI-compatible chat completions client for Ollama or another local gateway.
- Tool loop for OpenAI-style `tool_calls`.
- PowerShell command tool with basic risk filtering.
- Windows UI tools with optional `pywinauto`.
- HTTP ASR/TTS clients for separately hosted local speech services.
- SQLite audit events.
- FastAPI endpoints for health, chat, and voice skeleton flows.

## Notes

This project is designed for an isolated network. Do not put cloud API keys in `config.yaml` unless you later introduce a controlled boundary gateway.
