from __future__ import annotations

from intranet_assistant.tools.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.spec.name}")
        self._tools[tool.spec.name] = tool

    def openai_specs(self) -> list[dict]:
        return [tool.spec.to_openai_tool() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return sorted(self._tools)

    async def run(self, name: str, arguments: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, content=f"Unknown tool: {name}")
        return await tool.run(arguments)
