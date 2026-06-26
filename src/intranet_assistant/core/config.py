from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ServerSettings:
    host: str = "127.0.0.1"
    port: int = 18080


@dataclass(frozen=True)
class LlmSettings:
    provider: str = "openai_compatible"
    base_url: str = "http://127.0.0.1:11434/v1"
    api_key: str = "ollama"
    model: str = "qwen2.5:14b"
    timeout_seconds: float = 120
    temperature: float = 0.2
    max_tool_rounds: int = 4


@dataclass(frozen=True)
class AsrSettings:
    provider: str = "http"
    base_url: str = "http://127.0.0.1:8101"
    timeout_seconds: float = 120
    language: str = "zh"


@dataclass(frozen=True)
class TtsSettings:
    provider: str = "http"
    base_url: str = "http://127.0.0.1:8102"
    timeout_seconds: float = 120
    voice: str = "default"


@dataclass(frozen=True)
class ShellToolSettings:
    enabled: bool = True
    bash_enabled: bool = True
    timeout_seconds: int = 30
    allow_dangerous: bool = False
    max_output_chars: int = 12000


@dataclass(frozen=True)
class WindowsToolSettings:
    enabled: bool = True
    screenshot_dir: str = "data/screenshots"
    allow_coordinate_clicks: bool = False
    ocr_enabled: bool = False


@dataclass(frozen=True)
class ToolSettings:
    shell: ShellToolSettings = field(default_factory=ShellToolSettings)
    windows: WindowsToolSettings = field(default_factory=WindowsToolSettings)


@dataclass(frozen=True)
class StorageSettings:
    audit_db_path: str = "data/audit.db"


@dataclass(frozen=True)
class PolicySettings:
    require_confirmation_for_write_actions: bool = True


@dataclass(frozen=True)
class Settings:
    server: ServerSettings = field(default_factory=ServerSettings)
    llm: LlmSettings = field(default_factory=LlmSettings)
    asr: AsrSettings = field(default_factory=AsrSettings)
    tts: TtsSettings = field(default_factory=TtsSettings)
    tools: ToolSettings = field(default_factory=ToolSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    policy: PolicySettings = field(default_factory=PolicySettings)


def load_settings(path: str | Path = "config.yaml") -> Settings:
    config_path = Path(path)
    if not config_path.exists():
        fallback = Path("config.example.yaml")
        if fallback.exists():
            config_path = fallback
        else:
            return Settings()

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")
    return settings_from_dict(raw)


def settings_from_dict(raw: dict[str, Any]) -> Settings:
    tools_raw = _section(raw, "tools")
    return Settings(
        server=ServerSettings(**_section(raw, "server")),
        llm=LlmSettings(**_section(raw, "llm")),
        asr=AsrSettings(**_section(raw, "asr")),
        tts=TtsSettings(**_section(raw, "tts")),
        tools=ToolSettings(
            shell=ShellToolSettings(**_section(tools_raw, "shell")),
            windows=WindowsToolSettings(**_section(tools_raw, "windows")),
        ),
        storage=StorageSettings(**_section(raw, "storage")),
        policy=PolicySettings(**_section(raw, "policy")),
    )


def _section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a mapping.")
    return value
