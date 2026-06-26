from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from intranet_assistant.core.config import WindowsToolSettings
from intranet_assistant.tools.base import ToolResult, ToolSpec


class ListWindowsTool:
    spec = ToolSpec(
        name="list_windows",
        description="List visible top-level Windows desktop windows.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_list_windows_sync)


class ClickControlTool:
    spec = ToolSpec(
        name="click_control",
        description=(
            "Click a UI Automation control inside a window by title and control name. "
            "Prefer this over coordinate clicks when possible."
        ),
        parameters={
            "type": "object",
            "properties": {
                "window_title": {"type": "string"},
                "control_name": {"type": "string"},
            },
            "required": ["window_title", "control_name"],
            "additionalProperties": False,
        },
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_click_control_sync, arguments)


class TypeTextTool:
    spec = ToolSpec(
        name="type_text",
        description="Type text into the currently focused Windows control.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_type_text_sync, str(arguments.get("text", "")))


class HotkeyTool:
    spec = ToolSpec(
        name="hotkey",
        description="Send a keyboard shortcut to the currently focused Windows application.",
        parameters={
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keys such as ['ctrl', 's'] or ['alt', 'f4'].",
                }
            },
            "required": ["keys"],
            "additionalProperties": False,
        },
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_hotkey_sync, arguments)


class ScreenshotTool:
    spec = ToolSpec(
        name="screenshot",
        description="Capture the current desktop screen and save it to the configured screenshot directory.",
        parameters={
            "type": "object",
            "properties": {
                "monitor": {
                    "type": "integer",
                    "description": "Monitor index for mss. 0 captures the virtual all-monitor screen.",
                    "default": 0,
                }
            },
            "additionalProperties": False,
        },
    )

    def __init__(self, settings: WindowsToolSettings) -> None:
        self.settings = settings

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_screenshot_sync, self.settings, arguments)


class ClickXYTool:
    spec = ToolSpec(
        name="click_xy",
        description=(
            "Click absolute screen coordinates. Use only as a fallback when UI Automation "
            "controls are unavailable and coordinate clicks are enabled by policy."
        ),
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "default": "left",
                },
            },
            "required": ["x", "y"],
            "additionalProperties": False,
        },
    )

    def __init__(self, settings: WindowsToolSettings) -> None:
        self.settings = settings

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_click_xy_sync, self.settings, arguments)


class OcrScreenTool:
    spec = ToolSpec(
        name="ocr_screen",
        description="Run OCR over a screenshot of the current desktop. Requires an installed OCR engine.",
        parameters={
            "type": "object",
            "properties": {
                "monitor": {
                    "type": "integer",
                    "description": "Monitor index for mss. 0 captures the virtual all-monitor screen.",
                    "default": 0,
                }
            },
            "additionalProperties": False,
        },
    )

    def __init__(self, settings: WindowsToolSettings) -> None:
        self.settings = settings

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return await asyncio.to_thread(_ocr_screen_sync, self.settings, arguments)


class WindowsAutomationTools:
    def __init__(self, settings: WindowsToolSettings) -> None:
        self.settings = settings

    def as_tools(self) -> list:
        return [
            ListWindowsTool(),
            ClickControlTool(),
            TypeTextTool(),
            HotkeyTool(),
            ScreenshotTool(self.settings),
            ClickXYTool(self.settings),
            OcrScreenTool(self.settings),
        ]


def _list_windows_sync() -> ToolResult:
    try:
        from pywinauto import Desktop
    except ImportError:
        return ToolResult(ok=False, content="pywinauto is not installed.")

    windows = []
    for window in Desktop(backend="uia").windows():
        title = window.window_text()
        if title:
            windows.append(title)
    return ToolResult(ok=True, content="\n".join(windows) or "No visible windows found.")


def _click_control_sync(arguments: dict[str, Any]) -> ToolResult:
    try:
        from pywinauto import Desktop
    except ImportError:
        return ToolResult(ok=False, content="pywinauto is not installed.")

    window_title = str(arguments.get("window_title", ""))
    control_name = str(arguments.get("control_name", ""))
    if not window_title or not control_name:
        return ToolResult(ok=False, content="window_title and control_name are required.")

    try:
        window = Desktop(backend="uia").window(title_re=f".*{window_title}.*")
        control = window.child_window(title=control_name)
        control.click_input()
        return ToolResult(ok=True, content=f"Clicked control: {control_name}")
    except Exception as exc:
        return ToolResult(ok=False, content=f"Failed to click control: {exc}")


