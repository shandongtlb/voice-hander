from __future__ import annotations

import asyncio
import shutil
import re
from pathlib import Path

from intranet_assistant.core.config import ShellToolSettings
from intranet_assistant.tools.base import ToolResult, ToolSpec


DANGEROUS_PATTERNS = [
    r"\bRemove-Item\b",
    r"\brm\b",
    r"\bdel\b",
    r"\brmdir\b",
    r"\bFormat-Volume\b",
    r"\bStop-Computer\b",
    r"\bRestart-Computer\b",
    r"\bSet-ExecutionPolicy\b",
    r"\bNew-LocalUser\b",
    r"\bRemove-LocalUser\b",
    r"\breg\s+delete\b",
    r"\bsc\s+delete\b",
]


class PowerShellTool:
    spec = ToolSpec(
        name="run_powershell",
        description=(
            "Run a PowerShell command on the local Windows host. Use for local "
            "diagnostics and approved automation. Destructive commands are blocked "
            "unless explicitly enabled in server config."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The PowerShell command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Optional timeout override.",
                    "minimum": 1,
                    "maximum": 300,
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    def __init__(self, settings: ShellToolSettings) -> None:
        self._command_tool = CommandTool(
            settings=settings,
            spec=self.spec,
            executable="powershell",
            fixed_args=["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"],
            unavailable_message="PowerShell executable was not found.",
        )

    async def run(self, arguments: dict) -> ToolResult:
        return await self._command_tool.run(arguments)


class BashTool:
    spec = ToolSpec(
        name="run_bash",
        description=(
            "Run a Bash command on the local host or WSL/Linux environment. Use for "
            "Linux-style diagnostics and approved automation. Destructive commands "
            "are blocked unless explicitly enabled in server config."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The Bash command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Optional timeout override.",
                    "minimum": 1,
                    "maximum": 300,
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    def __init__(self, settings: ShellToolSettings) -> None:
        executable, fixed_args = _find_bash_command()
        self._command_tool = CommandTool(
            settings=settings,
            spec=self.spec,
            executable=executable,
            fixed_args=fixed_args,
            unavailable_message="Bash was not found. Install Git Bash, WSL, or run on Linux.",
        )

    async def run(self, arguments: dict) -> ToolResult:
        return await self._command_tool.run(arguments)


class CommandTool:
    def __init__(
        self,
        *,
        settings: ShellToolSettings,
        spec: ToolSpec,
        executable: str | None,
        fixed_args: list[str],
        unavailable_message: str,
    ) -> None:
        self.settings = settings
        self.spec = spec
        self.executable = executable
        self.fixed_args = fixed_args
        self.unavailable_message = unavailable_message

    async def run(self, arguments: dict) -> ToolResult:
        if self.executable is None:
            return ToolResult(ok=False, content=self.unavailable_message)

        command = str(arguments.get("command", "")).strip()
        if not command:
            return ToolResult(ok=False, content="Missing command.")

        if not self.settings.allow_dangerous and _looks_dangerous(command):
            return ToolResult(
                ok=False,
                content="Command blocked by shell policy because it looks destructive.",
                metadata={"blocked": True},
            )

        timeout = int(arguments.get("timeout_seconds") or self.settings.timeout_seconds)
        cwd_arg = arguments.get("cwd")
        cwd = str(Path(cwd_arg).resolve()) if cwd_arg else None

        process = await asyncio.create_subprocess_exec(
            self.executable,
            *self.fixed_args,
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ToolResult(ok=False, content=f"Command timed out after {timeout} seconds.")

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        combined = _trim_output(
            "\n".join(part for part in [stdout_text, stderr_text] if part),
            self.settings.max_output_chars,
        )
        return ToolResult(
            ok=process.returncode == 0,
            content=combined or f"Process exited with code {process.returncode}.",
            metadata={"returncode": process.returncode},
        )


def _looks_dangerous(command: str) -> bool:
    return any(re.search(pattern, command, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS)


def _trim_output(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + f"\n...[truncated {omitted} chars]"


def _find_bash_command() -> tuple[str | None, list[str]]:
    if shutil.which("bash"):
        return "bash", ["-lc"]
    if shutil.which("wsl"):
        return "wsl", ["bash", "-lc"]
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    if git_bash.exists():
        return str(git_bash), ["-lc"]
    return None, ["-lc"]
