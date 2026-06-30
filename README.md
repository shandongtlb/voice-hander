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

Open `http://127.0.0.1:5173`, allow microphone access, then use the record button. The browser sends 16 kHz PCM audio directly to a FunASR realtime WebSocket service; the recognized text is accumulated in the draft box and can be sent to `/v1/chat`.

The default realtime ASR URL in the UI is:

```text
ws://127.0.0.1:10095
```

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

## Realtime FunASR

The voice UI does not need the project ASR gateway for realtime transcription. It talks directly to the official FunASR WebSocket protocol:

```text
browser mic -> FunASR WebSocket -> transcript draft -> /v1/chat
```

### Docker on Windows

With Docker Desktop using the WSL2 backend, run the realtime service as a Linux GPU container:

```powershell
wsl --update
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
docker compose -f docker-compose.funasr.yml build
docker compose -f docker-compose.funasr.yml up
```

The first start downloads the vLLM image, installs FunASR, and downloads `FunAudioLLM/Fun-ASR-Nano-2512`; it can take a while. The default vLLM image is `vllm/vllm-openai:latest`, which currently requires a CUDA 13-capable NVIDIA driver. When the log shows `Server on ws://0.0.0.0:10095`, open the frontend and keep the FunASR realtime URL as `ws://127.0.0.1:10095`.

The compose file defaults to `--dtype bf16` and `--gpu-memory-utilization 0.65`, which fits RTX 40-series GPUs well. If CUDA reports out-of-memory, lower that value in `docker-compose.funasr.yml` to `0.55`; if there is headroom, raise it gradually. Use `fp32` only on GPUs without bfloat16 support.

If downloads time out, separate the proxy used by Docker itself from the proxy used inside the Linux container.

Docker image pulls run from Docker Desktop on the Windows host, so a local Windows proxy can use loopback:

```powershell
$env:HTTP_PROXY = "http://127.0.0.1:10808"
$env:HTTPS_PROXY = "http://127.0.0.1:10808"
```

Build steps and runtime downloads run inside the Linux container. In that context, `127.0.0.1` means the container itself, not Windows. If your proxy allows LAN/local-network connections, use `host.docker.internal` for FunASR's container downloads:

```powershell
$env:FUNASR_HTTP_PROXY = "http://host.docker.internal:10808"
$env:FUNASR_HTTPS_PROXY = "http://host.docker.internal:10808"
docker compose -f docker-compose.funasr.yml up --build
```

If `host.docker.internal:10808` still times out, enable the proxy app's LAN/listen-on-all-interfaces option, or configure the proxy directly in Docker Desktop settings. A proxy that only binds to `127.0.0.1` cannot be reached from inside the container.

To pin a vLLM image later:

```powershell
$env:VLLM_IMAGE = "vllm/vllm-openai:latest"
docker compose -f docker-compose.funasr.yml build
```

Stop the service with:

```powershell
docker compose -f docker-compose.funasr.yml down
```

Run the official Fun-ASR-Nano realtime service in WSL/Linux where vLLM is available:

```bash
git clone https://github.com/modelscope/FunASR.git
cd FunASR/examples/industrial_data_pretraining/fun_asr_nano

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install vllm

python serve_realtime_ws.py --port 10095 --device cuda:0 --dtype bf16 --gpu-memory-utilization 0.75
```

Then keep the frontend FunASR realtime URL as `ws://localhost:10095`. The UI sends `START`, optional `LANGUAGE:<value>` and `HOTWORDS:<value>`, then PCM16 audio bytes, and finally `STOP`. If a browser proxy extension is enabled, bypass `localhost` and `127.0.0.1`; otherwise local WebSocket connections may fail before reaching Docker.

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

## Technical Docs

- [Technical rules](docs/TECHNICAL_RULES.md)
- [TODO interfaces](docs/TODO_INTERFACES.md)

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
