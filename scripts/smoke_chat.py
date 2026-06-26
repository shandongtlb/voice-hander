from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from intranet_assistant.adapters.base import ChatMessage
from intranet_assistant.adapters.llm.openai_compatible import OpenAICompatibleLlmClient
from intranet_assistant.core.config import load_settings


async def run(config: str, message: str) -> None:
    settings = load_settings(config)
    client = OpenAICompatibleLlmClient(settings.llm)
    response = await client.chat([ChatMessage(role="user", content=message)])
    print(response.message.content or "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the configured LLM endpoint.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--message", default="用一句中文回答：本地模型连接正常。")
    args = parser.parse_args()
    asyncio.run(run(args.config, args.message))


if __name__ == "__main__":
    main()
