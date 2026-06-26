from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from intranet_assistant.adapters.base import ChatMessage, LlmClient
from intranet_assistant.storage.audit import AuditStore
from intranet_assistant.tools.registry import ToolRegistry


SYSTEM_PROMPT = """You are an offline intranet assistant.
You may use local tools only when they are necessary.
Before using tools, choose the least risky method.
Use PowerShell for diagnostics and explicit local automation.
Prefer UI Automation controls over coordinate-based desktop actions.
If a requested action is destructive or ambiguous, ask the user for confirmation.
Respond in the user's language.
"""


@dataclass
class ChatTurnResult:
    session_id: str
    reply: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        *,
        llm: LlmClient,
        tools: ToolRegistry,
        audit: AuditStore,
        max_tool_rounds: int,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.audit = audit
        self.max_tool_rounds = max_tool_rounds
        self._sessions: dict[str, list[ChatMessage]] = {}

    async def chat(self, message: str, *, session_id: str | None = None) -> ChatTurnResult:
        session_id = session_id or str(uuid.uuid4())
        history = self._sessions.setdefault(
            session_id,
            [ChatMessage(role="system", content=SYSTEM_PROMPT)],
        )
        history.append(ChatMessage(role="user", content=message))
        await self.audit.write_event(session_id, "user_message", {"message": message})

        tool_results: list[dict[str, Any]] = []
        final_reply = ""

        for _ in range(self.max_tool_rounds + 1):
            response = await self.llm.chat(history, tools=self.tools.openai_specs())
            assistant_message = response.message
            history.append(assistant_message)
            await self.audit.write_event(
                session_id,
                "assistant_message",
                {
                    "content": assistant_message.content,
                    "tool_calls": assistant_message.tool_calls,
                },
            )

            tool_calls = assistant_message.tool_calls or []
            if not tool_calls:
                final_reply = assistant_message.content or ""
                break

            for tool_call in tool_calls:
                result_payload = await self._run_tool_call(session_id, tool_call)
                tool_results.append(result_payload)
                history.append(
                    ChatMessage(
                        role="tool",
                        tool_call_id=result_payload["tool_call_id"],
                        name=result_payload["tool_name"],
                        content=result_payload["content"],
                    )
                )
        else:
            final_reply = "Tool round limit reached before a final answer was produced."

        self._sessions[session_id] = history[-40:]
        return ChatTurnResult(session_id=session_id, reply=final_reply, tool_results=tool_results)

    async def _run_tool_call(self, session_id: str, tool_call: dict[str, Any]) -> dict[str, Any]:
        tool_call_id = str(tool_call.get("id") or uuid.uuid4())
        function = tool_call.get("function") or {}
        tool_name = str(function.get("name") or "")
        raw_arguments = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError as exc:
            arguments = {}
            result_content = f"Invalid tool arguments JSON: {exc}"
            payload = {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "ok": False,
                "content": result_content,
                "arguments": raw_arguments,
            }
            await self.audit.write_event(session_id, "tool_result", payload)
            return payload

        result = await self.tools.run(tool_name, arguments)
        payload = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "ok": result.ok,
            "content": result.content,
            "arguments": arguments,
            "metadata": result.metadata,
        }
        await self.audit.write_event(session_id, "tool_result", payload)
        return payload
