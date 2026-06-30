ARG VLLM_IMAGE=vllm/vllm-openai:latest
FROM ${VLLM_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN if command -v uv >/dev/null 2>&1; then \
        uv pip install --system --no-cache \
          funasr \
          modelscope \
          huggingface_hub \
          "websockets>=12.0" \
          regex \
          soundfile; \
    else \
        python3 -m pip install --no-cache-dir \
          funasr \
          modelscope \
          huggingface_hub \
          "websockets>=12.0" \
          regex \
          soundfile; \
    fi

RUN git clone --depth 1 https://github.com/modelscope/FunASR.git /opt/FunASR

WORKDIR /opt/FunASR/examples/industrial_data_pretraining/fun_asr_nano

EXPOSE 10095

ENTRYPOINT []
CMD ["python3", "/opt/FunASR/examples/industrial_data_pretraining/fun_asr_nano/serve_realtime_ws.py", "--port", "10095", "--hub", "ms", "--device", "cuda:0", "--dtype", "bf16", "--gpu-memory-utilization", "0.65", "--hotword-file", ""]
