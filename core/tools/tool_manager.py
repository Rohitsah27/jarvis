"""
Tool Manager orchestrating registration, security checks, and execution.
"""
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from core.tools.base import BaseTool, ToolResult, PermissionLevel
from core.tools.permission import permission_manager
from core.tools.system_tools import (
    TakeScreenshotTool,
    OpenAppTool,
    CloseApplicationTool,
    OpenPathTool,
    TypeTextTool,
    PressKeyTool,
    ClickScreenTool,
    ScrollScreenTool,
    OpenBrowserTool,
    GetSystemStatusTool,
    CreateFolderTool,
    SearchFilesTool,
    AnalyzeScreenTool,
    ControlWindowTool,
    VolumeControlTool,
    MediaControlTool,
    LockScreenTool,
    ControlBrowserTabsTool,
    RunClaudeCLITool,
)


class ToolManager(QObject):
    """
    Central registry for system automation tools.
    Enforces security gate: Tool Manager -> Permission Check -> Execution.
    """

    tool_started = Signal(str)           # tool_name
    tool_finished = Signal(object)       # ToolResult
    tool_requires_approval = Signal(str, dict)  # tool_name, kwargs

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        defaults = [
            TakeScreenshotTool(),
            OpenAppTool(),
            CloseApplicationTool(),
            OpenPathTool(),
            TypeTextTool(),
            PressKeyTool(),
            ClickScreenTool(),
            ScrollScreenTool(),
            OpenBrowserTool(),
            ControlBrowserTabsTool(),
            GetSystemStatusTool(),
            CreateFolderTool(),
            SearchFilesTool(),
            AnalyzeScreenTool(),
            ControlWindowTool(),
            VolumeControlTool(),
            MediaControlTool(),
            LockScreenTool(),
            RunClaudeCLITool(),
        ]
        for tool in defaults:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            res = ToolResult(False, f"Tool '{name}' not found.", name, error="ToolNotFound")
            self.tool_finished.emit(res)
            return res

        # 1. Permission Check Gate
        has_permission = permission_manager.check_permission(tool, kwargs)
        if not has_permission:
            # Need confirmation from user
            res = ToolResult(
                False,
                f"Action '{name}' requires user confirmation before execution.",
                name,
                needs_confirmation=True,
                confirmation_prompt=f"Allow JARVIS to execute: {tool.description}?",
            )
            self.tool_requires_approval.emit(name, kwargs)
            self.tool_finished.emit(res)
            return res

        # 2. Windows Action Execution
        self.tool_started.emit(name)
        try:
            result = tool.execute(**kwargs)
        except Exception as e:
            result = ToolResult(False, f"Execution failed: {str(e)}", name, error=str(e))

        self.tool_finished.emit(result)
        return result


# Global ToolManager instance
tool_manager = ToolManager()
