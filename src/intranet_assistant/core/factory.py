from __future__ import annotations

from intranet_assistant.adapters.asr.http_client import HttpAsrClient
from intranet_assistant.adapters.llm.openai_compatible import OpenAICompatibleLlmClient
from intranet_assistant.adapters.tts.http_client import HttpTtsClient
from intranet_assistant.agent.loop import Agent
from intranet_assistant.core.config import Settings
from intranet_assistant.storage.audit import AuditStore
from intranet_assistant.tools.registry import ToolRegistry
from intranet_assistant.tools.shell import BashTool, PowerShellTool
from intranet_assistant.tools.windows import WindowsAutomationTools


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.audit = AuditStore(settings.storage.audit_db_path)
        self.llm = OpenAICompatibleLlmClient(settings.llm)
        self.asr = HttpAsrClient(settings.asr)
        self.tts = HttpTtsClient(settings.tts)
        self.tools = self._build_tools(settings)
        self.agent = Agent(
            llm=self.llm,
            tools=self.tools,
            audit=self.audit,
            max_tool_rounds=settings.llm.max_tool_rounds,
        )

    @staticmethod
    def _build_tools(settings: Settings) -> ToolRegistry:
        registry = ToolRegistry()
        if settings.tools.shell.enabled:
            registry.register(PowerShellTool(settings.tools.shell))
            if settings.tools.shell.bash_enabled:
                registry.register(BashTool(settings.tools.shell))
        if settings.tools.windows.enabled:
            windows_tools = WindowsAutomationTools(settings.tools.windows)
            for tool in windows_tools.as_tools():
                registry.register(tool)
        return registry