def _type_text_sync(text: str) -> ToolResult:
    try:
        from pywinauto.keyboard import send_keys
    except ImportError:
        return ToolResult(ok=False, content="pywinauto is not installed.")

    if not text:
        return ToolResult(ok=False, content="Text is empty.")
    send_keys(text, with_spaces=True, pause=0.01)
    return ToolResult(ok=True, content=f"Typed {len(text)} chars.")


def _hotkey_sync(arguments: dict[str, Any]) -> ToolResult:
    keys = arguments.get("keys")
    if not isinstance(keys, list) or not keys:
        return ToolResult(ok=False, content="keys must be a non-empty list.")
    normalized = [str(key).lower().strip() for key in keys if str(key).strip()]
    if not normalized:
        return ToolResult(ok=False, content="keys must contain at least one valid key.")
    try:
        import pyautogui
    except ImportError:
        return ToolResult(ok=False, content="pyautogui is not installed.")
    pyautogui.hotkey(*normalized)
    return ToolResult(ok=True, content=f"Sent hotkey: {'+'.join(normalized)}")


def _screenshot_sync(settings: WindowsToolSettings, arguments: dict[str, Any]) -> ToolResult:
    try:
        path, metadata = _capture_screenshot(settings, int(arguments.get("monitor") or 0))
    except RuntimeError as exc:
        return ToolResult(ok=False, content=str(exc))
    return ToolResult(ok=True, content=str(path), metadata=metadata)


def _click_xy_sync(settings: WindowsToolSettings, arguments: dict[str, Any]) -> ToolResult:
    if not settings.allow_coordinate_clicks:
        return ToolResult(
            ok=False,
            content="Coordinate clicks are disabled by policy. Prefer click_control or enable allow_coordinate_clicks.",
            metadata={"blocked": True},
        )
    try:
        import pyautogui
    except ImportError:
        return ToolResult(ok=False, content="pyautogui is not installed.")
    x = int(arguments.get("x"))
    y = int(arguments.get("y"))
    button = str(arguments.get("button") or "left")
    pyautogui.click(x=x, y=y, button=button)
    return ToolResult(ok=True, content=f"Clicked {button} at ({x}, {y}).")


def _ocr_screen_sync(settings: WindowsToolSettings, arguments: dict[str, Any]) -> ToolResult:
    if not settings.ocr_enabled:
        return ToolResult(
            ok=False,
            content="OCR is disabled by policy. Set tools.windows.ocr_enabled to true to enable it.",
            metadata={"blocked": True},
        )
    try:
        path, metadata = _capture_screenshot(settings, int(arguments.get("monitor") or 0))
    except RuntimeError as exc:
        return ToolResult(ok=False, content=str(exc))
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return ToolResult(
            ok=False,
            content="rapidocr-onnxruntime is not installed. Install the windows optional dependencies.",
            metadata={"screenshot_path": str(path)},
        )

    engine = RapidOCR()
    result, _ = engine(str(path))
    if not result:
        return ToolResult(ok=True, content="", metadata={"screenshot_path": str(path), **metadata})

    lines = []
    for item in result:
        text = item[1]
        score = item[2]
        lines.append(f"{text} ({score:.2f})")
    return ToolResult(
        ok=True,
        content="\n".join(lines),
        metadata={"screenshot_path": str(path), **metadata},
    )


def _capture_screenshot(settings: WindowsToolSettings, monitor_index: int) -> tuple[Path, dict[str, Any]]:
    try:
        import mss
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("mss and pillow are required for screenshots.") from exc

    screenshot_dir = Path(settings.screenshot_dir)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("screen_%Y%m%d_%H%M%S_%f.png")
    path = screenshot_dir / filename
    with mss.mss() as capture:
        monitors = capture.monitors
        if monitor_index < 0 or monitor_index >= len(monitors):
            monitor_index = 0
        monitor = monitors[monitor_index]
        shot = capture.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save(path)
    metadata = {
        "monitor": monitor_index,
        "width": monitor["width"],
        "height": monitor["height"],
        "left": monitor["left"],
        "top": monitor["top"],
    }
    return path, metadata
