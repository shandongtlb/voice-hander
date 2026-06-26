import pytest

from intranet_assistant.tools.base import ToolResult, ToolSpec
from intranet_assistant.tools.registry import ToolRegistry


class EchoTool:
    spec = ToolSpec(
        name="echo",
        description="Echo input.",
        parameters={"type": "object", "properties": {}, "additionalProperties": True},
    )

    async def run(self, arguments):
        return ToolResult(ok=True, content=str(arguments))


@pytest.mark.asyncio
async def test_registry_runs_tool():
    registry = ToolRegistry()
    registry.register(EchoTool())
    result = await registry.run("echo", {"x": 1})
    assert result.ok is True
    assert "x" in result.content
